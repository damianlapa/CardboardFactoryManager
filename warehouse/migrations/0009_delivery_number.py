# Generated by Django 5.0.1 on 2024-11-13 08:24 - not added to git why?

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('warehouse', '0008_deliveryitem'),
    ]

    operations = [
        migrations.AddField(
            model_name='delivery',
            name='number',
            field=models.CharField(default='', max_length=64),
        ),
    ]
