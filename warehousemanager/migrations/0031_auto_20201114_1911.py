# Generated by Django 3.1.2 on 2020-11-14 18:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('warehousemanager', '0030_cardboardprovider_shortcut'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='buyer',
            options={'ordering': ['name']},
        ),
        migrations.AlterModelOptions(
            name='cardboardprovider',
            options={'ordering': ['name']},
        ),
        migrations.AlterModelOptions(
            name='order',
            options={'ordering': ['date_of_order', 'order_provider_number']},
        ),
        migrations.AlterModelOptions(
            name='orderitem',
            options={'ordering': ['order__provider__name', 'order__order_provider_number', 'item_number']},
        ),
        migrations.AlterModelOptions(
            name='person',
            options={'ordering': ['last_name', 'first_name']},
        ),
        migrations.AlterField(
            model_name='order',
            name='date_of_order',
            field=models.DateField(),
        ),
    ]
