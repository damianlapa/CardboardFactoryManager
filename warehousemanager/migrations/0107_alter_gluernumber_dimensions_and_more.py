# Generated by Django 5.0.1 on 2024-10-14 07:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('warehousemanager', '0106_alter_gluernumber_comments'),
    ]

    operations = [
        migrations.AlterField(
            model_name='gluernumber',
            name='dimensions',
            field=models.CharField(max_length=32),
        ),
        migrations.AlterUniqueTogether(
            name='gluernumber',
            unique_together={('customer', 'dimensions')},
        ),
    ]