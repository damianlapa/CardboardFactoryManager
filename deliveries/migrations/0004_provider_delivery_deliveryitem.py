# Generated by Django 5.0.1 on 2024-04-17 14:09

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('deliveries', '0003_auto_20230703_0743'),
        ('orders', '0015_orderproduct_cardboard'),
        ('warehousemanager', '0094_alter_photopolymer_name'),
    ]

    operations = [
        migrations.CreateModel(
            name='Provider',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=128)),
                ('shortcut', models.CharField(max_length=16)),
            ],
        ),
        migrations.CreateModel(
            name='Delivery',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField()),
                ('car_number', models.CharField(max_length=32)),
                ('driver', models.CharField(max_length=64)),
                ('phone', models.CharField(max_length=24)),
                ('palette_number', models.PositiveIntegerField(default=0)),
                ('worker', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='warehousemanager.person')),
                ('provider', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='deliveries.provider')),
            ],
        ),
        migrations.CreateModel(
            name='DeliveryItem',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.PositiveIntegerField()),
                ('delivery', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='deliveries.delivery')),
                ('order_item', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='orders.orderproduct')),
            ],
        ),
    ]
