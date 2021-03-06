# Generated by Django 3.1.7 on 2021-04-12 17:31

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('warehousemanager', '0080_palettecustomer_exchange'),
    ]

    operations = [
        migrations.AlterField(
            model_name='absence',
            name='absence_type',
            field=models.CharField(choices=[('NN', 'Nieobecność nieusprawiedliwiona'), ('UW', 'Urlop wypoczynkowy'), ('UO', 'Urlop okolicznościowy'), ('SP', 'Spóźnienie'), ('UB', 'Urlop bezpłatny'), ('CH', 'Chorobowe'), ('KW', 'Kwarantanna'), ('OP', 'Opieka nad członkiem rodziny'), ('D', 'Delegacja'), ('IN', 'Inne'), ('PO', 'Postojowe')], max_length=4),
        ),
        migrations.CreateModel(
            name='Message',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('content', models.TextField()),
                ('date_send', models.DateField(blank=True, null=True)),
                ('date_read', models.DateField(blank=True, null=True)),
                ('recipient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='user_recipient', to=settings.AUTH_USER_MODEL)),
                ('sender', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='user_sender', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
