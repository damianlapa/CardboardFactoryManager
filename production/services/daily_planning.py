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

DAY_START = datetime.time(7, 0)
DAY_END = datetime.time(15, 0)

BREAK_START = datetime.time(11, 0)
BREAK_END = datetime.time(11, 20)

DAY_START_MINUTES = 7 * 60
DAY_END_MINUTES = 15 * 60

DAY_DURATION_MINUTES = (
    DAY_END_MINUTES
    - DAY_START_MINUTES
)

BREAK_START_OFFSET = (
    11 * 60
    - DAY_START_MINUTES
)

BREAK_DURATION_MINUTES = 20

SNAP_MINUTES = 15


# ============================================================
# WORKSTATION CAPACITY
# ============================================================

WORKSTATION_CAPACITY = {
    "OBRYWANIE": 3,
    "EUROKERY DUŻE": 2,
    "EUROKERY MAŁE": 2,
}


class DailyPlanningError(Exception):
    pass


# ============================================================
# WORKSTATION
# ============================================================


def get_workstation_capacity(workstation):
    if not workstation:
        return 1

    name = (
        workstation.name
        .upper()
        .strip()
    )

    return WORKSTATION_CAPACITY.get(
        name,
        1,
    )


# ============================================================
# WORKING DAYS
# ============================================================


def is_working_day(day):
    return day.isoweekday() <= 5


def next_working_day(day):
    result = (
        day
        + datetime.timedelta(days=1)
    )

    while not is_working_day(result):
        result += datetime.timedelta(
            days=1
        )

    return result


def previous_working_day(day):
    result = (
        day
        - datetime.timedelta(days=1)
    )

    while not is_working_day(result):
        result -= datetime.timedelta(
            days=1
        )

    return result


# ============================================================
# WEEK PLAN
# ============================================================


def get_day_week_plan(day):
    iso = day.isocalendar()

    plan, _ = (
        WeeklyPlan.objects
        .get_or_create(
            year=iso.year,
            week=iso.week,
        )
    )

    return plan


# ============================================================
# TIME
# ============================================================


def snap_minutes(value):
    value = int(value)

    return int(
        round(
            value / SNAP_MINUTES
        )
        * SNAP_MINUTES
    )


def normalize_start_minutes(value):
    """
    Start może dochodzić do 14:45.
    Nie ograniczamy taska jego długością,
    ponieważ może przejść na kolejny dzień.
    """

    value = snap_minutes(
        value
    )

    value = max(
        0,
        value,
    )

    value = min(
        DAY_DURATION_MINUTES
        - SNAP_MINUTES,
        value,
    )

    # 11:00-11:20 jest przerwą.
    # Przy snapie 15 minut możemy dostać 11:00 lub 11:15.
    if (
        BREAK_START_OFFSET
        <= value
        < BREAK_START_OFFSET
        + BREAK_DURATION_MINUTES
    ):
        value = (
            BREAK_START_OFFSET
            + BREAK_DURATION_MINUTES
        )

    return value


def datetime_from_minutes(
    *,
    day,
    minutes_from_start,
):
    minutes_from_start = (
        normalize_start_minutes(
            minutes_from_start
        )
    )

    total_minutes = (
        DAY_START_MINUTES
        + minutes_from_start
    )

    hour = total_minutes // 60
    minute = total_minutes % 60

    return datetime.datetime.combine(
        day,
        datetime.time(
            hour,
            minute,
        ),
    )


def minutes_from_day_start(value):
    if not value:
        return 0

    return (
        value.hour * 60
        + value.minute
        - DAY_START_MINUTES
    )


# ============================================================
# ADD WORKING MINUTES
# ============================================================


