from contextlib import closing
import csv
from django.db import connection
from datetime import datetime
import glob
import hashlib
from io import StringIO
from multiprocessing import Pool, cpu_count
import os
import tempfile
import time
import urllib.request
import zipfile

from django import db
from django.core import management
from django.core.management.base import BaseCommand

from ohiovoter.models import Election, Voter


COUNTIES = [
    'ADAMS',
    'ALLEN',
    'ASHLAND',
    'ASHTABULA',
    'ATHENS',
    'AUGLAIZE',
    'BELMONT',
    'BROWN',
    'BUTLER',
    'CARROLL',
    'CHAMPAIGN',
    'CLARK',
    'CLERMONT',
    'CLINTON',
    'COLUMBIANA',
    'COSHOCTON',
    'CRAWFORD',
    'CUYAHOGA',
    'DARKE',
    'DEFIANCE',
    'DELAWARE',
    'ERIE',
    'FAIRFIELD',
    'FAYETTE',
    'FRANKLIN',
    'FULTON',
    'GALLIA',
    'GEAUGA',
    'GREENE',
    'GUERNSEY',
    'HAMILTON',
    'HANCOCK',
    'HARDIN',
    'HARRISON',
    'HENRY',
    'HIGHLAND',
    'HOCKING',
    'HOLMES',
    'HURON',
    'JACKSON',
    'JEFFERSON',
    'KNOX',
    'LAKE',
    'LAWRENCE',
    'LICKING',
    'LOGAN',
    'LORAIN',
    'LUCAS',
    'MADISON',
    'MAHONING',
    'MARION',
    'MEDINA',
    'MEIGS',
    'MERCER',
    'MIAMI',
    'MONROE',
    'MONTGOMERY',
    'MORGAN',
    'MORROW',
    'MUSKINGUM',
    'NOBLE',
    'OTTAWA',
    'PAULDING',
    'PERRY',
    'PICKAWAY',
    'PIKE',
    'PORTAGE',
    'PREBLE',
    'PUTNAM',
    'RICHLAND',
    'ROSS',
    'SANDUSKY',
    'SCIOTO',
    'SENECA',
    'SHELBY',
    'STARK',
    'SUMMIT',
    'TRUMBULL',
    'TUSCARAWAS',
    'UNION',
    'VANWERT',
    'VINTON',
    'WARREN',
    'WASHINGTON',
    'WAYNE',
    'WILLIAMS',
    'WOOD',
    'WYANDOT',
]


VOTER_COLUMNS = [
    'sos_voterid',
    'county_number',
    'county_id',
    'last_name',
    'first_name',
    'middle_name',
    'suffix',
    'date_of_birth',
    'registration_date',
    'voter_status',
    'party_affiliation',
    'residential_address1',
    'residential_secondary_addr',
    'residential_city',
    'residential_state',
    'residential_zip',
    'residential_zip_plus4',
    'residential_country',
    'residential_postalcode',
    'mailing_address1',
    'mailing_secondary_address',
    'mailing_city',
    'mailing_state',
    'mailing_zip',
    'mailing_zip_plus4',
    'mailing_country',
    'mailing_postal_code',
    'career_center',
    'city',
    'city_school_district',
    'county_court_district',
    'congressional_district',
    'court_of_appeals',
    'edu_service_center_district',
    'exempted_vill_school_district',
    'library',
    'local_school_district',
    'municipal_court_district',
    'precinct_name',
    'precinct_code',
    'state_board_of_education',
    'state_representative_district',
    'state_senate_district',
    'township',
    'village',
    'ward',
    'county',
]


ELECTION_COLUMNS = [
    'id',
    'category',
    'date',
    'party',
]


PARTICIPATION_COLUMNS = [
    'voter_id',
    'election_id',
]


