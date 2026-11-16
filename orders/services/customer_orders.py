import datetime

from django.db import transaction

from orders.models import (
    CustomerOrder,
    CustomerOrderSequence,
)

from orders.services.scores import (
    save_requirement_scores,
)


# ============================================================
# CUSTOMER ORDER NUMBER
# ============================================================


def get_next_customer_order_number():
    year = datetime.date.today().year

    with transaction.atomic():

        sequence, _ = (
            CustomerOrderSequence.objects
            .select_for_update()
            .get_or_create(
                year=year,
                defaults={
                    "last_number": 0,
                },
            )
        )

        sequence.last_number += 1

        sequence.save(
            update_fields=[
                "last_number",
            ]
        )

        return sequence.last_number, year


# ============================================================
# CREATE CUSTOMER ORDER
# ============================================================


@transaction.atomic
def create_customer_order(
    *,
    form,
    user,
):
    number, year = (
        get_next_customer_order_number()
    )

    order = form.save(
        commit=False
    )

    order.number = number
    order.year = year

    order.created_by = user
    order.updated_by = user

    order.save()

    return order


# ============================================================
# CREATE MATERIAL REQUIREMENT
# ============================================================


@transaction.atomic
def create_material_requirement(
    *,
    customer_order,
    form,
):
    requirement = form.save(
        commit=False
    )

    requirement.customer_order = (
        customer_order
    )

    if not requirement.required_sheet_quantity:
        requirement.required_sheet_quantity = (
            requirement
            .calculate_required_sheet_quantity()
        )

    requirement.save()

    save_requirement_scores(
        requirement=requirement,
        value=form.cleaned_data.get(
            "scores"
        ),
    )

    return requirement


# ============================================================
# SIMPLE CUSTOMER ORDER QUERYSET
# ============================================================


def get_customer_orders():
    return (
        CustomerOrder.objects
        .select_related(
            "customer",
            "product",
            "created_by",
        )
        .order_by(
            "-year",
            "-number",
        )
    )