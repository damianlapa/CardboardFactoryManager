# Generated by Django 3.1.2 on 2020-11-12 03:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('warehousemanager', '0028_punchproduction_worker'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='punchproduction',
            options={'ordering': ['date_end']},
        ),
        migrations.AddField(
            model_name='orderitemquantity',
            name='is_used',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='punchproduction',
            name='cardboard',
            field=models.ManyToManyField(blank=True, to='warehousemanager.OrderItemQuantity'),
        ),
    ]