# Generated by Django 3.1.2 on 2021-03-05 21:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('warehousemanager', '0071_contract_extra_info'),
    ]

    operations = [
        migrations.AddField(
            model_name='contract',
            name='position',
            field=models.CharField(default='ok', max_length=64),
            preserve_default=False,
        ),
    ]