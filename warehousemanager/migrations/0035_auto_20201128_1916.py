# Generated by Django 3.1.2 on 2020-11-28 18:16

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('warehousemanager', '0034_productionprocess'),
    ]

    operations = [
        migrations.AddField(
            model_name='productionprocess',
            name='punch',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='warehousemanager.punch'),
        ),
        migrations.AlterField(
            model_name='productionprocess',
            name='machine',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='warehousemanager.machine'),
        ),
    ]
