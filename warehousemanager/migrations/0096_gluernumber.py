# Generated by Django 5.0.1 on 2024-06-19 07:45

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('warehousemanager', '0095_punch_active'),
    ]

    operations = [
        migrations.CreateModel(
            name='GluerNumber',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('number', models.PositiveIntegerField()),
                ('dimensions', models.CharField(max_length=32, unique=True)),
                ('name', models.CharField(max_length=32)),
                ('comments', models.CharField(blank=True, max_length=128, null=True)),
                ('customer', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='warehousemanager.buyer')),
            ],
        ),
    ]
