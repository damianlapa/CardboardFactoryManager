from decimal import Decimal
import datetime
from django.core.exceptions import ValidationError
from django.db import transaction

from ..models import ColorOrder, ColorOrderItem


@transaction.atomic
def create_color_order(
    *,
    provider,
    order_date,
    items,
    number=None,
    notes=None,
):
    if not items:
        raise ValidationError(
            "Zamówienie musi zawierać przynajmniej jedną farbę."
        )

    normalized_items = []

    for item in items:
        color = item["color"]
        quantity_kg = Decimal(item["quantity_kg"])
        price_per_kg = Decimal(item["price_per_kg"])

        if quantity_kg <= 0:
            raise ValidationError(
                f"Ilość dla koloru {color} musi być większa od 0."
            )

        if price_per_kg < 0:
            raise ValidationError(
                f"Cena dla koloru {color} nie może być ujemna."
            )

        normalized_items.append(
            ColorOrderItem(
                color=color,
                quantity_kg=quantity_kg,
                price_per_kg=price_per_kg,
            )
        )

    color_order = ColorOrder.objects.create(
        provider=provider,
        order_date=order_date,
        number=number,
        notes=notes,
        status=ColorOrder.STATUS_OPEN,
    )

    for item in normalized_items:
        item.order = color_order

    ColorOrderItem.objects.bulk_create(normalized_items)

    return color_order


from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from ..models import ColorOrder, ColorOrderItem, ColorBucket


def get_color_order(*, order_id):
    return (
        ColorOrder.objects
        .prefetch_related(
            "items__color",
            "items__buckets",
        )
        .get(pk=order_id)
    )


@transaction.atomic
def receive_color_order(
    *,
    color_order,
    buckets_by_item,
    received_date=None,
):
    """
    buckets_by_item:

    {
        15: [Decimal("20.00"), Decimal("10.00")],
        16: [Decimal("15.00"), Decimal("5.00")],
    }

    klucz = ColorOrderItem.id
    wartość = lista fizycznych wiader w kg
    """

    color_order = (
        ColorOrder.objects
        .select_for_update()
        .get(pk=color_order.pk)
    )

    if color_order.status == ColorOrder.STATUS_RECEIVED:
        raise ValidationError(
            "To zamówienie zostało już przyjęte."
        )

    if color_order.status == ColorOrder.STATUS_CANCELLED:
        raise ValidationError(
            "Nie można przyjąć anulowanego zamówienia."
        )

    items = (
        ColorOrderItem.objects
        .select_related("color")
        .filter(order=color_order)
    )

    if not items.exists():
        raise ValidationError(
            "Zamówienie nie zawiera żadnych pozycji."
        )

    received_date = received_date or datetime.date.today

    for item in items:
        bucket_weights = buckets_by_item.get(item.id, [])

        if not bucket_weights:
            raise ValidationError(
                f"Nie podano wiader dla koloru {item.color}."
            )

        total_received = Decimal("0.00")

        for weight in bucket_weights:
            weight = Decimal(weight)

            if weight <= 0:
                raise ValidationError(
                    f"Waga wiadra dla koloru {item.color} musi być większa od 0."
                )

            total_received += weight

        if total_received != item.quantity_kg:
            raise ValidationError(
                f"{item.color}: zamówiono {item.quantity_kg} kg, "
                f"a wpisano {total_received} kg."
            )

        for weight in bucket_weights:
            ColorBucket.objects.create(
                color=item.color,
                weight=weight,
                order_item=item,

                # tutaj później możemy dodać:
                # received_date=received_date,
            )

    color_order.status = ColorOrder.STATUS_RECEIVED
    color_order.received_date = received_date

    color_order.save(
        update_fields=[
            "status",
            "received_date",
        ]
    )

    return color_order