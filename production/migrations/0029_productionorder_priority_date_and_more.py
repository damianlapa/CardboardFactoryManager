from django.db import migrations, models


def copy_old_priority(apps, schema_editor):
    ProductionOrder = apps.get_model(
        "production",
        "ProductionOrder",
    )

    # Stary priority=True -> nowy poziom 1
    ProductionOrder.objects.filter(
        priority=True
    ).update(
        priority_level=1
    )

    # priority=False pozostaje NULL w priority_level


class Migration(migrations.Migration):

    dependencies = [
        (
            "production",
            "0028_productionorder_photopolymer_productionorder_punch",
        ),
    ]

    operations = [

        # 1. Dodajemy termin priorytetu
        migrations.AddField(
            model_name="productionorder",
            name="priority_date",
            field=models.DateField(
                blank=True,
                null=True,
            ),
        ),

        # 2. Dodajemy tymczasowe pole integer
        migrations.AddField(
            model_name="productionorder",
            name="priority_level",
            field=models.PositiveSmallIntegerField(
                blank=True,
                null=True,
                choices=[
                    (1, "Niski"),
                    (2, "Wysoki"),
                    (3, "Krytyczny"),
                ],
            ),
        ),

        # 3. Przepisujemy stare True -> 1
        migrations.RunPython(
            copy_old_priority,
            migrations.RunPython.noop,
        ),

        # 4. Usuwamy stare BooleanField
        migrations.RemoveField(
            model_name="productionorder",
            name="priority",
        ),

        # 5. priority_level -> priority
        migrations.RenameField(
            model_name="productionorder",
            old_name="priority_level",
            new_name="priority",
        ),
    ]