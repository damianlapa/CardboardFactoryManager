# Generated by Django 3.1.2 on 2020-10-26 20:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('warehousemanager', '0013_note'),
    ]

    operations = [
        migrations.AddField(
            model_name='note',
            name='genre',
            field=models.CharField(choices=[('Ordinary', 'Ordinary'), ('To Do List', 'To Do List'), ('Journal', 'Journal'), ('Notice', 'Notice')], default='Ordinary', max_length=16),
            preserve_default=False,
        ),
    ]
