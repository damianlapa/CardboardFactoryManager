# Generated by Django 3.1.3 on 2023-07-03 07:49

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0009_auto_20230615_1859'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='cardboardprice',
            name='cardboard',
        ),
        migrations.RemoveField(
            model_name='cardboardpurchase',
            name='cardboard',
        ),
        migrations.RemoveField(
            model_name='cardboardpurchase',
            name='supplier',
        ),
        migrations.RemoveField(
            model_name='delivery',
            name='supplier',
        ),
        migrations.RemoveField(
            model_name='deliveryunit',
            name='delivery',
        ),
        migrations.RemoveField(
            model_name='deliveryunit',
            name='order_unit',
        ),
        migrations.RemoveField(
            model_name='order',
            name='customer',
        ),
        migrations.RemoveField(
            model_name='orderunit',
            name='order',
        ),
        migrations.RemoveField(
            model_name='orderunit',
            name='product',
        ),
        migrations.DeleteModel(
            name='Cardboard',
        ),
        migrations.DeleteModel(
            name='CardboardPrice',
        ),
        migrations.DeleteModel(
            name='CardboardPurchase',
        ),
        migrations.DeleteModel(
            name='Customer',
        ),
        migrations.DeleteModel(
            name='Delivery',
        ),
        migrations.DeleteModel(
            name='DeliveryUnit',
        ),
        migrations.DeleteModel(
            name='Order',
        ),
        migrations.DeleteModel(
            name='OrderUnit',
        ),
        migrations.DeleteModel(
            name='Product',
        ),
    ]
