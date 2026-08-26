import datetime
from collections import defaultdict

from django.db import transaction
from django.shortcuts import get_object_or_404

from production.models import (
    ProductionTask,
    ProductionUnit,
    WeeklyPlan,
    WorkStation,
)


# ============================================================
# WORKING TIME
# ============================================================

WORK_START = datetime.time(7, 0)
WORK_END = datetime.time(15, 0)

BREAKS = (
    (
        datetime.time(9, 0),
        datetime.time(9, 5),
    ),
    (
        datetime.time(11, 0),
        datetime.time(11, 20),
    ),
    (
        datetime.time(12, 30),
        datetime.time(12, 35),
    ),
    (
        datetime.time(14, 0),
        datetime.time(14, 5),
    ),
)

WEEK_DAYS = (
    (1, "Poniedziałek"),
    (2, "Wtorek"),
    (3, "Środa"),
    (4, "Czwartek"),
    (5, "Piątek"),
)


# ============================================================
# EXCEPTIONS
# ============================================================


class PlanningError(Exception):
    pass


# ============================================================
# DATE HELPERS
# ============================================================


def get_week_dates(*, year, week):
    """
    Zwraca poniedziałek-piątek dla tygodnia ISO.
    """

    return [
        datetime.date.fromisocalendar(
            year,
            week,
            weekday,
        )
        for weekday, label in WEEK_DAYS
    ]


def get_week_start(*, year, week):
    return datetime.date.fromisocalendar(
        year,
        week,
        1,
    )


def get_week_end(*, year, week):
    return datetime.date.fromisocalendar(
        year,
        week,
        5,
    )


def get_previous_week(*, year, week):
    current = get_week_start(
        year=year,
        week=week,
    )

    previous = (
        current
        - datetime.timedelta(days=7)
    )

    iso = previous.isocalendar()

    return {
        "year": iso.year,
        "week": iso.week,
    }


def get_next_week(*, year, week):
    current = get_week_start(
        year=year,
        week=week,
    )

    next_date = (
        current
        + datetime.timedelta(days=7)
    )

    iso = next_date.isocalendar()

    return {
        "year": iso.year,
        "week": iso.week,
    }


# ============================================================
# DATETIME HELPERS
# ============================================================


def make_local_datetime(
    *,
    day,
    time_value,
):
    return datetime.datetime.combine(
        day,
        time_value,
    )


def get_workday_start(day):
    return make_local_datetime(
        day=day,
        time_value=WORK_START,
    )


def get_workday_end(day):
    return make_local_datetime(
        day=day,
        time_value=WORK_END,
    )


def get_daily_capacity_minutes():
    """
    07:00-15:00 minus production breaks.
    """

    start = datetime.datetime.combine(
        datetime.date.today(),
        WORK_START,
    )

    end = datetime.datetime.combine(
        datetime.date.today(),
        WORK_END,
    )

    total = int(
        (end - start).total_seconds()
        // 60
    )

    for break_start, break_end in BREAKS:

        break_start_dt = (
            datetime.datetime.combine(
                datetime.date.today(),
                break_start,
            )
        )

        break_end_dt = (
            datetime.datetime.combine(
                datetime.date.today(),
                break_end,
            )
        )

        total -= int(
            (
                break_end_dt
                - break_start_dt
            ).total_seconds()
            // 60
        )

    return total


DAILY_CAPACITY_MINUTES = (
    get_daily_capacity_minutes()
)


# ============================================================
# TASK TIME
# ============================================================


def get_task_duration_minutes(task):
    """
    Czas zadania.

    Priorytety:
    1. estimated_time z ProductionUnit
    2. obecna długość ProductionTask

    Nie zgadujemy czasu.
    """

    unit = task.production_unit

    if (
        unit.estimated_time
        and unit.estimated_time > 0
    ):
        return unit.estimated_time

    if task.start and task.end:

        duration = int(
            (
                task.end
                - task.start
            ).total_seconds()
            // 60
        )

        if duration > 0:
            return duration

    return None


def get_unit_duration_minutes(unit):
    """
    Używane przy dodawaniu niezaplanowanego
    ProductionUnit do planu.
    """

    if (
        unit.estimated_time
        and unit.estimated_time > 0
    ):
        return unit.estimated_time

    try:
        suggested = unit.suggested_time()
    except Exception:
        suggested = None

    if suggested and suggested > 0:
        return int(suggested)

    return None


