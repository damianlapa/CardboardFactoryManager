from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('deliveries', '0006_alter_event_event_type'),
    ]

    operations = [
        migrations.DeleteModel(
            name='Delivery',
        ),
    ]