# Generated by Django 3.1.7 on 2021-04-08 17:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('warehousemanager', '0079_palettecustomer_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='palettecustomer',
            name='exchange',
            field=models.BooleanField(default=False),
        ),
    ]