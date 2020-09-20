# Generated by Django 3.1.1 on 2020-09-20 14:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('warehousemanager', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='buyer',
            name='employers',
            field=models.ManyToManyField(null=True, to='warehousemanager.Person'),
        ),
        migrations.AlterField(
            model_name='cardboardprovider',
            name='employers',
            field=models.ManyToManyField(null=True, to='warehousemanager.Person'),
        ),
        migrations.AlterField(
            model_name='orderitem',
            name='item_number',
            field=models.IntegerField(unique=True),
        ),
    ]
