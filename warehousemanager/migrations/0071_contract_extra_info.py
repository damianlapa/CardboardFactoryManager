# Generated by Django 3.1.2 on 2021-03-05 21:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('warehousemanager', '0070_auto_20210305_2024'),
    ]

    operations = [
        migrations.AddField(
            model_name='contract',
            name='extra_info',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]