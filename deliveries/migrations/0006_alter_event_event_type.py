# Generated by Django 5.0.1 on 2024-08-28 08:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('deliveries', '0005_deliveryitem_cardboard_order'),
    ]

    operations = [
        migrations.AlterField(
            model_name='event',
            name='event_type',
            field=models.CharField(choices=[('PLANOWANA DOSTAWA', 'PLANOWANA DOSTAWA'), ('ZREALIZOWANA DOSTAWA', 'ZREALIZOWANA DOSTAWA'), ('SPOTKANIE', 'SPOTKANIE'), ('ODBIÓR OSOBISTY', 'ODBIÓR OSOBISTY'), ('SPEDYCJA', 'SPEDYCJA'), ('INNE', 'INNE')], max_length=32),
        ),
    ]
