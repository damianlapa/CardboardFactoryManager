# Generated by Django 3.1.2 on 2020-11-07 12:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('warehousemanager', '0020_punch'),
    ]

    operations = [
        migrations.AddField(
            model_name='punch',
            name='type_num',
            field=models.IntegerField(default=1),
            preserve_default=False,
        ),
    ]