class Command(BaseCommand):

    @staticmethod
    def download_county_data(county, destination_directory):
        url = 'ftp://sosftp.sos.state.oh.us/free/Voter/{}.zip'.format(county)

        downloaded_file = '{}/{}.zip'.format(destination_directory, county)
        urllib.request.urlretrieve(url, downloaded_file)
        with zipfile.ZipFile(downloaded_file, 'r') as z:
            z.extractall(destination_directory)

        # Some of our files are very large.
        # Let's split them into smaller files maxed at 100000 lines
        divisor = 100000
        outfileno = 1
        outfile = None

        big_file_name = '{}/{}.TXT'.format(destination_directory, county)
        with open(big_file_name, 'r') as input_file:
            reader = csv.reader(input_file)
            header = next(reader, None)  # skip the headers

            for index, row in enumerate(reader):
                if index % divisor == 0:
                    if outfile is not None:
                        outfile.close()
                    outfilename = '{}/{}-{}.csv'.format(destination_directory, county, outfileno)
                    outfile = open(outfilename, 'w')
                    outfileno += 1
                    writer = csv.writer(outfile)
                    writer.writerow(header)
                writer.writerow(row)

    @staticmethod
    def load_county_data_into_db(county, directory_name):
        db.connections.close_all()

        processed_elections = set()

        county_filenames = []
        pattern = '{}/{}-*csv'.format(directory_name, county)
        for f in glob.glob(pattern):
            county_filenames.append(f)

        for county_filename in county_filenames:
            with open(county_filename, encoding='utf-8') as input_file:
                reader = csv.reader(input_file)

                header = next(reader)

                voter_stream = StringIO()
                election_stream = StringIO()
                participation_stream = StringIO()

                voter_writer = csv.writer(voter_stream, delimiter=',', quoting=csv.QUOTE_ALL)
                voter_writer.writerow(VOTER_COLUMNS)  # start with the header

                # Since I'm defining this table, not pulling it from the CSV,
                # I don't need to quote my values, and we'll add the header at write
                participation_writer = csv.writer(participation_stream, delimiter=',')

                for row in reader:
                    this_voters_data = []
                    this_voters_elections = []

                    for index, column_value in enumerate(row):
                        field_name = header[index]
                        lower_field_name = field_name.lower()

                        if hasattr(Voter, lower_field_name):  # parse Voter data
                            this_voters_data.append(column_value)
                        else:  # parse Election data
                            if column_value:
                                category_display, date_string = field_name.split('-')

                                election_category = Election.CATEGORY_CHOICES_REVERSE_MAP[category_display]
                                election_date = datetime.strptime(date_string, '%m/%d/%Y').strftime('%Y-%m-%d')
                                election_party = column_value

                                election_hashable_key = '{}.{}.{}'.format(election_category, election_date, election_party).encode('utf-8')
                                election_id = hashlib.sha256(election_hashable_key).hexdigest()

                                election_data = [election_id, election_category, election_date, election_party]

                                # We'll write the elections as we go
                                # And keep track of them in memory
                                if not election_id in processed_elections:
                                    with closing(connection.cursor()) as cursor:
                                        fields = ','.join(ELECTION_COLUMNS)
                                        query_string = 'INSERT INTO ohiovoter_election ({}) VALUES (%s, %s, %s, %s) ON CONFLICT (id) DO NOTHING'.format(fields)
                                        cursor.execute(
                                            query_string,
                                            election_data,
                                        )
                                    processed_elections.add(election_id)

                                participation_writer.writerow([this_voters_data[0], election_id])

                    # I need to manually add this on since I'm inferring it
                    this_voters_data.append(county)
                    voter_writer.writerow(this_voters_data)

                # Write Voters
                voter_stream.seek(0)
                with closing(connection.cursor()) as cursor:
                    # We need to do this manually since copy_from doesn't handle CSV quoting
                    cursor.copy_expert("""COPY ohiovoter_voter FROM STDIN WITH CSV HEADER DELIMITER AS ','""", voter_stream)

                # Write Participations
                participation_stream.seek(0)
                with closing(connection.cursor()) as cursor:
                    cursor.copy_from(
                        file=participation_stream,
                        table='ohiovoter_participation',
                        sep=',',
                        columns=PARTICIPATION_COLUMNS,
                    )

        print('{} County...Finished!'.format(county.title()))

    def handle(self, **kwargs):
        message = ('\nThis command will completely wipe your database and '
                   'download & parse the latest Ohio Voter File data. The '
                   'process can take minutes or hours depending on your '
                   'machine. Continue? (y/n): ')

        answer = input(message)

        if answer == 'y':
            # start fresh
            management.call_command('flush', interactive=False)
            management.call_command('migrate', interactive=False)

            print('\nDownloading and parsing county data. This will take a while...')

            with tempfile.TemporaryDirectory() as tmpdirname:
                num_cpus = cpu_count()

                pool = Pool(num_cpus)

                args = [(county, tmpdirname) for county in COUNTIES]

                print('Downloading county data...')
                pool.starmap(self.download_county_data, args)

                start = time.time()

                print('Importing county data...')
                pool.starmap(self.load_county_data_into_db, args)

                end = time.time()
                print(end - start)

            print('\nDone!')
