# Generated by Django 3.2.16 on 2023-03-01 19:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('production', '0009_productionorder_add_date'),
    ]

    operations = [
        migrations.AlterField(
            model_name='productionorder',
            name='add_date',
            field=models.DateTimeField(auto_created=True, auto_now_add=True),
        ),
    ]
