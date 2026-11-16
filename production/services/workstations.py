import datetime

from django.db import transaction
from django.shortcuts import get_object_or_404

from production.models import (
    ProductionOrder,
    ProductionUnit,
    WorkStation,
)
from warehousemanager.models import Person


# ==========================================================
# WORKSTATIONS LIST
# ==========================================================


def get_workstations_context():
    today = datetime.date.today()

    stations = (
        WorkStation.objects
        .all()
        .order_by(
            "name"
        )
    )

    active_units = list(
        ProductionUnit.objects
        .filter(
            status="IN PROGRESS",
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
            "work_station__name",
            "order",
        )
    )

    planned_units = list(
        ProductionUnit.objects
        .filter(
            status="PLANNED",
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
            "work_station__name",
            "order",
        )
    )

    active_by_station = {}

    for unit in active_units:

        active_by_station.setdefault(
            unit.work_station_id,
            [],
        ).append(
            unit
        )

    planned_by_station = {}

    for unit in planned_units:

        planned_by_station.setdefault(
            unit.work_station_id,
            [],
        ).append(
            unit
        )

    station_rows = []

    now = datetime.datetime.now()

    for station in stations:

        station_active = (
            active_by_station.get(
                station.id,
                [],
            )
        )

        station_planned = (
            planned_by_station.get(
                station.id,
                [],
            )
        )

        active_unit = (
            station_active[0]
            if station_active
            else None
        )

        next_unit = (
            station_planned[0]
            if station_planned
            else None
        )

        active_timing = (
            build_unit_timing(
                active_unit,
                now=now,
            )
            if active_unit
            else None
        )

        next_timing = (
            build_unit_timing(
                next_unit,
                now=now,
            )
            if next_unit
            else None
        )

        station_rows.append({
            "station":
                station,

            "active_units":
                station_active,

            "active_unit":
                active_unit,

            "active_timing":
                active_timing,

            "has_multiple_active":
                len(
                    station_active
                ) > 1,

            "planned_count":
                len(
                    station_planned
                ),

            "next_unit":
                next_unit,

            "next_timing":
                next_timing,
        })

    workers = (
        Person.workers_at_work(
            today
        )
    )

    production_workers = [
        worker
        for worker
        in workers
        if worker.occupancy_type
        == "PRODUCTION"
    ]

    worker_rows = []

    active_worker_units = {}

    for unit in active_units:

        for person in unit.persons.all():

            active_worker_units[
                person.id
            ] = unit

    for worker in production_workers:

        unit = (
            active_worker_units.get(
                worker.id
            )
        )

        worker_rows.append({
            "worker":
                worker,

            "unit":
                unit,

            "station":
                (
                    unit.work_station
                    if unit
                    else None
                ),
        })

    return {
        "station_rows":
            station_rows,

        "worker_rows":
            worker_rows,

        "stations_count":
            len(
                station_rows
            ),

        "active_count":
            sum(
                len(
                    row[
                        "active_units"
                    ]
                )
                for row
                in station_rows
            ),

        "workers_count":
            len(
                worker_rows
            ),
    }


# ==========================================================
# TIMING HELPERS
# ==========================================================


def get_remaining_seconds(
    planned_end,
    *,
    now=None,
):
    if not planned_end:
        return None

    if now is None:
        now = (
            datetime.datetime.now()
        )

    return int(
        (
            planned_end
            - now
        ).total_seconds()
    )


def build_unit_timing(
    unit,
    *,
    now=None,
):
    if now is None:
        now = (
            datetime.datetime.now()
        )

    planned_start = (
        unit.planned_start()
    )

    planned_end = (
        unit.planned_end()
    )

    remaining_seconds = (
        get_remaining_seconds(
            planned_end,
            now=now,
        )
    )

    return {
        "planned_start":
            planned_start,

        "planned_end":
            planned_end,

        "estimated_time":
            unit.estimated_time,

        "remaining_seconds":
            remaining_seconds,

        "is_overdue":
            (
                remaining_seconds
                is not None
                and remaining_seconds
                < 0
            ),
    }


