# Generated by Django 5.0.1 on 2024-07-25 13:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('warehousemanager', '0102_alter_punch_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='person',
            name='date26',
            field=models.DateField(blank=True, null=True),
        ),
    ]