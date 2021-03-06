# Generated by Django 3.1.2 on 2020-11-09 19:16

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('warehousemanager', '0026_auto_20201109_1824'),
    ]

    operations = [
        migrations.AlterField(
            model_name='orderitem',
            name='cardboard_type',
            field=models.CharField(choices=[('B', 'B'), ('C', 'C'), ('E', 'E'), ('BC', 'BC'), ('EB', 'EB')], max_length=8),
        ),
        migrations.AlterField(
            model_name='punch',
            name='cardboard',
            field=models.CharField(choices=[('B', 'B'), ('C', 'C'), ('E', 'E'), ('BC', 'BC'), ('EB', 'EB')], max_length=4),
        ),
        migrations.CreateModel(
            name='PunchProduction',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_start', models.DateField()),
                ('date_end', models.DateField()),
                ('quantity', models.IntegerField()),
                ('comments', models.CharField(blank=True, max_length=128)),
                ('punch', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='warehousemanager.punch')),
            ],
        ),
    ]
