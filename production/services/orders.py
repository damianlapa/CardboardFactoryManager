import datetime

from django.shortcuts import (
    get_object_or_404,
)

from production.forms import (
    ProductionUnitForm,
)
from production.models import (
    PRODUCTION_ORDER_STATUSES,
    PRODUCTION_UNIT_STATUSES,
    ProductionOrder,
    ProductionUnit,
    WorkStation,
)
from warehousemanager.models import (
    Person,
    Photopolymer,
    Punch,
)


def get_production_order_detail_context(
    *,
    production_order_id,
):
    production_order = get_object_or_404(
        ProductionOrder.objects
        .select_related(
            "customer",
            "photopolymer",
            "punch",
        ),
        pk=production_order_id,
    )

    production_units = (
        ProductionUnit.objects
        .filter(
            production_order=production_order
        )
        .select_related(
            "work_station",
            "punch",
            "polymer",
        )
        .prefetch_related(
            "persons",
        )
        .order_by(
            "sequence"
        )
    )

    workers = (
        Person.objects
        .filter(
            occupancy_type="PRODUCTION",
            job_end__isnull=True,
        )
        .order_by(
            "last_name",
            "first_name",
        )
    )

    form = ProductionUnitForm(
        initial={
            "sequence":
                production_units.count() + 1,

            "status":
                "NOT STARTED",
        }
    )

    punches = (
        Punch.objects
        .filter(
            active=True
        )
        .order_by(
            "type",
            "type_letter",
            "type_num",
        )
    )

    photopolymers = (
        Photopolymer.objects
        .filter(
            active=True,
        )
        .select_related(
            "customer",
        )
        .order_by(
            "identification_number",
            "identification_letter",
        )
    )

    return {
        "production_order":
            production_order,

        "production_units":
            production_units,

        "production_order_statuses":
            PRODUCTION_ORDER_STATUSES,

        "production_unit_statuses":
            PRODUCTION_UNIT_STATUSES,

        "workstations":
            WorkStation.objects
            .all()
            .order_by("name"),

        "workers":
            workers,

        "form":
            form,

        "punches_data": [
            {
                "id": punch.id,
                "name": str(punch),
            }
            for punch in punches
        ],

        "photopolymers_data": [
            {
                "id": polymer.id,
                "name": str(polymer),
            }
            for polymer in photopolymers
        ],
    }