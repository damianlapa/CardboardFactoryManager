# Generated by Django 5.0.1 on 2024-07-05 10:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('warehousemanager', '0097_photopolymer_dimensions'),
    ]

    operations = [
        migrations.AlterField(
            model_name='photopolymer',
            name='identification_number',
            field=models.CharField(max_length=16),
        ),
    ]