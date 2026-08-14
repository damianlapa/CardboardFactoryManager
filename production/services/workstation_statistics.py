import datetime
from collections import defaultdict

from django.utils import timezone

from production.models import WorkStation, ProductionUnit
from warehousemanager.models import Holiday


WORKDAY_MINUTES = 8 * 60 - 35  # 445


def overlap_minutes(start1, end1, start2, end2):
    """
    Zwraca część przedziału start1-end1,
    która znajduje się wewnątrz start2-end2.
    """
    start = max(start1, start2)
    end = min(end1, end2)

    if start >= end:
        return 0

    return (end - start).total_seconds() / 60


def merge_intervals(intervals):
    """
    Scala nachodzące na siebie przedziały.

    Np.
    08:00-10:00
    09:00-11:00

    daje:
    08:00-11:00

    Dzięki temu stanowisko liczymy jako zajęte 3h,
    a nie 4h.
    """
    if not intervals:
        return []

    intervals = sorted(intervals, key=lambda x: x[0])

    merged = [list(intervals[0])]

    for start, end in intervals[1:]:
        last_start, last_end = merged[-1]

        if start <= last_end:
            merged[-1][1] = max(last_end, end)
        else:
            merged.append([start, end])

    return merged


def get_working_days(date_from, date_to):
    holidays = set(
        Holiday.objects.filter(
            holiday_date__range=(date_from, date_to)
        ).values_list("holiday_date", flat=True)
    )

    days = []

    current = date_from

    while current <= date_to:
        if current.weekday() < 5 and current not in holidays:
            days.append(current)

        current += datetime.timedelta(days=1)

    return days


def workstation_statistics(date_from, date_to):
    """
    date_from / date_to -> datetime.date
    """

    tz = timezone.get_current_timezone()

    period_start = timezone.make_aware(
        datetime.datetime.combine(date_from, datetime.time.min),
        timezone=tz,
    )

    period_end = timezone.make_aware(
        datetime.datetime.combine(
            date_to + datetime.timedelta(days=1),
            datetime.time.min,
        ),
        timezone=tz,
    )

    working_days = get_working_days(date_from, date_to)

    available_minutes = len(working_days) * WORKDAY_MINUTES

    units = (
        ProductionUnit.objects
        .filter(
            start__lt=period_end,
            end__gt=period_start,
            start__isnull=False,
            end__isnull=False,
        )
        .select_related(
            "work_station",
            "production_order",
        )
        .prefetch_related("persons")
        .order_by("start")
    )

    units_by_station = defaultdict(list)

    for unit in units:
        units_by_station[unit.work_station_id].append(unit)

    results = []

    for station in WorkStation.objects.all():

        station_units = units_by_station.get(station.id, [])

        # --------------------------------------------------
        # 1. CZAS ZAJĘCIA STANOWISKA
        # --------------------------------------------------

        intervals = []

        for unit in station_units:

            start = max(unit.start, period_start)
            end = min(unit.end, period_end)

            if start < end:
                intervals.append((start, end))

        merged = merge_intervals(intervals)

        occupied_minutes = sum(
            (end - start).total_seconds() / 60
            for start, end in merged
        )

        # --------------------------------------------------
        # 2. ROBOCZOGODZINY
        # --------------------------------------------------

        worker_minutes = 0

        # ile czasu występowała dana liczba pracowników
        persons_distribution = defaultdict(float)

        for unit in station_units:

            start = max(unit.start, period_start)
            end = min(unit.end, period_end)

            if start >= end:
                continue

            minutes = (end - start).total_seconds() / 60

            persons_count = unit.persons.count()

            worker_minutes += minutes * persons_count

            persons_distribution[persons_count] += minutes

        # --------------------------------------------------

        occupancy_percent = (
            occupied_minutes / available_minutes * 100
            if available_minutes
            else 0
        )

        results.append({
            "station": station,
            "available_minutes": available_minutes,

            "occupied_minutes": round(occupied_minutes, 2),
            "occupied_hours": round(occupied_minutes / 60, 2),

            "occupancy_percent": round(occupancy_percent, 2),

            "worker_minutes": round(worker_minutes, 2),
            "worker_hours": round(worker_minutes / 60, 2),

            "persons_distribution": {
                persons: {
                    "minutes": round(minutes, 2),
                    "hours": round(minutes / 60, 2),
                }
                for persons, minutes
                in sorted(persons_distribution.items())
            },

            "units_count": len(station_units),
        })

    return {
        "date_from": date_from,
        "date_to": date_to,
        "working_days": len(working_days),
        "available_minutes": available_minutes,
        "stations": results,
    }
