# django-ohio-voter-file

The Ohio Secretary Of State provides a [comprehensive data set](http://www6.sos.state.oh.us/ords/f?p=111:1) of Ohio voter registrations and voting history that dates back to 2000. In total, the CSVs hold roughly 4 GB of voter data. You can only get so far with Excel or `grep`, and as the portal states:

>it is advised that a database application be utilized to load and work with the data

**django-ohio-voter-file** will download the CSV data, parse it into relationships, load it into a PostgreSQL, and utilize the Django ORM for easy querying.

## Contents

- [Installation](#installation)
- [Usage](#usage)
  - [Import Data](#import-data)
  - [Data Model](#data-model)
  - [Query Examples](#query-examples)
- [Anything else I should know?](#anything-else-i-should-know)
- [License](#license)

## Installation

**django-ohio-voter-file** is built with _Django 1.10_, _PostgreSQL 9.5_, and _Python 3.5_.

You may certainly clone this repository and run the Django commands manually, but Docker makes it nice and easy to get all your dependencies. You can find the [various Docker install options](https://docs.docker.com/engine/installation/) for your platform and get rolling.

This project relies on PostgreSQL and thus assumes you have a PostgreSQL database up and running. You should have a database `ohiovoter` to which you can read/write.

## Usage

**django-ohio-voter-file** is best used within an interactive shell. Create a Docker container and launch bash:

```sh
docker run --name ohiovoter \
  -e DB_HOST=<your-host> \
  -e DB_USER=<your-user> \
  -e DB_PASS=<your-password> \
  -e DB_PORT=<your-port> \
  -i -t hodgesmr/ohiovoter /bin/bash
```

You must pass four environment variables to the container to reference your PostgreSQL server: `DB_HOST`, `DB_USER`, `DB_PASS`, and `DB_PORT`.

**Note:** it is assumed that PostgreSQL has a database `ohiovoter` to which your user can read/write.

### Import Data

The first step is to download the Ohio Voter data from the [Secretary of State FTP](http://www6.sos.state.oh.us/ords/f?p=111:1). This is done for you with the provided `import_data` Django management command. From within a running container:

```sh
python manage.py import_data
```

**WARNING:** This is a destructive operation. Since the voter file is a snapshot of _current_ registrants, there is no effort to keep a historic lineage or update old records with new data. Every time you import, the old database will be flushed (removing all data) and replaced with the most recent data.

**Note:** This operation can take a _long time_ and will vary depending on your hardware and network connections. As a benchmark, I ran the import on an [AWS i2.2xlarge EC2](http://docs.aws.amazon.com/AWSEC2/latest/UserGuide/i2-instances.html) instance, with PostgreSQL running on the same box. With this provisioning I was able to load all of the data in just under 75 minutes. This resulted in 41 GB of data loaded into PostgreSQL. On my last run of the import, the table sizes were:

| table                   | row count  |
|-------------------------|------------|
| ohiovoter_election      | 149        |
| ohiovoter_voter         | 7,724,006  |
| ohiovoter_participation | 71,256,665 |

### Data Model

Three models are represented upon import: **Election**, **Voter**, and **Participation**.

#### Election

The **Election** model represents a specific real-world election.

| name     | type            |
|----------|-----------------|
| id       | CharField       |
| category | IntegerField    |
| date     | DateField       |
| party    | CharField       |
| voters   | ManyToManyField |

The `id` field is a generated unique id that acts as a primary key.
The `voters` field uses the **Participation** table as a passthrough.

`category` is an enum defined as:

```python
CATEGORY_GENERAL = 1
CATEGORY_PRIMARY = 2
CATEGORY_SPECIAL = 3
```

`party` is an enum defined as:

```python
PARTY_CONSTITUTION = 'C'
PARTY_DEMOCRAT = 'D'
PARTY_REFORM = 'E'
PARTY_GREEN = 'G'
PARTY_LIBERTARIAN = 'L'
PARTY_NATURAL_LAW = 'N'
PARTY_REPUBLICAN = 'R'
PARTY_SOCIALIST = 'S'
PARTY_NONE = 'X'
```

Typically, only primary elections (`CATEGORY_PRIMARY`) will have a `party` field that is not `X` (`PARTY_NONE`).

#### Voter

The **Voter** model almost exactly mirrors the Secretary of State Voter representation as defined in the [Voter File Layout](http://bit.ly/2d5mco0). I've added a `county` field that was inferred from the source CSV.

| name                          | type            |
|-------------------------------|-----------------|
| sos_voterid                   | CharField       |
| county_number                 | IntegerField    |
| county_id                     | CharField       |
| last_name                     | CharField       |
| first_name                    | CharField       |
| middle_name                   | CharField       |
| suffix                        | CharField       |
| date_of_birth                 | DateField       |
| registration_date             | DateField       |
| voter_status                  | CharField       |
| party_affiliation             | CharField       |
| residential_address1          | CharField       |
| residential_secondary_addr    | CharField       |
| residential_city              | CharField       |
| residential_state             | CharField       |
| residential_zip               | CharField       |
| residential_zip_plus4         | CharField       |
| residential_country           | CharField       |
| residential_postalcode        | CharField       |
| mailing_address1              | CharField       |
| mailing_secondary_address     | CharField       |
| mailing_city                  | CharField       |
| mailing_state                 | CharField       |
| mailing_zip                   | CharField       |
| mailing_zip_plus4             | CharField       |
| mailing_country               | CharField       |
| mailing_postal_code           | CharField       |
| career_center                 | CharField       |
| city                          | CharField       |
| city_school_district          | CharField       |
| county_court_district         | CharField       |
| congressional_district        | IntegerField    |
| court_of_appeals              | CharField       |
| edu_service_center_district   | CharField       |
| exempted_vill_school_district | CharField       |
| library                       | CharField       |
| local_school_district         | CharField       |
| municipal_court_district      | CharField       |
| precinct_name                 | CharField       |
| precinct_code                 | CharField       |
| state_board_of_education      | CharField       |
| state_representative_district | IntegerField    |
| state_senate_district         | IntegerField    |
| township                      | CharField       |
| village                       | CharField       |
| ward                          | CharField       |
| county                        | CharField       |
| elections                     | ManyToManyField |

The `sos_voterid` field serves as the primary key.
The `elections` field uses the **Participation** table as a passthrough.

#### Participation

The **Participation** model simply acts as a many-to-many table between **Election** and **Voter**. If a **Voter** participated in a given **Election** there will be a corresponding row in **Participation**.

| name     | type         |
|----------|--------------|
| id       | IntegerField |
| election | ForeignKey   |
| voter    | ForeignKey   |

### Query Examples

After you have imported the data, you can start running queries. Of course, you can use SQL if you'd like, but you can also leverage the Django ORM.

From within your running container, open a Django shell:

```sh
python manage.py shell
```

Here are some example queries:

```python
from ohiovoter.models import Voter, Election
from datetime import datetime


# How many registered voters are there?
Voter.objects.all().count()
7724006


# What is the registration status of Matt Hodges?
Voter.objects.get(last_name="HODGES", first_name="MATTHEW", middle_name="ROBERT").voter_status
'ACTIVE'


# Give me all the voters in Jefferson county
jefferson_county_voters = Voter.objects.filter(county="JEFFERSON")


# Give me all the voters who participated in the 2012 general election
the_date = datetime.strptime('2012-11-06', '%Y-%m-%d')
the_election = Election.objects.get(date=the_date)
voters = the_election.voters.all()


# How many of 2016 Republican Primary Voters participated in the Democratic
# primary the last time they voted in a primary?
republican_primary_date = datetime.strptime('2016-03-15', '%Y-%m-%d')
republican_primary = Election.objects.get(
  date=republican_primary_date,
  party=Election.PARTY_REPUBLICAN
)
republican_voters = republican_primary.voters.only('sos_voterid')
count = 0
for republican_voter in republican_voters:
    past_primaries = republican_voter.elections.filter(
      date__lt=republican_primary_date,
      category=Election.CATEGORY_PRIMARY
    ).only('party')
    for past_primary in past_primaries:
        if past_primary.party != Election.PARTY_NONE:
            if past_primary.party == Election.PARTY_DEMOCRAT:
                count += 1
            break
print(count)
312054
```

## Anything else I should know?

You'll note that some queries may take a _long time_. This is due to a combination of [table size](#import-data) and non-optimized database indexes. You can likely see higher performance for your queries if you create indexes around the data that is interesting to you.

You should also read the [License](#license) section below if you plan to do anything substantial with the data.

## License

All code is provided under the [BSD 3-Clause license](https://github.com/hodgesmr/django-ohio-voter-file/blob/master/LICENSE). However, use of the Ohio Voter File data is subject to the protections outlined in the [Ohio Sunshine Laws Manual](http://www.ohioattorneygeneral.gov/yellowbook).

I am not a lawyer, so don't ask me what is or is not an appropriate use of the data. You should talk to your own legal advisor(s) and/or [contact the Office of the Secretary of State](http://www.sos.state.oh.us/SOS/agency/contactall.aspx).

## A Matt Hodges project

This project is maintained by [@hodgesmr](http://twitter.com/hodgesmr).

_Please use it for good, not evil._
