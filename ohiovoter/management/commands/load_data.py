from contextlib import closing
import csv
from django.db import connection
from datetime import datetime
from io import StringIO
import os
import shutil
import tempfile
import urllib.request
import zipfile

from django.core import management
from django.core.management.base import BaseCommand

from ohiovoter.models import Election, Voter, Participation


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


class Command(BaseCommand):
    def handle(self, **kwargs):

        message = ('\nThis command will completely wipe your database and download & parse the latest Ohio Voter File data.'
                   '\nThe process is very slow and can take minutes or hours depending on your network and machine. Continue? (y/n): ')

        answer = input(message)

        if answer == 'y':
            management.call_command('flush', interactive=False)

            import time
            start = time.time()

            # caching the elections across files to decrease DB I/O
            cached_elections = {}

            for county in COUNTIES:
                print('\nDownloading {} County data...'.format(county.title()))

                url = 'ftp://sosftp.sos.state.oh.us/free/Voter/{}.zip'.format(county)

                voter_columns = []
                participation_columns = ['voter_id', 'election_id']  # I know these ahead of time because I made them.

                with tempfile.TemporaryDirectory() as tmpdirname:
                    downloaded_file = '{}/{}.zip'.format(tmpdirname, county)
                    urllib.request.urlretrieve(url, downloaded_file)
                    with zipfile.ZipFile(downloaded_file, 'r') as z:
                        z.extractall(tmpdirname)
                    os.remove(downloaded_file)

                    old_filename = '{}/{}.TXT'.format(tmpdirname, county)
                    county_filename = '{}/{}_COUNTY.csv'.format(tmpdirname, county)
                    os.rename(old_filename, county_filename)

                    print('Parsing and loading {} County data...'.format(county.title()))

                    with open(county_filename, encoding='utf-8') as input_file:
                        reader = csv.reader(input_file)

                        header = next(reader)

                        voter_stream = StringIO()
                        voter_writer = csv.writer(voter_stream, delimiter='\t')

                        participation_stream = StringIO()
                        participation_writer = csv.writer(participation_stream, delimiter='\t')

                        c_start = time.time()
                        print('Starting to parse CSV')
                        for row in reader:
                            this_voters_data = []

                            this_voters_elections = []
                            voter_kwargs = {'county': county}
                            election_kwargs = {}

                            for index, column_value in enumerate(row):
                                field_name = header[index]
                                lower_field_name = field_name.lower()

                                if hasattr(Voter, lower_field_name):  # parse Voter data
                                    voter_columns.append(lower_field_name)
                                    this_voters_data.append(column_value)
                                else:  # parse Election data
                                    if column_value:
                                        category_display, date_string = field_name.split('-')

                                        election_category = Election.CATEGORY_CHOICES_REVERSE_MAP[category_display]
                                        election_party = column_value

                                        election_kwargs['category'] = election_category
                                        election_kwargs['party'] = election_party
                                        election_kwargs['date'] = datetime.strptime(date_string, '%m/%d/%Y')

                                        # Get the cached election, or create a cache if we've never seen it before
                                        hashable_election_kwargs = frozenset(election_kwargs.items())
                                        election = cached_elections.get(hashable_election_kwargs, None)
                                        if not election:
                                            election = Election.objects.create(**election_kwargs)
                                            election.save()
                                            cached_elections[hashable_election_kwargs] = election

                                        participation_writer.writerow([this_voters_data[0], election.id])
                            voter_writer.writerow(this_voters_data)

                        c_end = time.time()
                        print('Done parsing CSV')
                        print('Parsing CSV took: {}'.format(c_end-c_start))

                        v_start = time.time()
                        print('Starting to insert Voters')
                        voter_stream.seek(0)
                        seen = set()
                        seen_add = seen.add
                        voter_columns_unique = [x for x in voter_columns if not (x in seen or seen_add(x))]
                        with closing(connection.cursor()) as cursor:
                            cursor.copy_from(
                                file=voter_stream,
                                table='ohiovoter_voter',
                                sep='\t',
                                columns=voter_columns_unique,
                            )

                        v_end = time.time()
                        print('Done inserting Voters')
                        print('Writing voters took: {}'.format(v_end-v_start))

                        p_start = time.time()
                        print('Starting to insert Participations')
                        participation_stream.seek(0)
                        with closing(connection.cursor()) as cursor:
                            cursor.copy_from(
                                file=participation_stream,
                                table='ohiovoter_participation',
                                sep='\t',
                                columns=participation_columns,
                            )
                        p_end = time.time()
                        print('Done inserting Participations')
                        print('Writing participations took: {}'.format(p_end-p_start))

            print('\nDone!')

            end = time.time()
            print(end - start)
