# Generated by Django 3.1.3 on 2023-09-20 13:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('production', '0016_auto_20230719_0928'),
    ]

    operations = [
        migrations.AlterField(
            model_name='productionunit',
            name='status',
            field=models.CharField(choices=[('FINISHED', 'FINISHED'), ('NOT STARTED', 'NOT STARTED'), ('PLANNED', 'PLANNED'), ('IN PROGRESS', 'IN PROGRESS')], default='NOT STARTED', max_length=32),
        ),
    ]