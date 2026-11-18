from django.db import transaction
from ..models import QuotationWorkEntry
from decimal import Decimal
from ..models import QuotationPrintColor

def sum_work_hours(entries):
    return sum(
        (
            Decimal(entry["hours"])
            for entry in entries
        ),
        Decimal("0.00"),
    )


@transaction.atomic
def save_quotation_items(formset):
    for form in formset.forms:
        if not form.has_changed() or not form.cleaned_data:
            continue
        item = form.save(commit=False)
        item.quotation = formset.instance
        item.save()
        item.work_entries.all().delete()
        QuotationWorkEntry.objects.bulk_create([
            QuotationWorkEntry(item=item, work_station_id=entry["work_station"], employees=entry["employees"], hours=entry["hours"])
            for entry in form.cleaned_data["work_entries"]
        ])
        item.print_colors.all().delete()

        QuotationPrintColor.objects.bulk_create([
            QuotationPrintColor(
                item=item,
                **color,
            )
            for color in form.cleaned_data["print_colors"]
        ])
