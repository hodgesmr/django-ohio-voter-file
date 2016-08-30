import csv
from datetime import datetime
import os
import shutil
import urllib
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

MY_DIR = os.path.dirname(os.path.realpath(__file__))
DATETIME_STRING = datetime.utcnow().strftime("%Y_%m_%dT%H_%M_%SZ")
TMP_DIR = '{}/tmp/'.format(MY_DIR, DATETIME_STRING)
WORKING_DIR = '{}{}/'.format(TMP_DIR, DATETIME_STRING)

class Command(BaseCommand):
    def handle(self, **kwargs):

        message = ('\nThis command will completely wipe your database and download & parse the latest Ohio Voter File data.'
                   '\nThe process is very slow and can take minutes or hours depending on your network and machine. Continue? (y/n): ')

        answer = raw_input(message)

        if answer == 'y':
            management.call_command('flush', interactive=False)

            for county in COUNTIES:
                print '\nDownloading {} County data...'.format(county.title())

                url = 'ftp://sosftp.sos.state.oh.us/free/Voter/{}.zip'.format(county)

                if not os.path.exists(WORKING_DIR):
                    os.makedirs(WORKING_DIR)

                downloaded_file = '{}{}.zip'.format(WORKING_DIR, county)
                urllib.urlretrieve(url, downloaded_file)
                with zipfile.ZipFile(downloaded_file, 'r') as z:
                    z.extractall(WORKING_DIR)
                os.remove(downloaded_file)

                old_filename = '{}{}.TXT'.format(WORKING_DIR, county)
                county_filename = '{}{}_COUNTY.csv'.format(WORKING_DIR, county)
                os.rename(old_filename, county_filename)

                print 'Parsing and loading {} County data...'.format(county.title())

                with open(county_filename, 'rb') as input_file:
                    reader = csv.reader(input_file)

                    header = next(reader)

                    for row in reader:
                        elections = []
                        voter_kwargs = {'county': county}
                        election_kwargs = {}

                        for index, column_value in enumerate(row):
                            field_name = header[index]
                            lower_field_name = field_name.lower()
                            if hasattr(Voter, lower_field_name):
                                voter_kwargs[lower_field_name] = column_value
                            else:
                                if column_value:
                                    category_display, date_string = field_name.split('-')

                                    election_category = Election.CATEGORY_CHOICES_REVERSE_MAP[category_display]
                                    election_party = column_value

                                    election_kwargs['category'] = election_category
                                    election_kwargs['party'] = election_party
                                    election_kwargs['date'] = datetime.strptime(date_string, '%m/%d/%Y')

                                    try:
                                        election = Election.objects.get(**election_kwargs)
                                    except Election.DoesNotExist:
                                        election = Election.objects.create(**election_kwargs)
                                        election.save()
                                        elections.append(election)

                        # I'd love to do a bulk_create here, but the Django docs say it won't work
                        # https://docs.djangoproject.com/en/1.10/ref/models/querysets/#bulk-create
                        # Because of the ManyToManyField
                        voter = Voter.objects.create(**voter_kwargs)
                        voter.elections.add(*elections)
                        voter.save()

            print '\nCleaning up...'
            shutil.rmtree(TMP_DIR)
            print '\nDone!'
