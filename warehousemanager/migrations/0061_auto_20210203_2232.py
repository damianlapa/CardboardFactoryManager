# Generated by Django 3.1.2 on 2021-02-03 21:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('warehousemanager', '0060_extrahour_full_day'),
    ]

    operations = [
        migrations.AddField(
            model_name='person',
            name='yearly_vacation_limit',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='absence',
            name='absence_type',
            field=models.CharField(choices=[('NN', 'Nieobecność nieusprawiedliwiona'), ('UW', 'Urlop wypoczynkowy'), ('UO', 'Urlop okolicznościowy'), ('SP', 'Spóźnienie'), ('UB', 'Urlop bezpłatny'), ('CH', 'Chorobowe'), ('KW', 'Kwarantanna')], max_length=4),
        ),
    ]