def build_workstation_unit_rows(
    units,
):
    now = (
        datetime.datetime.now()
    )

    rows = []

    for unit in units:

        rows.append({
            "unit":
                unit,

            "timing":
                build_unit_timing(
                    unit,
                    now=now,
                ),
        })

    return rows


# ==========================================================
# WORKSTATION DETAIL
# ==========================================================


def get_workstation_detail_context(
    *,
    workstation_id,
):
    station = get_object_or_404(
        WorkStation,
        pk=workstation_id,
    )

    units = (
        ProductionUnit.objects
        .filter(
            work_station=station,
        )
        .select_related(
            "production_order",
            "production_order__customer",
            "work_station",
        )
        .prefetch_related(
            "persons",
        )
    )

    in_progress_units = list(
        units
        .filter(
            status="IN PROGRESS",
        )
        .order_by(
            "order",
            "start",
        )
    )

    planned_units = list(
        units
        .filter(
            status="PLANNED",
        )
        .order_by(
            "order",
            "sequence",
        )
    )

    other_units = list(
        units
        .filter(
            status="NOT STARTED",
        )
        .order_by(
            "production_order__id_number",
            "sequence",
        )
    )

    history_from = (
        datetime.date.today()
        - datetime.timedelta(
            days=7,
        )
    )

    history_units = list(
        units
        .filter(
            status="FINISHED",
            end__date__gte=
                history_from,
        )
        .order_by(
            "-end",
        )
    )

    return {
        "station":
            station,

        # ACTIVE

        "in_progress_units":
            in_progress_units,

        "in_progress_rows":
            build_workstation_unit_rows(
                in_progress_units
            ),

        # QUEUE

        "planned_units":
            planned_units,

        "planned_rows":
            build_workstation_unit_rows(
                planned_units
            ),

        # OTHER

        "other_units":
            other_units,

        "history_units":
            history_units,

        # COUNTERS

        "planned_count":
            len(
                planned_units
            ),

        "waiting_count":
            len(
                other_units
            ),

        "history_from":
            history_from,
    }


# ==========================================================
# START
# ==========================================================


@transaction.atomic
def start_production_unit(
    *,
    unit_id,
):
    unit = get_object_or_404(
        ProductionUnit.objects
        .select_for_update()
        .select_related(
            "work_station",
            "production_order",
        ),
        pk=unit_id,
    )

    unit.status = (
        "IN PROGRESS"
    )

    unit.start = (
        datetime.datetime.now()
    )

    unit.end = None

    unit.save(
        update_fields=[
            "status",
            "start",
            "end",
        ]
    )

    return unit


# ==========================================================
# FINISH
# ==========================================================


@transaction.atomic
def finish_production_unit(
    *,
    unit_id,
):
    unit = get_object_or_404(
        ProductionUnit.objects
        .select_for_update()
        .select_related(
            "work_station",
            "production_order",
        ),
        pk=unit_id,
    )

    unit.status = (
        "FINISHED"
    )

    unit.end = (
        datetime.datetime.now()
    )

    unit.save(
        update_fields=[
            "status",
            "end",
        ]
    )

    production_order = (
        unit.production_order
    )

    units = (
        ProductionUnit.objects
        .filter(
            production_order=
                production_order,
        )
        .only(
            "id",
            "status",
        )
    )

    statuses = list(
        units.values_list(
            "status",
            flat=True,
        )
    )

    if (
        statuses
        and all(
            status == "FINISHED"
            for status
            in statuses
        )
    ):
        new_order_status = (
            "FINISHED"
        )

    elif (
        statuses
        and all(
            status in (
                "FINISHED",
                "PLANNED",
            )
            for status
            in statuses
        )
    ):
        new_order_status = (
            "PLANNED"
        )

    else:
        new_order_status = None

    if (
        new_order_status
        and production_order.status
        != new_order_status
    ):
        production_order.status = (
            new_order_status
        )

        production_order.save(
            update_fields=[
                "status",
            ]
        )

    return unit


# ==========================================================
# PLAN
# ==========================================================


