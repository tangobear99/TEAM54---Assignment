# Generated by Django 2.1 on 2018-10-11 10:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('CarRentalCompany', '0010_userprofile_customer_number'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='order_checked',
            field=models.BooleanField(default=True, verbose_name='checked'),
        ),
    ]