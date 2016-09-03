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

    CATEGORY_CHOICES_REVERSE_MAP = {_[1]:_[0] for _ in CATEGORY_CHOICES}

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

    PARTY_CHOICES_SET = set([_[0] for _ in PARTY_CHOICES])

    id = models.CharField(primary_key=True, max_length=64, null=False)
    category = models.IntegerField(db_index=True, null=False, blank=False, choices=CATEGORY_CHOICES)
    date = models.DateField(db_index=True, null=False, blank=False)
    party = models.CharField(max_length=512, db_index=True, null=False, blank=False, choices=PARTY_CHOICES)

    @property
    def voters(self):
        return [obj.voter for obj in self.participations.all()]

    def __str__(self):
        if self.party != self.PARTY_NONE:
            output = '{} {} {}'.format(self.date.strftime('%Y-%m-%d'),
                                       self.get_party_display(),
                                       self.get_category_display(),
                                       )
        else:
            output = '{} {}'.format(self.date.strftime('%Y-%m-%d'),
                                       self.get_category_display(),
                                       )
        return output

    class Meta:
        #unique_together = ('category', 'date', 'party')
        ordering = ('-date', 'party')


class Voter(models.Model):
    sos_voterid = models.CharField(max_length=512, primary_key=True, null=False)
    county_number = models.IntegerField(null=True)
    county_id = models.CharField(max_length=512, null=True)
    last_name = models.CharField(max_length=512, null=True)
    first_name = models.CharField(max_length=512, null=True)
    middle_name = models.CharField(max_length=512, null=True)
    suffix = models.CharField(max_length=512, null=True)
    date_of_birth = models.DateField(null=True)
    registration_date = models.DateField(null=True)
    voter_status = models.CharField(max_length=512, null=True)
    party_affiliation = models.CharField(max_length=512, null=True)
    residential_address1 = models.CharField(max_length=512, null=True)
    residential_secondary_addr = models.CharField(max_length=512, null=True)
    residential_city = models.CharField(max_length=512, null=True)
    residential_state = models.CharField(max_length=512, null=True)
    residential_zip = models.CharField(max_length=512, null=True)
    residential_zip_plus4 = models.CharField(max_length=512, null=True)
    residential_country = models.CharField(max_length=512, null=True)
    residential_postalcode = models.CharField(max_length=512, null=True)
    mailing_address1 = models.CharField(max_length=512, null=True)
    mailing_secondary_address = models.CharField(max_length=512, null=True)
    mailing_city = models.CharField(max_length=512, null=True)
    mailing_state = models.CharField(max_length=512, null=True)
    mailing_zip = models.CharField(max_length=512, null=True)
    mailing_zip_plus4 = models.CharField(max_length=512, null=True)
    mailing_country = models.CharField(max_length=512, null=True)
    mailing_postal_code = models.CharField(max_length=512, null=True)
    career_center = models.CharField(max_length=512, null=True)
    city = models.CharField(max_length=512, null=True)
    city_school_district = models.CharField(max_length=512, null=True)
    county_court_district = models.CharField(max_length=512, null=True)
    congressional_district = models.IntegerField(null=True)
    court_of_appeals = models.CharField(max_length=512, null=True)
    edu_service_center_district = models.CharField(max_length=512, null=True)
    exempted_vill_school_district = models.CharField(max_length=512, null=True)
    library = models.CharField(max_length=512, null=True)
    local_school_district = models.CharField(max_length=512, null=True)
    municipal_court_district = models.CharField(max_length=512, null=True)
    precinct_name = models.CharField(max_length=512, null=True)
    precinct_code = models.CharField(max_length=512, null=True)
    state_board_of_education = models.CharField(max_length=512, null=True)
    state_representative_district = models.IntegerField(null=True)
    state_senate_district = models.IntegerField(null=True)
    township = models.CharField(max_length=512, null=True)
    village = models.CharField(max_length=512, null=True)
    ward = models.CharField(max_length=512, null=True)
    county = models.CharField(max_length=512, null=True)

    @property
    def elections(self):
        return [obj.election for obj in self.participations.all()]

    def __str__(self):
        return '{} - {} {} {}'.format(self.sos_voterid,
                                      self.first_name,
                                      self.middle_name,
                                      self.last_name,
                                      )

    class Meta:
        ordering = ('last_name', 'first_name', 'middle_name')


class Participation(models.Model):
    election = models.ForeignKey(Election, related_name='participations', on_delete=models.CASCADE)
    voter = models.ForeignKey(Voter, related_name='participations', on_delete=models.CASCADE)

    class Meta:
        unique_together = ('election', 'voter')
