from django.shortcuts import get_object_or_404

from orders.models import CardboardPriceListItem
from production.models import WorkStation

from ..forms import QuotationItemFormSet
from ..models import Quotation
from .materials import material_label


def get_quotation(quotation_id):
    return get_object_or_404(
        Quotation.objects.select_related("customer"),
        pk=quotation_id,
    )


def get_item_formset(quotation, data=None):
    queryset = (
        quotation.items
        .select_related(
            "material__cardboard",
            "material__price_list__provider",
        )
        .prefetch_related("work_entries")
        .order_by("pk")
    )

    return QuotationItemFormSet(
        data=data,
        instance=quotation,
        prefix="items",
        queryset=queryset,
    )


def get_detail_context(quotation, formset):
    material_ids = []

    for form in formset:
        value = str(form["material"].value())

        if (
            value.isascii()
            and value.isdecimal()
            and len(value) <= 18
        ):
            material_ids.append(value)

    materials = (
        CardboardPriceListItem.objects
        .filter(pk__in=material_ids)
        .select_related(
            "cardboard",
            "price_list__provider",
        )
    )

    labels = {
        str(item.pk): item.cardboard.index
        for item in materials
    }

    for form in formset:
        form.material_label = labels.get(
            str(form["material"].value()),
            "Wybierz materiał",
        )

    return {
        "quotation": quotation,
        "formset": formset,
        "workstations": list(
            WorkStation.objects
            .order_by("name")
            .values("id", "name")
        ),
    }