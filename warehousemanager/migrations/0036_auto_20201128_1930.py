# Generated by Django 3.1.2 on 2020-11-28 18:30

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('warehousemanager', '0035_auto_20201128_1916'),
    ]

    operations = [
        migrations.AddField(
            model_name='productionprocess',
            name='order_item',
            field=models.ForeignKey(default=None, on_delete=django.db.models.deletion.CASCADE, to='warehousemanager.orderitem'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='productionprocess',
            name='production',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='warehousemanager.productionprocess'),
        ),
        migrations.AddField(
            model_name='productionprocess',
            name='quantity_end',
            field=models.IntegerField(default=0),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='productionprocess',
            name='quantity_start',
            field=models.IntegerField(default=0),
            preserve_default=False,
        ),
    ]