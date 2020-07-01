import logging
import os
from setuptools import setup

import ohiovoter

logger = logging.getLogger(__name__)

PWD = os.path.abspath(os.path.dirname(__file__))
README_PATH = os.path.join(PWD, 'README.md')
VERSION = ohiovoter.__version__


def get_readme():
    with open(README_PATH) as readme:
        return readme.read()


REQUIREMENTS = [
    'Django==1.10.7',
    'psycopg2==2.6.*',
]


setup(
    name='django-ohio-voter-file',
    version=VERSION,
    description='The Ohio Voter File behind the Django ORM',
    url='https://github.com/hodgesmr/django-ohio-voter-file',
    long_description=get_readme(),
    author='Matt Hodges',
    packages=['ohiovoter'],
    zip_safe=False,
    install_requires=REQUIREMENTS,
    include_package_data=True,
    classifiers=[
        'Programming Language :: Python :: 3.5',
    ]
)