def add_working_minutes(
    start,
    duration_minutes,
):
    """
    Dodaje REALNE minuty produkcyjne.

    Pomija:
    - 11:00-11:20,
    - 15:00-07:00,
    - soboty,
    - niedziele.
    """

    remaining = int(
        duration_minutes
    )

    current = start

    while remaining > 0:

        # Weekend
        if not is_working_day(
            current.date()
        ):
            current = datetime.datetime.combine(
                next_working_day(
                    current.date()
                ),
                DAY_START,
            )
            continue

        # Przed rozpoczęciem pracy
        if current.time() < DAY_START:
            current = datetime.datetime.combine(
                current.date(),
                DAY_START,
            )
            continue

        # Po zakończeniu pracy
        if current.time() >= DAY_END:
            current = datetime.datetime.combine(
                next_working_day(
                    current.date()
                ),
                DAY_START,
            )
            continue

        # Wewnątrz przerwy
        if (
            BREAK_START
            <= current.time()
            < BREAK_END
        ):
            current = datetime.datetime.combine(
                current.date(),
                BREAK_END,
            )
            continue

        # Najbliższa granica
        if current.time() < BREAK_START:
            boundary = datetime.datetime.combine(
                current.date(),
                BREAK_START,
            )

        else:
            boundary = datetime.datetime.combine(
                current.date(),
                DAY_END,
            )

        available = int(
            (
                boundary
                - current
            ).total_seconds()
            // 60
        )

        if remaining <= available:

            current += datetime.timedelta(
                minutes=remaining
            )

            remaining = 0

        else:

            remaining -= available

            current = boundary

            if (
                current.time()
                == BREAK_START
            ):
                current = datetime.datetime.combine(
                    current.date(),
                    BREAK_END,
                )

            else:
                current = datetime.datetime.combine(
                    next_working_day(
                        current.date()
                    ),
                    DAY_START,
                )

    return current


# ============================================================
# DURATION
# ============================================================


def get_unit_duration(unit):
    if (
        unit.estimated_time
        and unit.estimated_time > 0
    ):
        return int(
            unit.estimated_time
        )

    return None


def get_task_duration(task):
    duration = get_unit_duration(
        task.production_unit
    )

    if duration:
        return duration

    if (
        task.start
        and task.end
    ):
        return max(
            1,
            int(
                (
                    task.end
                    - task.start
                ).total_seconds()
                // 60
            ),
        )

    return None


# ============================================================
# DISPLAY SEGMENTS
# ============================================================


def build_task_day_segments(
    *,
    start,
    duration,
):
    """
    Jeden task może być widoczny na kilku dniach.

    Przykład:
    start: pon 14:00
    duration: 120 min

    daje:
    pon 14:00-15:00
    wt  07:00-08:00

    W obrębie pojedynczego dnia task jest wyświetlany
    jako jeden ciągły span. Jeżeli przecina przerwę
    11:00-11:20, wizualnie przechodzi przez zaznaczoną
    strefę przerwy.
    """

    final_end = add_working_minutes(
        start,
        duration,
    )

    segments = []

    current_day = start.date()

    while current_day <= final_end.date():

        if not is_working_day(
            current_day
        ):
            current_day += datetime.timedelta(
                days=1
            )
            continue

        if current_day == start.date():
            segment_start = start
        else:
            segment_start = datetime.datetime.combine(
                current_day,
                DAY_START,
            )

        if current_day == final_end.date():
            segment_end = final_end
        else:
            segment_end = datetime.datetime.combine(
                current_day,
                DAY_END,
            )

        if segment_end > segment_start:

            start_minutes = (
                minutes_from_day_start(
                    segment_start
                )
            )

            display_minutes = int(
                (
                    segment_end
                    - segment_start
                ).total_seconds()
                // 60
            )

            segments.append({
                "day":
                    current_day,

                "start_dt":
                    segment_start,

                "end_dt":
                    segment_end,

                "start_minutes":
                    start_minutes,

                "display_minutes":
                    display_minutes,

                "left_percent":
                    (
                        start_minutes
                        / DAY_DURATION_MINUTES
                        * 100
                    ),

                "width_percent":
                    (
                        display_minutes
                        / DAY_DURATION_MINUTES
                        * 100
                    ),

                "continues_from_previous":
                    current_day
                    != start.date(),

                "continues_next":
                    current_day
                    != final_end.date(),
            })

        current_day += datetime.timedelta(
            days=1
        )

    return (
        segments,
        final_end,
    )