@transaction.atomic
def plan_production_unit(
    *,
    unit_id,
):
    unit = get_object_or_404(
        ProductionUnit.objects
        .select_for_update()
        .select_related(
            "work_station",
            "production_order",
        ),
        pk=unit_id,
    )

    last_order = (
        ProductionUnit.objects
        .filter(
            work_station=
                unit.work_station,

            status=
                "PLANNED",
        )
        .exclude(
            pk=unit.pk,
        )
        .order_by(
            "-order"
        )
        .values_list(
            "order",
            flat=True,
        )
        .first()
    )

    unit.status = (
        "PLANNED"
    )

    unit.order = (
        (last_order or 0)
        + 1
    )

    unit.start = None
    unit.end = None

    unit.save(
        update_fields=[
            "status",
            "order",
            "start",
            "end",
        ]
    )

    return unit


# ==========================================================
# REMOVE FROM PLAN
# ==========================================================


@transaction.atomic
def remove_production_unit_from_plan(
    *,
    unit_id,
):
    unit = get_object_or_404(
        ProductionUnit.objects
        .select_for_update()
        .select_related(
            "work_station",
            "production_order",
        ),
        pk=unit_id,
    )

    station = (
        unit.work_station
    )

    old_order = (
        unit.order
    )

    unit.status = (
        "NOT STARTED"
    )

    unit.order = None
    unit.start = None
    unit.end = None

    unit.save(
        update_fields=[
            "status",
            "order",
            "start",
            "end",
        ]
    )

    if old_order is not None:

        queued_units = (
            ProductionUnit.objects
            .select_for_update()
            .filter(
                work_station=
                    station,

                status=
                    "PLANNED",

                order__gt=
                    old_order,
            )
            .order_by(
                "order",
                "id",
            )
        )

        for queued_unit in queued_units:

            queued_unit.order -= 1

            queued_unit.save(
                update_fields=[
                    "order",
                ]
            )

    return unit


# ==========================================================
# MOVE UP
# ==========================================================


@transaction.atomic
def move_production_unit_up(
    *,
    unit_id,
):
    unit = get_object_or_404(
        ProductionUnit.objects
        .select_for_update()
        .select_related(
            "work_station",
        ),
        pk=unit_id,
    )

    if (
        unit.status
        != "PLANNED"
        or unit.order
        is None
    ):
        return unit

    previous_unit = (
        ProductionUnit.objects
        .select_for_update()
        .filter(
            work_station=
                unit.work_station,

            status=
                "PLANNED",

            order__lt=
                unit.order,
        )
        .order_by(
            "-order",
            "-id",
        )
        .first()
    )

    if not previous_unit:
        return unit

    current_order = (
        unit.order
    )

    previous_order = (
        previous_unit.order
    )

    unit.order = (
        previous_order
    )

    previous_unit.order = (
        current_order
    )

    previous_unit.save(
        update_fields=[
            "order",
        ]
    )

    unit.save(
        update_fields=[
            "order",
        ]
    )

    return unit


# ==========================================================
# MOVE DOWN
# ==========================================================


@transaction.atomic
def move_production_unit_down(
    *,
    unit_id,
):
    unit = get_object_or_404(
        ProductionUnit.objects
        .select_for_update()
        .select_related(
            "work_station",
        ),
        pk=unit_id,
    )

    if (
        unit.status
        != "PLANNED"
        or unit.order
        is None
    ):
        return unit

    next_unit = (
        ProductionUnit.objects
        .select_for_update()
        .filter(
            work_station=
                unit.work_station,

            status=
                "PLANNED",

            order__gt=
                unit.order,
        )
        .order_by(
            "order",
            "id",
        )
        .first()
    )

    if not next_unit:
        return unit

    current_order = (
        unit.order
    )

    next_order = (
        next_unit.order
    )

    unit.order = (
        next_order
    )

    next_unit.order = (
        current_order
    )

    next_unit.save(
        update_fields=[
            "order",
        ]
    )

    unit.save(
        update_fields=[
            "order",
        ]
    )

    return unit