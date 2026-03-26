from django.db import migrations, models
from django.db.models import F


def backfill_delta(apps, schema_editor):
    WarehouseStockHistory = apps.get_model("warehouse", "WarehouseStockHistory")
    # delta = quantity_after - quantity_before
    WarehouseStockHistory.objects.update(delta=F("quantity_after") - F("quantity_before"))


class Migration(migrations.Migration):
    dependencies = [
        ('warehouse', '0049_alter_product_name'),
    ]

    operations = [
        migrations.AddField(
            model_name="warehousestockhistory",
            name="delta",
            field=models.IntegerField(default=0),
        ),
        migrations.RunPython(backfill_delta, migrations.RunPython.noop),
    ]

