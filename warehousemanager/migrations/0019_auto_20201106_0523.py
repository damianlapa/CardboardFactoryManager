# Generated by Django 3.1.2 on 2020-11-06 04:23

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('warehousemanager', '0018_extrahour'),
    ]

    operations = [
        migrations.RenameField(
            model_name='extrahour',
            old_name='date',
            new_name='extras_date',
        ),
    ]
