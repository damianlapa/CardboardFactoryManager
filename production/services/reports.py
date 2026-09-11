import datetime
from collections import defaultdict

from production.models import (
    ProductionUnit,
    WorkStation,
)


def format_seconds(seconds):
    if not seconds:
        return "00:00"

    seconds = int(seconds)

    hours = seconds // 3600
    minutes = (
        seconds % 3600
    ) // 60

    return (
        f"{hours:02d}:"
        f"{minutes:02d}"
    )


def get_report_units(
    *,
    date_from,
    date_to,
    station_id=None,
    worker_id=None,
):
    queryset = (
        ProductionUnit.objects
        .filter(
            start__isnull=False,
            end__isnull=False,
            start__date__lte=date_to,
            end__date__gte=date_from,
        )
        .select_related(
            "production_order",
            "production_order__customer",
            "work_station",
        )
        .prefetch_related(
            "persons",
        )
        .order_by(
            "start",
            "id",
        )
    )

    if station_id:
        queryset = queryset.filter(
            work_station_id=station_id
        )

    if worker_id:
        queryset = queryset.filter(
            persons__id=worker_id
        ).distinct()

    return queryset


def get_unit_real_seconds(unit):
    try:
        value = unit.unit_duration2()

        return int(
            value or 0
        )

    except Exception:
        return 0


def get_unit_estimated_seconds(unit):
    try:
        value = (
            unit.estimated_duration_in_seconds()
        )

        return int(
            value or 0
        )

    except Exception:
        if unit.estimated_time:
            return int(
                unit.estimated_time
                * 60
            )

        return 0


def get_unit_efficiency(
    *,
    estimated_seconds,
    real_seconds,
):
    if not real_seconds:
        return None

    if not estimated_seconds:
        return None

    return round(
        (
            estimated_seconds
            / real_seconds
        )
        * 100,
        1,
    )


def get_report_summary(units):
    total_units = 0

    total_real_seconds = 0
    total_estimated_seconds = 0

    total_quantity = 0

    orders = set()
    workers = set()

    for unit in units:

        total_units += 1

        orders.add(
            unit.production_order_id
        )

        real_seconds = (
            get_unit_real_seconds(
                unit
            )
        )

        estimated_seconds = (
            get_unit_estimated_seconds(
                unit
            )
        )

        total_real_seconds += (
            real_seconds
        )

        total_estimated_seconds += (
            estimated_seconds
        )

        quantity = (
            unit.quantity_end
            or unit.quantity_start
            or 0
        )

        total_quantity += quantity

        for person in unit.persons.all():
            workers.add(
                person.id
            )

    efficiency = (
        get_unit_efficiency(
            estimated_seconds=
                total_estimated_seconds,

            real_seconds=
                total_real_seconds,
        )
    )

    return {
        "units_count":
            total_units,

        "orders_count":
            len(orders),

        "workers_count":
            len(workers),

        "quantity":
            total_quantity,

        "real_seconds":
            total_real_seconds,

        "real_time":
            format_seconds(
                total_real_seconds
            ),

        "estimated_seconds":
            total_estimated_seconds,

        "estimated_time":
            format_seconds(
                total_estimated_seconds
            ),

        "efficiency":
            efficiency,
    }


def get_station_report(units):
    data = defaultdict(
        lambda: {
            "units_count": 0,
            "real_seconds": 0,
            "estimated_seconds": 0,
            "quantity": 0,
            "orders": set(),
            "workers": set(),
        }
    )

    for unit in units:

        station = unit.work_station

        if not station:
            continue

        row = data[
            station.id
        ]

        row["station"] = station

        row["units_count"] += 1

        row["orders"].add(
            unit.production_order_id
        )

        real_seconds = (
            get_unit_real_seconds(
                unit
            )
        )

        estimated_seconds = (
            get_unit_estimated_seconds(
                unit
            )
        )

        row["real_seconds"] += (
            real_seconds
        )

        row["estimated_seconds"] += (
            estimated_seconds
        )

        row["quantity"] += (
            unit.quantity_end
            or unit.quantity_start
            or 0
        )

        for person in unit.persons.all():

            row["workers"].add(
                person.id
            )

    result = []

    for row in data.values():

        row["orders_count"] = len(
            row["orders"]
        )

        row["workers_count"] = len(
            row["workers"]
        )

        row["real_time"] = (
            format_seconds(
                row["real_seconds"]
            )
        )

        row["estimated_time"] = (
            format_seconds(
                row["estimated_seconds"]
            )
        )

        row["efficiency"] = (
            get_unit_efficiency(
                estimated_seconds=
                    row[
                        "estimated_seconds"
                    ],

                real_seconds=
                    row[
                        "real_seconds"
                    ],
            )
        )

        result.append(
            row
        )

    result.sort(
        key=lambda row:
            row["real_seconds"],
        reverse=True,
    )

    return result


def get_unit_rows(units):
    rows = []

    for unit in units:

        real_seconds = (
            get_unit_real_seconds(
                unit
            )
        )

        estimated_seconds = (
            get_unit_estimated_seconds(
                unit
            )
        )

        rows.append({
            "unit":
                unit,

            "real_seconds":
                real_seconds,

            "real_time":
                format_seconds(
                    real_seconds
                ),

            "estimated_seconds":
                estimated_seconds,

            "estimated_time":
                format_seconds(
                    estimated_seconds
                ),

            "efficiency":
                get_unit_efficiency(
                    estimated_seconds=
                        estimated_seconds,

                    real_seconds=
                        real_seconds,
                ),

            "quantity":
                (
                    unit.quantity_end
                    or unit.quantity_start
                    or 0
                ),

            "persons":
                list(
                    unit.persons.all()
                ),
        })

    return rows


def get_production_report(
    *,
    date_from,
    date_to,
    station_id=None,
    worker_id=None,
):
    units = list(
        get_report_units(
            date_from=date_from,
            date_to=date_to,
            station_id=station_id,
            worker_id=worker_id,
        )
    )

    return {
        "summary":
            get_report_summary(
                units
            ),

        "stations":
            get_station_report(
                units
            ),

        "units":
            get_unit_rows(
                units
            ),
    }