from contextlib import closing
import csv
from django.db import connection
from datetime import datetime
import hashlib
from io import StringIO
from multiprocessing.dummy import Pool as ThreadPool
import os
import tempfile
import time
import urllib.request
import zipfile

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

    processed_elections = set()

    @staticmethod
    def download_county_data(county, destination_directory):
        url = 'ftp://sosftp.sos.state.oh.us/free/Voter/{}.zip'.format(county)

        downloaded_file = '{}/{}.zip'.format(destination_directory, county)
        urllib.request.urlretrieve(url, downloaded_file)
        with zipfile.ZipFile(downloaded_file, 'r') as z:
            z.extractall(destination_directory)

    @staticmethod
    def load_county_data_into_db(county, directory_name):
        print('Parsing and imorting {} County data...'.format(county.title()))

        county_filename = '{}/{}.TXT'.format(directory_name, county)

        with open(county_filename, encoding='utf-8') as input_file:
            reader = csv.reader(input_file)

            header = next(reader)

            voter_stream = StringIO()
            election_stream = StringIO()
            participation_stream = StringIO()

            voter_writer = csv.writer(voter_stream, delimiter='\t')
            election_writer = csv.writer(election_stream, delimiter='\t')
            participation_writer = csv.writer(participation_stream, delimiter='\t')

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

                            if not election_id in Command.processed_elections:
                                election_writer.writerow(election_data)
                                Command.processed_elections.add(election_id)

                            participation_writer.writerow([this_voters_data[0], election_id])

                # I need to manually add this on since I'm inferring it
                this_voters_data.append(county)
                voter_writer.writerow(this_voters_data)

            # Write Voters
            voter_stream.seek(0)
            with closing(connection.cursor()) as cursor:
                cursor.copy_from(
                    file=voter_stream,
                    table='ohiovoter_voter',
                    sep='\t',
                    columns=VOTER_COLUMNS,
                )

            # Write Elections
            election_stream.seek(0)
            with closing(connection.cursor()) as cursor:
                cursor.copy_from(
                    file=election_stream,
                    table='ohiovoter_election',
                    sep='\t',
                    columns=ELECTION_COLUMNS,
                )

            # Write Participations
            participation_stream.seek(0)
            with closing(connection.cursor()) as cursor:
                cursor.copy_from(
                    file=participation_stream,
                    table='ohiovoter_participation',
                    sep='\t',
                    columns=PARTICIPATION_COLUMNS,
                )

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

            start = time.time()

            # download all the county data from the SoS website
            print('\nDownloading County data...')
            pool = ThreadPool(8)
            with tempfile.TemporaryDirectory() as tmpdirname:
                args = [(county, tmpdirname) for county in COUNTIES]
                pool.starmap(self.download_county_data, args)
                pool.close()
                pool.join()

                # Parse and load it all into the database
                for county in COUNTIES:
                    self.load_county_data_into_db(county, tmpdirname)

            print('\nDone!')

            end = time.time()
            print(end - start)
