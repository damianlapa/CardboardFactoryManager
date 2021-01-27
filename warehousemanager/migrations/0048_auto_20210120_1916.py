# Generated by Django 3.1.2 on 2021-01-20 18:16

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('warehousemanager', '0047_auto_20210118_0544'),
    ]

    operations = [
        migrations.AlterField(
            model_name='photopolymer',
            name='name',
            field=models.CharField(default='', max_length=32),
        ),
        migrations.CreateModel(
            name='UserVisitCounter',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('page', models.CharField(max_length=32)),
                ('counter', models.PositiveIntegerField(default=0)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]