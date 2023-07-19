# Generated by Django 3.1.3 on 2023-07-19 09:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('production', '0015_auto_20230718_1129'),
    ]

    operations = [
        migrations.AddField(
            model_name='productionorder',
            name='ordered_quantity',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='productionorder',
            name='status',
            field=models.CharField(choices=[('ORDERED', 'ORDERED'), ('UNCOMPLETED', 'UNCOMPLETED'), ('COMPLETED', 'COMPLETED'), ('PLANNED', 'PLANNED'), ('FINISHED', 'FINISHED')], default='UNCOMPLETED', max_length=32),
        ),
    ]