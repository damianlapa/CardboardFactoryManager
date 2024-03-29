# Generated by Django 3.2.9 on 2022-02-02 14:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('warehousemanager', '0088_person_occupancy_type'),
    ]

    operations = [
        migrations.AlterField(
            model_name='absence',
            name='absence_type',
            field=models.CharField(choices=[('NN', 'Nieobecność nieusprawiedliwiona'), ('UW', 'Urlop wypoczynkowy'), ('UO', 'Urlop okolicznościowy'), ('SP', 'Spóźnienie'), ('UB', 'Urlop bezpłatny'), ('CH', 'Chorobowe'), ('KW', 'Kwarantanna'), ('OP', 'Opieka nad członkiem rodziny'), ('D', 'Delegacja'), ('IN', 'Inne'), ('IZ', 'Izolacja'), ('PO', 'Postojowe')], max_length=4),
        ),
        migrations.AlterField(
            model_name='person',
            name='occupancy_type',
            field=models.CharField(choices=[('MECHANIC', 'MECHANIC'), ('PRODUCTION', 'PRODUCTION'), ('OFFICE', 'OFFICE'), ('OTHER', 'OTHER')], default='PRODUCTION', max_length=32),
        ),
    ]
