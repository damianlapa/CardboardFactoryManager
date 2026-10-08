import datetime
from decimal import Decimal, ROUND_HALF_UP

from django.db.models import Q
from orders.models import (
    CardboardPriceList,
    CardboardPriceListItem,
)


def search_offers(spec):
    area = (
        Decimal(spec["sheet_length"])
        * Decimal(spec["sheet_width"])
        * Decimal(spec["quantity"])
        / Decimal("1000000")
    )

    today = datetime.datetime.today().date()

    price_lists = (
        CardboardPriceList.objects
        .filter(valid_from__lte=today)
        .filter(
            Q(valid_to__isnull=True)
            | Q(valid_to__gte=today)
        )
        .order_by(
            "provider_id",
            "-valid_from",
            "-id",
        )
    )

    # Najnowszy aktualny cennik każdego dostawcy
    latest = {}

    for price_list in price_lists:
        latest.setdefault(
            price_list.provider_id,
            price_list.pk,
        )

    items = (
        CardboardPriceListItem.objects
        .filter(
            price_list_id__in=latest.values(),
            cardboard__is_active=True,
        )
        .select_related(
            "cardboard",
            "cardboard__provider",
            "price_list",
        )
        .prefetch_related("price_tiers")
    )

    matched = []
    alternatives = []

    for item in items:
        grade = item.cardboard

        # Inna liczba warstw lub fala wyklucza materiał
        if (
            grade.layers != spec["layers"]
            or grade.flute.upper() != spec["flute"].upper()
        ):
            continue

        tier = next(
            (
                tier
                for tier in sorted(
                    item.price_tiers.all(),
                    key=lambda x: x.min_area_m2,
                    reverse=True,
                )
                if (
                    tier.min_area_m2 <= area
                    and (
                        tier.max_area_m2 is None
                        or area <= tier.max_area_m2
                    )
                )
            ),
            None,
        )

        if tier is None:
            continue

        differences = []

        # Pokrycie
        if spec.get("cover") and grade.cover != spec["cover"]:
            expected_cover = dict(
                grade.Cover.choices
            ).get(
                spec["cover"],
                spec["cover"],
            )

            actual_cover = (
                grade.get_cover_display()
                if grade.cover
                else "brak danych"
            )

            differences.append(
                f"Pokrycie: wymagane {expected_cover}, "
                f"oferowane {actual_cover}"
            )

        # Gramatura
        if (
            spec.get("min_gsm") is not None
            and (
                grade.gsm is None
                or grade.gsm < spec["min_gsm"]
            )
        ):
            if grade.gsm is None:
                differences.append("Gramatura: brak danych")
            else:
                differences.append(
                    f"Gramatura niższa o "
                    f"{spec['min_gsm'] - grade.gsm} g/m²"
                )

        # ECT
        if (
            spec.get("min_ect") is not None
            and (
                grade.ect is None
                or grade.ect < spec["min_ect"]
            )
        ):
            if grade.ect is None:
                differences.append("ECT: brak danych")
            else:
                differences.append(
                    f"ECT niższe o "
                    f"{spec['min_ect'] - grade.ect}"
                )

        # Cena całkowita
        total = (
            area
            * tier.price_per_1000_m2
            / Decimal("1000")
        ).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )

        unit_price = (
            (
                area
                * tier.price_per_1000_m2
                / Decimal("1000")
            )
            / Decimal(spec["quantity"])
        ).quantize(
            Decimal("0.0001"),
            rounding=ROUND_HALF_UP,
        )

        row = {
            "grade": grade,
            "item": item,
            "price_list": item.price_list,
            "area": area,
            "price": tier.price_per_1000_m2,
            "total": total,
            "unit_price": unit_price,
            "differences": differences,
            "difference_count": len(differences),
        }

        if differences:
            alternatives.append(row)
        else:
            matched.append(row)

    # Zgodne: najtańsze na początku
    matched.sort(
        key=lambda row: (
            row["total"],
            row["grade"].provider.name,
        )
    )

    # Alternatywy: najmniej różnic, potem cena
    alternatives.sort(
        key=lambda row: (
            row["difference_count"],
            row["total"],
            row["grade"].provider.name,
        )
    )

    return {
        "matched": matched,
        "alternatives": alternatives,
        "area": area,
    }