# ============================================================
# ADD WORKING MINUTES
# ============================================================


def add_work_minutes(
    *,
    start,
    minutes,
):
    """
    Dodaje minuty pomijając przerwy.

    Jeżeli plan przekracza 15:00, nie przerzucamy
    automatycznie na kolejny dzień.

    Dzięki temu UI może pokazać przeciążenie dnia.
    """

    current = start
    remaining = int(minutes)

    day = current.date()

    for break_start_time, break_end_time in BREAKS:

        break_start = make_local_datetime(
            day=day,
            time_value=break_start_time,
        )

        break_end = make_local_datetime(
            day=day,
            time_value=break_end_time,
        )

        # jesteśmy już po tej przerwie
        if current >= break_end:
            continue

        # trafiliśmy w przerwę
        if (
            current >= break_start
            and current < break_end
        ):
            current = break_end

        # przerwa przed nami
        if current < break_start:

            available = int(
                (
                    break_start
                    - current
                ).total_seconds()
                // 60
            )

            if remaining <= available:

                return (
                    current
                    + datetime.timedelta(
                        minutes=remaining
                    )
                )

            remaining -= available
            current = break_end

    return (
        current
        + datetime.timedelta(
            minutes=remaining
        )
    )


# ============================================================
# PLAN
# ============================================================


def get_or_create_weekly_plan(
    *,
    year,
    week,
):
    try:
        datetime.date.fromisocalendar(
            year,
            week,
            1,
        )
    except ValueError as error:
        raise PlanningError(
            "Nieprawidłowy numer tygodnia."
        ) from error

    plan, created = (
        WeeklyPlan.objects.get_or_create(
            year=year,
            week=week,
        )
    )

    return plan


# ============================================================
# LANE
# ============================================================


