import csv
from datetime import datetime
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

                        # all of the Voter objects built from this csv
                        voters = []

                        # a list of lists, each item being a list of elections index-coresponding to voters
                        election_lists = []

                        c_start = time.time()
                        print('Starting to parse CSV')
                        for row in reader:
                            this_voters_elections = []
                            voter_kwargs = {'county': county}
                            election_kwargs = {}

                            for index, column_value in enumerate(row):
                                field_name = header[index]
                                lower_field_name = field_name.lower()

                                if hasattr(Voter, lower_field_name):  # parse Voter data
                                    voter_kwargs[lower_field_name] = column_value

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

                                        this_voters_elections.append(election)

                            election_lists.append(this_voters_elections)

                            voter = Voter(**voter_kwargs)
                            voters.append(voter)

                        c_end = time.time()
                        print('Done parsing CSV')
                        print('Parsing CSV took: {}'.format(c_end-c_start))

                        v_start = time.time()
                        print('Starting to insert Voters')
                        Voter.objects.bulk_create(voters)
                        v_end = time.time()
                        print('Done inserting Voters')
                        print('Writing voters took: {}'.format(v_end-v_start))

                        # Build out our middle Participation table
                        b_start = time.time()
                        print('Building participations')
                        participations = []
                        for index, election_list in enumerate(election_lists):
                            voter = voters[index]
                            for election in election_list:
                                participation = Participation(voter=voter, election=election)
                                participations.append(participation)
                        b_end = time.time()
                        print('Done building participations')
                        print('Building participations took: {}'.format(b_end-b_start))

                        p_start = time.time()
                        print('Starting to insert Participations')
                        Participation.objects.bulk_create(participations)
                        p_end = time.time()
                        print('Done inserting Participations')
                        print('Writing participations took: {}'.format(p_end-p_start))

            print('\nDone!')

            end = time.time()
            print(end - start)
