import datetime

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q

from orders.models import (
    CardboardGrade,
    CardboardOrder,
    CardboardOrderItem,
    CardboardOrderItemScore,
    CardboardPriceListItem,
    MaterialAllocation,
)



# ============================================================
# GET MATCHING PURCHASE OFFERS
# ============================================================


def get_material_purchase_offers(
    requirement,
    *,
    price_date=None,
):
    """
    Zwraca aktualne oferty dostawców spełniające
    wymagania MaterialRequirement.

    Nie przeszukuje magazynu.
    """

    if price_date is None:
        price_date = datetime.date.today()

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
    # TECHNICAL FILTERS
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

    grade_ids = grades.values_list(
        "id",
        flat=True,
    )

    # ========================================================
    # ACTIVE PRICE LISTS
    # ========================================================

    price_items = (
        CardboardPriceListItem.objects
        .filter(
            cardboard_id__in=grade_ids,
            price_list__valid_from__lte=price_date,
        )
        .filter(
            Q(
                price_list__valid_to__gte=price_date
            )
            |
            Q(
                price_list__valid_to__isnull=True
            )
        )
        .select_related(
            "cardboard",
            "cardboard__provider",
            "price_list",
        )
        .prefetch_related(
            "price_tiers",
        )
        .order_by(
            "cardboard_id",
            "-price_list__valid_from",
            "-price_list_id",
        )
    )

    # ========================================================
    # KEEP ONLY LATEST ACTIVE PRICE LIST FOR EACH GRADE
    # ========================================================

    latest_by_cardboard = {}

    for item in price_items:

        if (
            item.cardboard_id
            not in latest_by_cardboard
        ):
            latest_by_cardboard[
                item.cardboard_id
            ] = item

    area_m2 = Decimal(
        requirement.required_area_m2
    )

    offers = []

    # ========================================================
    # BUILD OFFER DATA
    # ========================================================

    for item in latest_by_cardboard.values():

        price = item.price_for_area(
            area_m2
        )

        if price is None:
            continue

        total_value = (
            area_m2
            * Decimal(price)
            / Decimal("1000")
        ).quantize(
            Decimal("0.01")
        )

        grade = item.cardboard

        offers.append(
            {
                "price_item": item,
                "price_item_id": item.pk,

                "grade": grade,

                "provider": grade.provider,
                "provider_id":
                    grade.provider_id,

                "index": grade.index,
                "layers": grade.layers,
                "flute": grade.flute,
                "gsm": grade.gsm,
                "ect": grade.ect,
                "cover": grade.cover,

                "composition":
                    grade.composition,

                "provider_status":
                    item.get_provider_status_display(),

                "price_list":
                    item.price_list,

                "price_per_1000_m2":
                    price,

                "sheet_length":
                    requirement.sheet_length,

                "sheet_width":
                    requirement.sheet_width,

                "sheet_quantity":
                    requirement.required_sheet_quantity,

                "area_m2":
                    area_m2,

                "total_value":
                    total_value,
            }
        )

    # ========================================================
    # SORT
    # ========================================================

    offers.sort(
        key=lambda offer: (
            offer["total_value"],
            offer["gsm"],
            str(offer["provider"]),
        )
    )

    return offers


# ============================================================
# GET ONE SELECTED OFFER
# ============================================================


def get_material_purchase_offer(
    requirement,
    price_list_item_id,
):
    """
    Backend ponownie sprawdza ofertę.

    Nie ufamy cenie ani parametrom przesłanym
    przez formularz HTML.
    """

    try:
        price_list_item_id = int(
            price_list_item_id
        )

    except (TypeError, ValueError):

        raise ValidationError(
            "Niepoprawna oferta materiału."
        )

    offers = (
        get_material_purchase_offers(
            requirement
        )
    )

    for offer in offers:

        if (
            offer["price_item_id"]
            == price_list_item_id
        ):
            return offer

    raise ValidationError(
        "Wybrana oferta nie jest już dostępna."
    )


# ============================================================
# CREATE MATERIAL PURCHASE
# ============================================================


@transaction.atomic
def create_material_purchase(
    *,
    requirement,
    offer,
    order_number,
    order_date,
    delivery_date,
    user,
):
    """
    Tworzy pełny zakup materiału:

    CardboardOrder
        ↓
    CardboardOrderItem
        ↓
    CardboardOrderItemScore

    oraz:

    MaterialAllocation(source=PURCHASE)
    """

    order_number = (
        order_number or ""
    ).strip()

    if not order_number:
        raise ValidationError(
            "Podaj numer zamówienia u dostawcy."
        )

    if not order_date:
        raise ValidationError(
            "Podaj datę zamówienia."
        )

    # ========================================================
    # DO NOT PURCHASE THE SAME REQUIREMENT TWICE
    # ========================================================

    existing_purchase = (
        MaterialAllocation.objects
        .filter(
            requirement=requirement,
            source=(
                MaterialAllocation
                .Source
                .PURCHASE
            ),
        )
        .exists()
    )

    if existing_purchase:
        raise ValidationError(
            (
                "Dla tego zapotrzebowania "
                "materiał został już zamówiony."
            )
        )

    provider = offer["provider"]

    # ========================================================
    # PROVIDER ORDER NUMBER DUPLICATE
    # ========================================================

    if (
        CardboardOrder.objects
        .filter(
            provider=provider,
            number=order_number,
        )
        .exists()
    ):
        raise ValidationError(
            (
                f"Zamówienie {order_number} "
                f"dla dostawcy {provider} "
                f"już istnieje."
            )
        )

    # ========================================================
    # CARDBOARD ORDER
    # ========================================================

    cardboard_order = (
        CardboardOrder.objects.create(
            provider=provider,
            number=order_number,
            order_date=order_date,
            status=(
                CardboardOrder
                .Status
                .DRAFT
            ),
            created_by=user,
        )
    )

    # ========================================================
    # ORDER ITEM / SNAPSHOT
    # ========================================================

    item = (
        CardboardOrderItem.objects.create(
            order=cardboard_order,

            requirement=requirement,

            cardboard=offer["grade"],

            price_list_item=(
                offer["price_item"]
            ),

            sheet_length=(
                requirement.sheet_length
            ),

            sheet_width=(
                requirement.sheet_width
            ),

            quantity=(
                requirement
                .required_sheet_quantity
            ),

            price_per_1000_m2=(
                offer[
                    "price_per_1000_m2"
                ]
            ),
        )
    )

    # ========================================================
    # SCORES SNAPSHOT
    # ========================================================

    score_positions = (
        requirement
        .scores
        .order_by(
            "position_mm"
        )
        .values_list(
            "position_mm",
            flat=True,
        )
    )

    CardboardOrderItemScore.objects.bulk_create(
        [
            CardboardOrderItemScore(
                order_item=item,
                position_mm=position,
            )
            for position
            in score_positions
        ]
    )

    # ========================================================
    # MATERIAL ALLOCATION
    # ========================================================

    MaterialAllocation.objects.create(
        requirement=requirement,

        source=(
            MaterialAllocation
            .Source
            .PURCHASE
        ),

        quantity=(
            requirement
            .required_sheet_quantity
        ),

        cardboard_order_item=item,

        created_by=user,
    )

    # ========================================================
    # AQUILA EDI
    # ========================================================

    provider_name = (
        str(provider.name)
        .strip()
        .upper()
    )

    provider_shortcut = (
        str(provider.shortcut or "")
        .strip()
        .upper()
    )

    is_aquila = (
        provider_name == "AQUILA"
        or provider_shortcut == "AQ"
        or provider_shortcut == "AQUILA"
    )

    return cardboard_order
