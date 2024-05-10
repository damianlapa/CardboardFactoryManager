# Generated by Django 3.1.3 on 2023-07-08 20:48

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Expense',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=12)),
                ('date', models.DateField()),
                ('title', models.CharField(max_length=64)),
                ('description', models.CharField(blank=True, max_length=248, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Product',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=64, unique=True)),
                ('product_type', models.CharField(choices=[('BOX', 'BOX')], max_length=32)),
                ('quantity', models.IntegerField(default=0)),
                ('description', models.CharField(blank=True, max_length=248, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Resource',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=64)),
                ('resource_type', models.CharField(choices=[('CARDBOARD', 'CARDBOARD'), ('PACKAGING TAPE', 'PACKAGING TAPE'), ('STRETCH FOIL', 'STRETCH FOIL'), ('GLUE', 'GLUE'), ('BINDING TAPE', 'BINDING TAPE'), ('OTHERS', 'OTHERS')], max_length=32)),
                ('unit', models.CharField(choices=[('PIECE', 'PIECE'), ('KG', 'KG'), ('M2', 'M2'), ('HOUR', 'HOUR')], max_length=32)),
                ('quantity', models.DecimalField(decimal_places=2, max_digits=9)),
                ('price', models.DecimalField(decimal_places=3, max_digits=12)),
                ('date', models.DateField()),
                ('used', models.BooleanField(default=False)),
                ('description', models.CharField(blank=True, max_length=256, null=True)),
            ],
        ),
    ]