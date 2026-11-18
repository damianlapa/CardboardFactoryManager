from django.db import transaction

from ..models import QuotationSheetRule
from ..settings_forms import (
    SheetRuleRowForm,
    SheetRuleSelectForm,
)


FLUTES = ("B", "C", "E", "EB", "BC")

RULE_FIELDS = (
    "glue_flap",
    "length_allowance",
    "width_allowance",
)


def get_sheet_settings_context(params, data=None):
    selector = SheetRuleSelectForm(
        params if params else None
    )

    selected = None

    if selector.is_bound and selector.is_valid():
        selected = selector.cleaned_data["packaging_type"]

    rows = []

    if selected:
        rules = {
            rule.flute: rule
            for rule in QuotationSheetRule.objects.filter(
                packaging_type=selected,
            )
        }

        for flute in FLUTES:
            rule = rules.get(flute)

            initial = (
                {
                    name: getattr(rule, name)
                    for name in RULE_FIELDS
                }
                if rule
                else {}
            )

            rows.append({
                "flute": flute,
                "configured": rule is not None,
                "form": SheetRuleRowForm(
                    data=data,
                    initial=initial,
                    prefix=f"flute-{flute}",
                    configured=rule is not None,
                ),
            })

    return {
        "selector": selector,
        "packaging_type": selected,
        "rows": rows,
    }


@transaction.atomic
def save_sheet_settings(context):
    if context["packaging_type"] is None:
        return False

    # Walidujemy wszystkie wiersze przed zapisem.
    valid = [
        row["form"].is_valid()
        for row in context["rows"]
    ]

    if not all(valid):
        return False

    for row in context["rows"]:
        values = row["form"].cleaned_data

        # Całkowicie pusty nowy wiersz pomijamy.
        if values["glue_flap"] is None:
            continue

        QuotationSheetRule.objects.update_or_create(
            packaging_type=context["packaging_type"],
            flute=row["flute"],
            defaults={
                name: values[name]
                for name in RULE_FIELDS
            },
        )

    return True
