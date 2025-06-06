# Generated by Django 5.0.1 on 2024-11-27 11:28

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('warehouse', '0003_warehousestockhistory'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ordersettlement',
            name='material',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='used_in_settlements', to='warehouse.warehousestock'),
        ),
    ]
