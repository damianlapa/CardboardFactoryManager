# Generated by Django 3.1.2 on 2021-01-26 03:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('warehousemanager', '0049_auto_20210126_0350'),
    ]

    operations = [
        migrations.CreateModel(
            name='Color',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(blank=True, max_length=32, null=True)),
                ('number', models.CharField(blank=True, max_length=12, null=True)),
                ('company', models.CharField(blank=True, max_length=20, null=True)),
                ('capacity', models.PositiveIntegerField()),
            ],
        ),
        migrations.AddField(
            model_name='photopolymer',
            name='colors',
            field=models.ManyToManyField(to='warehousemanager.Color'),
        ),
    ]