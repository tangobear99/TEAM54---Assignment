# Generated by Django 2.1 on 2018-09-13 22:17

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('CarRentalCompany', '0003_auto_20180913_1841'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='order_create_date',
            field=models.DateField(blank=True, default=datetime.datetime.today, verbose_name='order create date'),
        ),
        migrations.AlterField(
            model_name='order',
            name='order_pickup_date',
            field=models.DateField(blank=True, default=datetime.datetime.today, verbose_name='order pickup date'),
        ),
        migrations.AlterField(
            model_name='order',
            name='order_return_date',
            field=models.DateField(blank=True, default=datetime.datetime.today, verbose_name='order return date'),
        ),
        migrations.AlterField(
            model_name='user',
            name='user_birthday',
            field=models.DateField(blank=True, default=datetime.datetime.today, verbose_name='user birthday'),
        ),
    ]