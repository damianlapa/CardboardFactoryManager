# Generated by Django 3.2.16 on 2023-02-20 14:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0005_auto_20230220_0019'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='number',
            field=models.CharField(default='', max_length=32),
        ),
    ]
