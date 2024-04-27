# Generated by Django 5.0.1 on 2024-02-27 12:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('warehousemanager', '0092_auto_20230920_1300'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='contract',
            options={'ordering': ['worker', 'date_end']},
        ),
        migrations.AlterField(
            model_name='contract',
            name='type',
            field=models.CharField(choices=[('UOP', 'Umowa o pracę'), ('UZ', 'Umowa zlecenie'), ('FZ', 'Firma zewnętrzna')], max_length=8),
        ),
    ]
