# Generated by Django 3.1.2 on 2021-01-27 04:35

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('warehousemanager', '0054_auto_20210126_1949'),
    ]

    operations = [
        migrations.RenameField(
            model_name='colordelivery',
            old_name='capacity',
            new_name='weight',
        ),
        migrations.AlterField(
            model_name='color',
            name='availability',
            field=models.DecimalField(decimal_places=1, default=0, max_digits=4),
        ),
        migrations.CreateModel(
            name='ColorUsage',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('value', models.DecimalField(decimal_places=1, max_digits=3)),
                ('color', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='warehousemanager.color')),
            ],
        ),
        migrations.AddField(
            model_name='productionprocess',
            name='colors',
            field=models.ManyToManyField(to='warehousemanager.ColorUsage'),
        ),
    ]