def get_task_segment_for_day(
    task,
    day,
):
    duration = get_task_duration(
        task
    )

    if not duration:
        return None

    segments, final_end = (
        build_task_day_segments(
            start=task.start,
            duration=duration,
        )
    )

    for segment in segments:

        if segment["day"] == day:

            result = dict(
                segment
            )

            result["final_end"] = (
                final_end
            )

            result["total_duration"] = (
                duration
            )

            return result

    return None


# ============================================================
# DAY TASKS
# ============================================================


def get_day_tasks(day):
    """
    Pobieramy także taski rozpoczęte wcześniej,
    które kończą się danego dnia.
    """

    day_start_dt = datetime.datetime.combine(
        day,
        DAY_START,
    )

    next_day_dt = datetime.datetime.combine(
        day + datetime.timedelta(days=1),
        DAY_START,
    )

    tasks = (
        ProductionTask.objects
        .filter(
            start__lt=next_day_dt,
            end__gt=day_start_dt,
        )
        .select_related(
            "plan",
            "production_unit",
            "production_unit__production_order",
            "production_unit__production_order__customer",
            "work_station",
        )
        .prefetch_related(
            "persons",
            "production_unit__persons",
        )
        .order_by(
            "work_station__name",
            "start",
            "id",
        )
    )

    result = []

    for task in tasks:

        segment = (
            get_task_segment_for_day(
                task,
                day,
            )
        )

        if segment:
            result.append(
                task
            )

    return list(
        result
    )


# ============================================================
# UNPLANNED
# ============================================================


def get_unplanned_units():
    planned_ids = (
        ProductionTask.objects
        .values_list(
            "production_unit_id",
            flat=True,
        )
    )

    return (
        ProductionUnit.objects
        .exclude(
            id__in=planned_ids
        )
        .exclude(
            status="FINISHED"
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
            "work_station__name",
            "production_order__id_number",
            "sequence",
        )
    )


# ============================================================
# INTERVALS
# ============================================================


def intervals_overlap(
    start_a,
    end_a,
    start_b,
    end_b,
):
    return (
        start_a < end_b
        and end_a > start_b
    )


# ============================================================
# CAPACITY VALIDATION
# ============================================================


def validate_station_capacity(
    *,
    station,
    start,
    duration,
    exclude_task_id=None,
):
    capacity = (
        get_workstation_capacity(
            station
        )
    )

    proposed_segments, proposed_end = (
        build_task_day_segments(
            start=start,
            duration=duration,
        )
    )

    queryset = (
        ProductionTask.objects
        .filter(
            work_station=station,
            start__lt=proposed_end,
            end__gt=start,
        )
        .select_related(
            "production_unit",
        )
    )

    if exclude_task_id:
        queryset = queryset.exclude(
            pk=exclude_task_id
        )

    existing_tasks = list(
        queryset
    )

    for proposed in proposed_segments:

        events = []

        # Nowy task
        events.append(
            (
                proposed["start_dt"],
                1,
            )
        )

        events.append(
            (
                proposed["end_dt"],
                -1,
            )
        )

        for existing in existing_tasks:

            existing_segment = (
                get_task_segment_for_day(
                    existing,
                    proposed["day"],
                )
            )

            if not existing_segment:
                continue

            if not intervals_overlap(
                proposed["start_dt"],
                proposed["end_dt"],
                existing_segment["start_dt"],
                existing_segment["end_dt"],
            ):
                continue

            events.append(
                (
                    existing_segment["start_dt"],
                    1,
                )
            )

            events.append(
                (
                    existing_segment["end_dt"],
                    -1,
                )
            )

        # -1 przed +1 przy tej samej godzinie.
        # Dzięki temu 08-09 i 09-10 się nie konfliktują.
        events.sort(
            key=lambda item: (
                item[0],
                item[1],
            )
        )

        active = 0

        for _, change in events:

            active += change

            if active > capacity:

                raise DailyPlanningError(
                    (
                        f"Brak wolnego miejsca na stanowisku "
                        f"{station.name} w tym czasie "
                        f"(pojemność: {capacity})."
                    )
                )

    return True


