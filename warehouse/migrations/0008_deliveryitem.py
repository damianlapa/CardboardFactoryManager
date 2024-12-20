# Generated by Django 5.0.1 on 2024-11-12 11:12

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('warehouse', '0007_delete_deliveryitem'),
    ]

    operations = [
        migrations.CreateModel(
            name='DeliveryItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.PositiveIntegerField(default=0)),
                ('palettes_quantity', models.CharField(blank=True, max_length=128, null=True)),
                ('delivery', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='warehouse.delivery')),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='warehouse.order')),
            ],
        ),
    ]
