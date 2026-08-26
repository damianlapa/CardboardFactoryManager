import datetime

from django.db.models import Prefetch
from django.shortcuts import get_object_or_404

from production.models import (
    ProductionUnit,
    WorkStation,
)
from warehousemanager.models import Person


def get_workstations_context():
    today = datetime.date.today()

    stations = (
        WorkStation.objects
        .all()
        .order_by("name")
    )

    active_units = (
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

    planned_units = (
        ProductionUnit.objects
        .filter(
            status="PLANNED",
        )
        .select_related(
            "production_order",
            "production_order__customer",
            "work_station",
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
        ).append(unit)

    planned_by_station = {}

    for unit in planned_units:
        planned_by_station.setdefault(
            unit.work_station_id,
            [],
        ).append(unit)

    station_rows = []

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

        station_rows.append({
            "station": station,

            "active_units":
                station_active,

            "active_unit":
                station_active[0]
                if station_active
                else None,

            "has_multiple_active":
                len(station_active) > 1,

            "planned_count":
                len(station_planned),

            "next_unit":
                station_planned[0]
                if station_planned
                else None,
        })

    workers = (
        Person.workers_at_work(
            today
        )
    )

    production_workers = [
        worker
        for worker in workers
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
        unit = active_worker_units.get(
            worker.id
        )

        worker_rows.append({
            "worker": worker,
            "unit": unit,
            "station":
                unit.work_station
                if unit
                else None,
        })

    return {
        "station_rows":
            station_rows,

        "worker_rows":
            worker_rows,

        "stations_count":
            len(station_rows),

        "active_count":
            sum(
                len(
                    row["active_units"]
                )
                for row
                in station_rows
            ),

        "workers_count":
            len(worker_rows),
    }


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

    in_progress_units = (
        units
        .filter(
            status="IN PROGRESS"
        )
        .order_by(
            "order",
            "start",
        )
    )

    planned_units = (
        units
        .filter(
            status="PLANNED"
        )
        .order_by(
            "order",
            "sequence",
        )
    )

    other_units = (
        units
        .filter(
            status="NOT STARTED"
        )
        .order_by(
            "production_order__id_number",
            "sequence",
        )
    )

    history_from = (
        datetime.date.today()
        - datetime.timedelta(
            days=7
        )
    )

    history_units = (
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

        "in_progress_units":
            in_progress_units,

        "planned_units":
            planned_units,

        "other_units":
            other_units,

        "history_units":
            history_units,

        "planned_count":
            planned_units.count(),

        "waiting_count":
            other_units.count(),

        "history_from":
            history_from,
    }