# Generated by Django 3.1.2 on 2020-11-07 12:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('warehousemanager', '0019_auto_20201106_0523'),
    ]

    operations = [
        migrations.CreateModel(
            name='Punch',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('type', models.CharField(choices=[('427', 'FEFCO 427'), ('426', 'FEFCO 426'), ('421', 'FEFCO 421'), ('201', 'FEFCO 201'), ('SWT', 'Spody, wieka, tacki'), ('KR', 'Krata'), ('NR', 'Narożnik'), ('PDK', 'Pozostałe do klejenia'), ('WK', 'Wkład'), ('INNE', 'Inne')], max_length=8)),
                ('dimension_one', models.IntegerField(blank=True, null=True)),
                ('dimension_two', models.IntegerField(blank=True, null=True)),
                ('dimension_three', models.IntegerField(blank=True, null=True)),
                ('quantity', models.IntegerField(default=1)),
                ('size_one', models.IntegerField()),
                ('size_two', models.IntegerField()),
                ('cardboard', models.CharField(choices=[('B', 'B'), ('C', 'C'), ('E', 'E'), ('BC', 'BC'), ('BE', 'BE')], max_length=4)),
                ('pressure_large', models.IntegerField(default=0)),
                ('pressure_small', models.IntegerField(default=0)),
                ('wave_direction', models.BooleanField(default=True)),
                ('customers', models.ManyToManyField(blank=True, to='warehousemanager.Buyer')),
            ],
        ),
    ]
