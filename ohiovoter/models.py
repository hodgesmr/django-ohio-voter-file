from django.db import models


class Election(models.Model):
    CATEGORY_GENERAL = 1
    CATEGORY_PRIMARY = 2
    CATEGORY_SPECIAL = 3

    CATEGORY_CHOICES = (
        (CATEGORY_GENERAL, 'GENERAL'),
        (CATEGORY_PRIMARY, 'PRIMARY'),
        (CATEGORY_SPECIAL, 'SPECIAL'),
    )

    PARTY_CONSTITUTION = 'C'
    PARTY_DEMOCRAT = 'D'
    PARTY_REFORM = 'E'
    PARTY_GREEN = 'G'
    PARTY_LIBERTARIAN = 'L'
    PARTY_NATURAL_LAW = 'N'
    PARTY_REPUBLICAN = 'R'
    PARTY_SOCIALIST = 'S'
    PARTY_NONE = 'X'

    PARTY_CHOICES = (
        (PARTY_CONSTITUTION, 'CONSTITUTION'),
        (PARTY_DEMOCRAT, 'DEMOCRAT'),
        (PARTY_REFORM, 'REFORM'),
        (PARTY_GREEN, 'GREEN'),
        (PARTY_LIBERTARIAN, 'LIBERTARIAN'),
        (PARTY_NATURAL_LAW, 'NATURAL_LAW'),
        (PARTY_REPUBLICAN, 'REPUBLICAN'),
        (PARTY_SOCIALIST, 'SOCIALIST'),
        (PARTY_NONE, 'N/A'),
    )

    category = models.IntegerField(db_index=True, null=False, blank=False, choices=CATEGORY_CHOICES)
    date = models.DateField(db_index=True, null=False, blank=False)
    party = models.CharField(db_index=True, null=False, blank=False, choices=PARTY_CHOICES)

    def __str__(self):
        if self.party != self.PARTY_NONE:
            output = '{} {} {}'.format(self.date.strftime('%Y-%m-%d'),
                                       self.party.get_display(),
                                       self.category.get_display(),
                                       )

    class Meta:
        unique_together = ('category', 'date', 'party')
        ordering('-date', 'party')


class Voter(models.Model):
    sos_voterid = models.CharField(primary_key=True, null=True)
    county_number = models.IntegerField(null=True)
    county_id = models.CharField(null=True)
    last_name = models.CharField(null=True)
    first_name = models.CharField(null=True)
    middle_name = models.CharField(null=True)
    suffix = models.CharField(null=True)
    date_of_birth = models.DateField(null=True)
    registration_date = models.DateField(null=True)
    voter_status = models.CharField(null=True)
    party_affiliation = models.CharField(null=True)
    residential_address1 = models.CharField(null=True)
    residential_secondary_addr = models.CharField(null=True)
    residential_city = models.CharField(null=True)
    residential_state = models.CharField(null=True)
    residential_zip = models.CharField(null=True)
    residential_zip_plus4 = models.CharField(null=True)
    residential_country = models.CharField(null=True)
    residential_postalcode = models.CharField(null=True)
    mailing_address1 = models.CharField(null=True)
    mailing_secondary_address = models.CharField(null=True)
    mailing_city = models.CharField(null=True)
    mailing_state = models.CharField(null=True)
    mailing_zip = models.CharField(null=True)
    mailing_zip_plus4 = models.CharField(null=True)
    mailing_country = models.CharField(null=True)
    mailing_postal_code = models.CharField(null=True)
    career_center = models.CharField(null=True)
    city = models.CharField(null=True)
    city_school_district = models.CharField(null=True)
    county_court_district = models.CharField(null=True)
    congressional_district = models.IntegerField(null=True)
    court_of_appeals = models.CharField(null=True)
    edu_service_center_district = models.CharField(null=True)
    exempted_vill_school_district = models.CharField(null=True)
    library = models.CharField(null=True)
    local_school_district = models.CharField(null=True)
    municipal_court_district = models.CharField(null=True)
    precinct_name = models.CharField(null=True)
    precinct_code = models.CharField(null=True)
    state_board_of_education = models.CharField(null=True)
    state_representative_district = models.IntegerField(null=True)
    state_senate_district = models.IntegerField(null=True)
    township = models.CharField(null=True)
    village = models.CharField(null=True)
    ward = models.CharField(null=True)
    county = models.CharField(null=True)
    elections = models.ManyToManyField(Election)

    def __str__(self):
        return '{} - {} {} {}'.format(self.sos_voterid,
                                      self.first_name,
                                      self.middle_name,
                                      self.last_name,
                                      )

    class Meta:
        ordering('last_name', 'first_name', 'middle_name')
