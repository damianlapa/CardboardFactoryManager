# Generated by Django 3.2.9 on 2022-10-14 12:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('warehousemanager', '0091_auto_20221014_1224'),
    ]

    operations = [
        migrations.AlterField(
            model_name='photopolymer',
            name='identification_number',
            field=models.IntegerField(),
        ),
    ]