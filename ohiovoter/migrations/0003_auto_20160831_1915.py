# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2016-08-31 19:15
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ohiovoter', '0002_auto_20160830_1844'),
    ]

    operations = [
        migrations.AlterField(
            model_name='election',
            name='id',
            field=models.CharField(max_length=64, primary_key=True, serialize=False),
        ),
    ]