# ============================================================
# LANE ASSIGNMENT
# ============================================================


def lane_is_available(
    *,
    lane_tasks,
    item,
):
    current = item["segment"]

    for existing in lane_tasks:

        other = existing["segment"]

        if intervals_overlap(
            current["start_dt"],
            current["end_dt"],
            other["start_dt"],
            other["end_dt"],
        ):
            return False

    return True


def assign_tasks_to_lanes(
    *,
    station,
    task_items,
):
    capacity = (
        get_workstation_capacity(
            station
        )
    )

    lanes = [
        {
            "number": index + 1,
            "tasks": [],
        }
        for index in range(
            capacity
        )
    ]

    overflow = []

    sorted_items = sorted(
        task_items,
        key=lambda item: (
            item["segment"]["start_dt"],
            item["segment"]["end_dt"],
            item["task"].id,
        ),
    )

    for item in sorted_items:

        assigned = False

        for lane in lanes:

            if lane_is_available(
                lane_tasks=lane["tasks"],
                item=item,
            ):
                item["lane"] = (
                    lane["number"]
                )

                item["overflow"] = False

                lane["tasks"].append(
                    item
                )

                assigned = True

                break

        if not assigned:

            item["lane"] = None
            item["overflow"] = True

            overflow.append(
                item
            )

    return {
        "capacity":
            capacity,

        "lanes":
            lanes,

        "overflow":
            overflow,

        "has_overflow":
            bool(overflow),
    }


# ============================================================
# CONTEXT
# ============================================================


def get_day_planning_context(day):
    tasks = get_day_tasks(
        day
    )

    stations = list(
        WorkStation.objects
        .all()
        .order_by(
            "name"
        )
    )

    tasks_by_station = defaultdict(
        list
    )

    for task in tasks:

        segment = (
            get_task_segment_for_day(
                task,
                day,
            )
        )

        if not segment:
            continue

        tasks_by_station[
            task.work_station_id
        ].append({
            "task":
                task,

            "segment":
                segment,
        })

    station_rows = []

    for station in stations:

        lane_data = (
            assign_tasks_to_lanes(
                station=station,
                task_items=tasks_by_station.get(
                    station.id,
                    [],
                ),
            )
        )

        station_rows.append({
            "station":
                station,

            "capacity":
                lane_data["capacity"],

            "lanes":
                lane_data["lanes"],

            "overflow":
                lane_data["overflow"],

            "has_overflow":
                lane_data["has_overflow"],
        })

    hours = []

    for hour in range(
        7,
        16,
    ):

        hours.append({
            "hour":
                hour,

            "label":
                f"{hour:02d}:00",

            "offset_percent":
                (
                    (
                        hour * 60
                        - DAY_START_MINUTES
                    )
                    / DAY_DURATION_MINUTES
                    * 100
                ),
        })

    break_left_percent = (
        BREAK_START_OFFSET
        / DAY_DURATION_MINUTES
        * 100
    )

    break_width_percent = (
        BREAK_DURATION_MINUTES
        / DAY_DURATION_MINUTES
        * 100
    )

    return {
        "day":
            day,

        "previous_day":
            previous_working_day(
                day
            ),

        "next_day":
            next_working_day(
                day
            ),

        "station_rows":
            station_rows,

        "hours":
            hours,

        "day_start":
            DAY_START,

        "day_end":
            DAY_END,

        "day_duration_minutes":
            DAY_DURATION_MINUTES,

        "snap_minutes":
            SNAP_MINUTES,

        "break_left_percent":
            break_left_percent,

        "break_width_percent":
            break_width_percent,

        "unplanned_units":
            get_unplanned_units(),
    }


# ============================================================
# CREATE
# ============================================================


