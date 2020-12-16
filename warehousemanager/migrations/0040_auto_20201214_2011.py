# Generated by Django 3.1.2 on 2020-12-14 19:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('warehousemanager', '0039_auto_20201210_0524'),
    ]

    operations = [
        migrations.CreateModel(
            name='SpreadsheetCopy',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('gs_id', models.CharField(max_length=48)),
                ('created', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.AlterField(
            model_name='buyer',
            name='shortcut',
            field=models.CharField(max_length=8),
        ),
    ]
