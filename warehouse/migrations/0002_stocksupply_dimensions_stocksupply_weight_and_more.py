# Generated by Django 5.0.1 on 2024-11-08 09:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('warehouse', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='stocksupply',
            name='dimensions',
            field=models.CharField(blank=True, max_length=32, null=True),
        ),
        migrations.AddField(
            model_name='stocksupply',
            name='weight',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='stock',
            name='supplies',
            field=models.ManyToManyField(blank=True, null=True, to='warehouse.stocksupply'),
        ),
        migrations.AlterField(
            model_name='warehouse',
            name='stocks',
            field=models.ManyToManyField(blank=True, null=True, to='warehouse.stock'),
        ),
    ]
