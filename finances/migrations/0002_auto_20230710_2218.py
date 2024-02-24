# Generated by Django 3.1.3 on 2023-07-10 22:18

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('finances', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Customer',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=128)),
                ('tax_number', models.CharField(max_length=10, unique=True)),
                ('description', models.CharField(blank=True, max_length=512, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='ProductProduction',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField()),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='finances.product')),
            ],
        ),
        migrations.CreateModel(
            name='ProductSell',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.IntegerField()),
                ('price_per_unit', models.DecimalField(decimal_places=3, max_digits=12)),
                ('date', models.DateField()),
                ('customer', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='finances.customer')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='finances.product')),
            ],
        ),
        migrations.CreateModel(
            name='ProductResourceProduction',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.DecimalField(decimal_places=2, max_digits=9)),
                ('product_production', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='finances.productproduction')),
                ('resource', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='finances.resource')),
            ],
        ),
        migrations.AddField(
            model_name='productproduction',
            name='resources',
            field=models.ManyToManyField(through='finances.ProductResourceProduction', to='finances.Resource'),
        ),
    ]
