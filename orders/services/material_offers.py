from decimal import Decimal

from django.db.models import Q

from orders.models import (
    CardboardGrade,
    CardboardPriceListItem,
)


def get_matching_cardboard_offers(
    requirement,
):
    """
    Znajduje materiały dostawców spełniające
    wymagania MaterialRequirement.

    NIE przeszukuje magazynu.

    Zwraca gotowe dane do wyświetlenia.
    """

    grades = (
        CardboardGrade.objects
        .filter(
            is_active=True,
        )
        .select_related(
            "provider",
        )
    )

    # ========================================================
    # FILTRY TECHNICZNE
    # ========================================================

    if requirement.layers:
        grades = grades.filter(
            layers=requirement.layers,
        )

    if requirement.flute:
        grades = grades.filter(
            flute__iexact=requirement.flute,
        )

    if requirement.min_gsm:
        grades = grades.filter(
            gsm__gte=requirement.min_gsm,
        )

    if requirement.min_ect:
        grades = grades.filter(
            ect__gte=requirement.min_ect,
        )

    if requirement.cover:
        grades = grades.filter(
            cover=requirement.cover,
        )

    # ========================================================
    # POWIERZCHNIA ZAMÓWIENIA
    # ========================================================

    area_m2 = requirement.required_area_m2

    results = []

    for grade in grades:

        price_item = (
            CardboardPriceListItem.objects
            .filter(
                cardboard=grade,
                price_list__valid_from__lte=requirement.customer_order.order_date,
            )
            .filter(
                Q(
                    price_list__valid_to__gte=requirement.customer_order.order_date
                )
                |
                Q(
                    price_list__valid_to__isnull=True
                )
            )
            .select_related(
                "price_list",
                "price_list__provider",
                "cardboard",
            )
            .prefetch_related(
                "price_tiers",
            )
            .order_by(
                "-price_list__valid_from",
                "-price_list_id",
            )
            .first()
        )

        if not price_item:
            continue

        price = price_item.price_for_area(
            area_m2
        )

        if price is None:
            continue

        total_value = (
            Decimal(area_m2)
            * Decimal(price)
            / Decimal("1000")
        ).quantize(
            Decimal("0.01")
        )

        results.append(
            {
                "grade": grade,
                "price_item": price_item,

                "provider": grade.provider,

                "index": grade.index,

                "layers": grade.layers,
                "flute": grade.flute,
                "gsm": grade.gsm,
                "ect": grade.ect,
                "cover": grade.cover,

                "composition": grade.composition,

                "price_per_1000_m2": price,

                "area_m2": area_m2,

                "total_value": total_value,

                "price_list": price_item.price_list,
            }
        )

    # ========================================================
    # SORTOWANIE
    # ========================================================

    results.sort(
        key=lambda row: (
            row["total_value"],
            row["gsm"],
            row["provider"].name,
        )
    )

    return results