def get_lane_tasks(
    *,
    plan,
    station,
    day,
    lock=False,
):
    queryset = (
        ProductionTask.objects
        .filter(
            plan=plan,
            work_station=station,
            start__date=day,
        )
        .select_related(
            "production_unit",
            "production_unit__production_order",
            "production_unit__production_order__customer",
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

    if lock:
        queryset = (
            queryset.select_for_update()
        )

    return list(queryset)


# ============================================================
# RECALCULATE LANE
# ============================================================


def recalculate_lane(
    *,
    plan,
    station,
    day,
    ordered_task_ids=None,
):
    """
    Ustawia zadania jedno po drugim od 07:00.

    Kolejność może zostać przesłana z drag&drop.
    """

    tasks = get_lane_tasks(
        plan=plan,
        station=station,
        day=day,
        lock=True,
    )

    if ordered_task_ids is not None:

        task_map = {
            task.id: task
            for task in tasks
        }

        ordered = []

        for task_id in ordered_task_ids:

            task = task_map.pop(
                int(task_id),
                None,
            )

            if task:
                ordered.append(task)

        # bezpieczeństwo:
        # jeśli frontend nie przesłał któregoś taska,
        # nie możemy go zgubić
        ordered.extend(
            task_map.values()
        )

        tasks = ordered

    current = get_workday_start(
        day
    )

    for task in tasks:

        duration = (
            get_task_duration_minutes(
                task
            )
        )

        if not duration:
            raise PlanningError(
                (
                    "Brak planowanego czasu "
                    f"dla operacji "
                    f"{task.production_unit}."
                )
            )

        task.start = current

        task.end = add_work_minutes(
            start=current,
            minutes=duration,
        )

        task.work_station = station

        task.save(
            update_fields=[
                "work_station",
                "start",
                "end",
            ]
        )

        current = task.end

    return tasks


# ============================================================
# CREATE TASK FROM UNIT
# ============================================================


def create_task_from_unit(
    *,
    plan,
    unit,
    station,
    day,
):
    duration = (
        get_unit_duration_minutes(
            unit
        )
    )

    if not duration:
        raise PlanningError(
            (
                "Nie można zaplanować operacji "
                "bez określonego czasu."
            )
        )

    # nie planujemy tej samej operacji
    # równocześnie w dwóch tygodniach
    existing_task = (
        ProductionTask.objects
        .filter(
            production_unit=unit
        )
        .first()
    )

    if existing_task:

        if existing_task.plan_id == plan.id:
            return existing_task

        raise PlanningError(
            (
                "Ta operacja znajduje się już "
                "w innym planie produkcji."
            )
        )

    start = get_workday_start(
        day
    )

    task = ProductionTask.objects.create(
        plan=plan,
        production_unit=unit,
        work_station=station,
        start=start,
        end=add_work_minutes(
            start=start,
            minutes=duration,
        ),
        is_temporary=False,
    )

    task.persons.set(
        unit.persons.all()
    )

    return task


# ============================================================
# MOVE TASK
# ============================================================


@transaction.atomic
def move_task(
    *,
    plan,
    target_station_id,
    target_day,
    target_index,
    task_id=None,
    unit_id=None,
):
    """
    Główna funkcja dla drag&drop.

    Obsługuje:
    - task -> inny dzień,
    - task -> inne stanowisko,
    - zmianę kolejności,
    - unassigned ProductionUnit -> plan.
    """

    if (
        task_id is None
        and unit_id is None
    ):
        raise PlanningError(
            "Brak zadania lub operacji."
        )

    if (
        task_id is not None
        and unit_id is not None
    ):
        raise PlanningError(
            "Podano jednocześnie task i unit."
        )

    valid_dates = set(
        get_week_dates(
            year=plan.year,
            week=plan.week,
        )
    )

    if target_day not in valid_dates:
        raise PlanningError(
            "Docelowy dzień nie należy do tego tygodnia."
        )

    station = get_object_or_404(
        WorkStation,
        pk=target_station_id,
    )

    target_index = max(
        0,
        int(target_index),
    )

    source_station = None
    source_day = None


    # ========================================================
    # EXISTING TASK
    # ========================================================

    if task_id is not None:

        task = get_object_or_404(
            ProductionTask.objects
            .select_for_update()
            .select_related(
                "production_unit",
                "work_station",
            ),
            pk=task_id,
            plan=plan,
        )

        source_station = (
            task.work_station
        )

        source_day = task.start.date()


    # ========================================================
    # UNASSIGNED UNIT
    # ========================================================

    else:

        unit = get_object_or_404(
            ProductionUnit.objects
            .select_related(
                "production_order",
                "work_station",
            )
            .prefetch_related(
                "persons",
            ),
            pk=unit_id,
        )

        if unit.status == "FINISHED":
            raise PlanningError(
                "Zakończonej operacji nie można planować."
            )

        if unit.status == "IN PROGRESS":
            raise PlanningError(
                "Operacja jest już w trakcie produkcji."
            )

        task = create_task_from_unit(
            plan=plan,
            unit=unit,
            station=station,
            day=target_day,
        )


    # ========================================================
    # DESTINATION ORDER
    # ========================================================

    destination_tasks = (
        get_lane_tasks(
            plan=plan,
            station=station,
            day=target_day,
            lock=True,
        )
    )

    destination_tasks = [
        item
        for item in destination_tasks
        if item.id != task.id
    ]

    target_index = min(
        target_index,
        len(destination_tasks),
    )

    destination_tasks.insert(
        target_index,
        task,
    )


    # ========================================================
    # TEMP MOVE
    # ========================================================

    # Musimy najpierw przesunąć task do nowej lane,
    # aby recalculate_lane go pobrało.

    task.work_station = station

    task.start = get_workday_start(
        target_day
    )

    duration = (
        get_task_duration_minutes(
            task
        )
    )

    if not duration:
        raise PlanningError(
            "Brak czasu operacji."
        )

    task.end = add_work_minutes(
        start=task.start,
        minutes=duration,
    )

    task.save(
        update_fields=[
            "work_station",
            "start",
            "end",
        ]
    )


    # ========================================================
    # RECALCULATE TARGET
    # ========================================================

    recalculate_lane(
        plan=plan,
        station=station,
        day=target_day,
        ordered_task_ids=[
            item.id
            for item in destination_tasks
        ],
    )


    # ========================================================
    # RECALCULATE SOURCE
    # ========================================================

    if (
        source_station
        and source_day
        and (
            source_station.id
            != station.id
            or source_day
            != target_day
        )
    ):
        recalculate_lane(
            plan=plan,
            station=source_station,
            day=source_day,
        )

    return task


# ============================================================
# REMOVE TASK FROM PLAN
# ============================================================


@transaction.atomic
def remove_task_from_plan(
    *,
    plan,
    task_id,
):
    task = get_object_or_404(
        ProductionTask.objects
        .select_for_update()
        .select_related(
            "work_station",
        ),
        pk=task_id,
        plan=plan,
    )

    station = task.work_station

    day = task.start.date()

    task.delete()

    recalculate_lane(
        plan=plan,
        station=station,
        day=day,
    )


# ============================================================
# UNASSIGNED
# ============================================================


def get_unassigned_units():
    """
    Operacje, które nie są zakończone i nie mają
    żadnego ProductionTask.
    """

    planned_unit_ids = (
        ProductionTask.objects
        .values_list(
            "production_unit_id",
            flat=True,
        )
    )

    return (
        ProductionUnit.objects
        .exclude(
            id__in=planned_unit_ids
        )
        .exclude(
            status__in=(
                "FINISHED",
                "IN PROGRESS",
            )
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
            "-production_order__priority",
            "production_order__id_number",
            "sequence",
        )
    )


# ============================================================
# PLAN CONTEXT
# ============================================================


def get_weekly_plan_context(
    *,
    year,
    week,
):
    plan = get_or_create_weekly_plan(
        year=year,
        week=week,
    )

    dates = get_week_dates(
        year=year,
        week=week,
    )

    stations = list(
        WorkStation.objects
        .all()
        .order_by("name")
    )

    tasks = list(
        ProductionTask.objects
        .filter(
            plan=plan,
        )
        .select_related(
            "production_unit",
            "production_unit__production_order",
            "production_unit__production_order__customer",
            "work_station",
        )
        .prefetch_related(
            "persons",
        )
        .order_by(
            "work_station__name",
            "start",
            "id",
        )
    )

    tasks_by_lane = defaultdict(
        list
    )

    for task in tasks:

        local_start = task.start

        key = (
            task.work_station_id,
            local_start.date(),
        )

        tasks_by_lane[key].append(
            task
        )

    days = []

    today = datetime.date.today()

    for weekday, label in WEEK_DAYS:

        day = datetime.date.fromisocalendar(
            year,
            week,
            weekday,
        )

        days.append({
            "number": weekday,
            "label": label,
            "short_label": label[:3],
            "date": day,
            "is_today": day == today,
        })

    station_rows = []

    for station in stations:

        day_columns = []

        for day in days:

            lane_tasks = tasks_by_lane.get(
                (
                    station.id,
                    day["date"],
                ),
                [],
            )

            occupied_minutes = sum(
                (
                    get_task_duration_minutes(
                        task
                    )
                    or 0
                )
                for task in lane_tasks
            )

            occupancy_percent = round(
                (
                    occupied_minutes
                    / DAILY_CAPACITY_MINUTES
                )
                * 100,
                1,
            )

            day_columns.append({
                "day": day,
                "tasks": lane_tasks,
                "occupied_minutes":
                    occupied_minutes,
                "capacity_minutes":
                    DAILY_CAPACITY_MINUTES,
                "occupancy_percent":
                    occupancy_percent,
                "is_overloaded":
                    occupied_minutes
                    > DAILY_CAPACITY_MINUTES,
                "overload_minutes":
                    max(
                        0,
                        occupied_minutes
                        - DAILY_CAPACITY_MINUTES,
                    ),
            })

        station_rows.append({
            "station": station,
            "days": day_columns,
        })

    previous_week = get_previous_week(
        year=year,
        week=week,
    )

    next_week = get_next_week(
        year=year,
        week=week,
    )

    return {
        "plan": plan,

        "year": year,
        "week": week,

        "week_start": dates[0],
        "week_end": dates[-1],

        "days": days,

        "station_rows":
            station_rows,

        "unassigned_units":
            get_unassigned_units(),

        "unassigned_count":
            get_unassigned_units().count(),

        "daily_capacity_minutes":
            DAILY_CAPACITY_MINUTES,

        "previous_week":
            previous_week,

        "next_week":
            next_week,
    }