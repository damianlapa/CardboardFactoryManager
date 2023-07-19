# Generated by Django 3.1.3 on 2023-07-03 08:18

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0010_auto_20230703_0749'),
    ]

    operations = [
        migrations.CreateModel(
            name='Cardboard',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('designation', models.CharField(max_length=16)),
                ('layers', models.CharField(choices=[('2', '2'), ('3', '3'), ('4', '4'), ('5', '5'), ('6', '6'), ('7', '7')], max_length=1)),
                ('wave', models.CharField(choices=[('A', 'A'), ('B', 'B'), ('C', 'C'), ('D', 'D'), ('E', 'E'), ('F', 'F'), ('BC', 'BC'), ('EB', 'EB'), ('EC', 'EC'), ('EE', 'EE')], max_length=8)),
                ('grammage', models.IntegerField()),
                ('ect', models.DecimalField(decimal_places=2, max_digits=4)),
            ],
        ),
        migrations.CreateModel(
            name='Product',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('type', models.CharField(choices=[('Karton', 'Karton'), ('Przekładka', 'Przekładka'), ('Taśma', 'Taśma'), ('Folia Stretch', 'Folia Stretch'), ('Folia Bąbelkowa', 'Folia Bąbelkowa'), ('Usługa', 'Usługa'), ('Paleta', 'Paleta'), ('Produkt', 'Produkt')], max_length=64)),
                ('description', models.CharField(default='', max_length=256)),
                ('dimensions', models.CharField(blank=True, max_length=128, null=True)),
                ('cardboard', models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, to='orders.cardboard')),
            ],
        ),
        migrations.AlterField(
            model_name='supplier',
            name='name',
            field=models.CharField(max_length=64, unique=True),
        ),
        migrations.AlterField(
            model_name='supplier',
            name='shortcut',
            field=models.CharField(max_length=8, unique=True),
        ),
        migrations.CreateModel(
            name='ProductPrice',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('price', models.DecimalField(decimal_places=3, max_digits=6)),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='orders.product')),
            ],
        ),
        migrations.AddField(
            model_name='cardboard',
            name='supplier',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='orders.supplier'),
        ),
    ]