@transaction.atomic
def create_task_from_unit(
    *,
    day,
    unit_id,
    station_id,
    start_minutes,
):
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
        raise DailyPlanningError(
            "Nie można planować zakończonej operacji."
        )

    if (
        ProductionTask.objects
        .filter(
            production_unit=unit
        )
        .exists()
    ):
        raise DailyPlanningError(
            "Ta jednostka jest już zaplanowana."
        )

    duration = (
        get_unit_duration(
            unit
        )
    )

    if not duration:
        raise DailyPlanningError(
            "Jednostka nie ma ustawionego estimated_time."
        )

    station = get_object_or_404(
        WorkStation,
        pk=station_id,
    )

    start_minutes = (
        normalize_start_minutes(
            start_minutes
        )
    )

    start = datetime_from_minutes(
        day=day,
        minutes_from_start=start_minutes,
    )

    final_end = add_working_minutes(
        start,
        duration,
    )

    validate_station_capacity(
        station=station,
        start=start,
        duration=duration,
    )

    # WeeklyPlan przypisujemy wg tygodnia rozpoczęcia.
    plan = get_day_week_plan(
        day
    )

    task = ProductionTask.objects.create(
        plan=plan,
        production_unit=unit,
        work_station=station,
        start=start,
        end=final_end,
        is_temporary=False,
    )

    task.persons.set(
        unit.persons.all()
    )

    return task


# ============================================================
# MOVE
# ============================================================


@transaction.atomic
def move_task(
    *,
    day,
    task_id,
    station_id,
    start_minutes,
):
    task = get_object_or_404(
        ProductionTask.objects
        .select_for_update()
        .select_related(
            "production_unit",
            "production_unit__production_order",
            "work_station",
        ),
        pk=task_id,
    )

    duration = (
        get_task_duration(
            task
        )
    )

    if not duration:
        raise DailyPlanningError(
            "Nie można ustalić czasu trwania operacji."
        )

    station = get_object_or_404(
        WorkStation,
        pk=station_id,
    )

    start_minutes = (
        normalize_start_minutes(
            start_minutes
        )
    )

    start = datetime_from_minutes(
        day=day,
        minutes_from_start=start_minutes,
    )

    final_end = add_working_minutes(
        start,
        duration,
    )

    validate_station_capacity(
        station=station,
        start=start,
        duration=duration,
        exclude_task_id=task.id,
    )

    task.plan = (
        get_day_week_plan(
            day
        )
    )

    task.work_station = station
    task.start = start
    task.end = final_end

    task.save(
        update_fields=[
            "plan",
            "work_station",
            "start",
            "end",
        ]
    )

    return task


# ============================================================
# REMOVE
# ============================================================


@transaction.atomic
def remove_task(
    *,
    task_id,
):
    task = get_object_or_404(
        ProductionTask.objects
        .select_for_update(),
        pk=task_id,
    )

    task.delete()


# ============================================================
# JSON
# ============================================================


def get_task_json(
    task,
    *,
    day,
):
    unit = task.production_unit
    order = unit.production_order

    segment = (
        get_task_segment_for_day(
            task,
            day,
        )
    )

    if not segment:
        raise DailyPlanningError(
            "Task nie posiada segmentu dla tego dnia."
        )

    return {
        "id":
            task.id,

        "unit_id":
            unit.id,

        "station_id":
            task.work_station_id,

        "station_capacity":
            get_workstation_capacity(
                task.work_station
            ),

        "start":
            segment["start_dt"].strftime(
                "%H:%M"
            ),

        "end":
            segment["end_dt"].strftime(
                "%H:%M"
            ),

        "final_end_date":
            segment["final_end"].strftime(
                "%Y-%m-%d"
            ),

        "final_end":
            segment["final_end"].strftime(
                "%H:%M"
            ),

        "start_minutes":
            segment["start_minutes"],

        "display_duration":
            segment["display_minutes"],

        "total_duration":
            segment["total_duration"],

        "left_percent":
            segment["left_percent"],

        "width_percent":
            segment["width_percent"],

        "continues_from_previous":
            segment[
                "continues_from_previous"
            ],

        "continues_next":
            segment[
                "continues_next"
            ],

        "order":
            order.id_number,

        "customer":
            str(
                order.customer
            ),

        "quantity":
            order.quantity or 0,
    }