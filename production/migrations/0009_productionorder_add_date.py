# Generated by Django 3.2.16 on 2023-03-01 19:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('production', '0008_auto_20220621_0907'),
    ]

    operations = [
        migrations.AddField(
            model_name='productionorder',
            name='add_date',
            field=models.DateTimeField(auto_created=True, default='2022-01-01 00:00:00'),
            preserve_default=False,
        ),
    ]