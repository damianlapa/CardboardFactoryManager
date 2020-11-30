# Generated by Django 3.1.2 on 2020-11-20 04:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('warehousemanager', '0031_auto_20201114_1911'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='delivery',
            options={'ordering': ['date_of_delivery']},
        ),
        migrations.AddField(
            model_name='orderitem',
            name='is_completed',
            field=models.BooleanField(default=False),
        ),
    ]
