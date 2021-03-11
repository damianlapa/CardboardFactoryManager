# Generated by Django 3.1.2 on 2021-03-06 19:07

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('warehousemanager', '0073_person_medical_examination'),
    ]

    operations = [
        migrations.CreateModel(
            name='Reminder',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=64)),
                ('create_date', models.DateField()),
                ('sent_date', models.DateField(blank=True, null=True)),
                ('worker', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='warehousemanager.person')),
            ],
        ),
    ]
