# Generated by Django 3.1.1 on 2020-09-20 14:36

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Buyer',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=32)),
            ],
        ),
        migrations.CreateModel(
            name='CardboardProvider',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=32)),
            ],
        ),
        migrations.CreateModel(
            name='Order',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('order_provider_number', models.IntegerField(unique=True)),
                ('date_of_order', models.DateTimeField()),
                ('provider', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='warehousemanager.cardboardprovider')),
            ],
        ),
        migrations.CreateModel(
            name='Person',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('first_name', models.CharField(max_length=32)),
                ('last_name', models.CharField(max_length=32)),
                ('email_address', models.EmailField(max_length=254)),
                ('telephone', models.CharField(max_length=16)),
            ],
        ),
        migrations.CreateModel(
            name='OrderItem',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('item_number', models.IntegerField()),
                ('sort', models.CharField(choices=[('201', 'FEFCO 201'), ('202', 'FEFCO 202'), ('203', 'FEFCO 203'), ('SZTANCA', 'Sztanca'), ('PRZEKLADKA', 'Przekładka')], max_length=15)),
                ('format_width', models.IntegerField()),
                ('format_height', models.IntegerField()),
                ('cardboard_type', models.CharField(choices=[('B', 'B'), ('C', 'C'), ('E', 'E'), ('BC', 'BC'), ('BE', 'BE')], max_length=8)),
                ('cardboard_weight', models.IntegerField()),
                ('dimension_one', models.IntegerField()),
                ('dimension_two', models.IntegerField()),
                ('dimension_three', models.IntegerField(null=True)),
                ('scores', models.CharField(max_length=64)),
                ('buyer', models.ManyToManyField(to='warehousemanager.Buyer')),
                ('order', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='warehousemanager.order')),
            ],
        ),
        migrations.AddField(
            model_name='cardboardprovider',
            name='employers',
            field=models.ManyToManyField(to='warehousemanager.Person'),
        ),
        migrations.AddField(
            model_name='buyer',
            name='employers',
            field=models.ManyToManyField(to='warehousemanager.Person'),
        ),
    ]
