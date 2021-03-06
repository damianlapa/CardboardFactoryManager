# Generated by Django 3.1.2 on 2021-03-05 19:24

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('warehousemanager', '0068_uservisitcounter'),
    ]

    operations = [
        migrations.CreateModel(
            name='Contract',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('type', models.CharField(choices=[('UOP', 'Umowa o pracę'), ('UZ', 'Umowa zlecenie')], max_length=8)),
                ('date_start', models.DateField()),
                ('date_end', models.DateField(blank=True, null=True)),
                ('salary', models.DecimalField(decimal_places=2, max_digits=7)),
                ('worker', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='warehousemanager.person')),
            ],
        ),
    ]
