# Generated by Django 3.1.2 on 2021-01-18 04:44

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('warehousemanager', '0046_auto_20210118_0510'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='photopolymer',
            options={'ordering': ['-delivery_date']},
        ),
        migrations.AddField(
            model_name='photopolymer',
            name='name',
            field=models.CharField(default='rab 312', max_length=32),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='photopolymer',
            name='delivery_date',
            field=models.DateField(blank=True, default=datetime.datetime(2017, 1, 1, 0, 1), null=True),
        ),
    ]
