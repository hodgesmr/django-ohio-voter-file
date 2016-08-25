from django.db import models


class Voter(models.Model):
    pass


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

    class Meta:
        unique_together = ('category', 'date', 'party')
