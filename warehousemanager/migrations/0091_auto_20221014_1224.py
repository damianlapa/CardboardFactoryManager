# Generated by Django 3.2.9 on 2022-10-14 12:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('warehousemanager', '0090_alter_absence_absence_type'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='photopolymer',
            options={'ordering': ['identification_number']},
        ),
        migrations.AlterModelOptions(
            name='punch',
            options={'ordering': ['type', 'type_letter', 'type_num']},
        ),
        migrations.AlterField(
            model_name='photopolymer',
            name='identification_number',
            field=models.DecimalField(decimal_places=1, max_digits=4),
        ),
    ]