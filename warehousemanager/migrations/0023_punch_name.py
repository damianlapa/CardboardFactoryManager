# Generated by Django 3.1.2 on 2020-11-09 03:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('warehousemanager', '0022_auto_20201107_1836'),
    ]

    operations = [
        migrations.AddField(
            model_name='punch',
            name='name',
            field=models.CharField(default='', max_length=24),
        ),
    ]
