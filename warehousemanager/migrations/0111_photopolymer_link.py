# Generated by Django 5.0.1 on 2025-03-31 07:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('warehousemanager', '0110_colorbucket'),
    ]

    operations = [
        migrations.AddField(
            model_name='photopolymer',
            name='link',
            field=models.URLField(blank=True, null=True),
        ),
    ]
