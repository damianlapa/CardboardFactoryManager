# Generated by Django 3.1.2 on 2021-01-26 03:27

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('warehousemanager', '0050_auto_20210126_0423'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='color',
            name='capacity',
        ),
        migrations.CreateModel(
            name='ColorDelivery',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('capacity', models.PositiveIntegerField()),
                ('color', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='warehousemanager.color')),
            ],
        ),
    ]
