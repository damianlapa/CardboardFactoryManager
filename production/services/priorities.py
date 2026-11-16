import datetime

from django.core.exceptions import ValidationError
from django.db import transaction

from production.models import (
    ProductionOrder,
    ProductionOrderPriorityHistory,
)


VALID_PRIORITIES = (1, 2, 3)


def normalize_priority(value):
    if value in (None, "", 0, "0"):
        return None

    try:
        value = int(value)
    except (TypeError, ValueError):
        raise ValidationError(
            "Nieprawidłowy poziom priorytetu."
        )

    if value not in VALID_PRIORITIES:
        raise ValidationError(
            "Priorytet musi mieć poziom 1, 2 lub 3."
        )

    return value


def parse_priority_date(value):
    if not value:
        return None

    if isinstance(value, datetime.date):
        return value

    try:
        return datetime.date.fromisoformat(value)
    except (TypeError, ValueError):
        raise ValidationError(
            "Nieprawidłowa data realizacji."
        )


@transaction.atomic
def set_production_order_priority(
    *,
    order: ProductionOrder,
    priority,
    priority_date=None,
    changed_by=None,
):
    priority = normalize_priority(priority)
    priority_date = parse_priority_date(priority_date)

    # brak priorytetu = brak terminu
    if priority is None:
        priority_date = None

    # Jeżeli nic się faktycznie nie zmieniło,
    # nie tworzymy sztucznego wpisu historii.
    if (
        order.priority == priority
        and order.priority_date == priority_date
    ):
        return {
            "order": order,
            "history": None,
            "changed": False,
        }

    order.priority = priority
    order.priority_date = priority_date

    order.save(
        update_fields=[
            "priority",
            "priority_date",
        ]
    )

    history = ProductionOrderPriorityHistory.objects.create(
        order=order,
        priority=priority,
        priority_date=priority_date,
        changed_by=changed_by,
    )

    return {
        "order": order,
        "history": history,
        "changed": True,
    }