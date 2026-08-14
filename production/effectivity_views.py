from django.shortcuts import render, HttpResponse, redirect
from django.views import View

from production.models import WorkStation


class OEEView(View):
    def get(self, request, year, month):
        workstations = WorkStation.objects.all()
        result = ''
        for w in workstations:
            result += f'{w.name:40} - {w.oee_factor(year, month)}</br>'
        return HttpResponse(result)


import datetime

from django.shortcuts import render

from production.services.workstation_statistics import (
    workstation_statistics,
)


import datetime
from collections import defaultdict

from django.contrib.auth.mixins import PermissionRequiredMixin
from django.shortcuts import render
from django.utils import timezone
from django.views import View

from production.models import WorkStation, ProductionUnit
from warehousemanager.models import Holiday


class WorkstationEffectivityView(PermissionRequiredMixin, View):
    permission_required = "production.view_productionunit"
    template_name = "production/workstation_effectivity.html"

    WORK_START = datetime.time(7, 0)
    WORK_END = datetime.time(15, 0)

    BREAKS = (
        (datetime.time(9, 0), datetime.time(9, 5)),
        (datetime.time(11, 0), datetime.time(11, 20)),
        (datetime.time(12, 30), datetime.time(12, 35)),
        (datetime.time(14, 0), datetime.time(14, 5)),
    )

    def get_work_intervals_for_day(self, day):
        """
        Zwraca przedziały faktycznej dostępności stanowiska w danym dniu.

        07:00-09:00
        09:15-11:00
        11:20-15:00

        Razem: 445 minut.
        """

        if day.weekday() >= 5:
            return []

        if Holiday.objects.filter(holiday_date=day).exists():
            return []

        work_start = datetime.datetime.combine(
            day,
            self.WORK_START,
        )

        work_end = datetime.datetime.combine(
            day,
            self.WORK_END,
        )

        intervals = []

        current = work_start

        for break_start_time, break_end_time in self.BREAKS:

            break_start = datetime.datetime.combine(
                day,
                break_start_time,
            )

            break_end = datetime.datetime.combine(
                day,
                break_end_time,
            )

            if current < break_start:
                intervals.append(
                    (current, break_start)
                )

            current = break_end

        if current < work_end:
            intervals.append(
                (current, work_end)
            )

        return intervals

    def get_unit_work_intervals(
            self,
            unit_start,
            unit_end,
            date_from,
            date_to,
    ):
        """
        Zwraca tylko tę część ProductionUnit,
        która przypada na faktyczny czas pracy.
        """

        intervals = []

        current_day = max(
            unit_start.date(),
            date_from,
        )

        last_day = min(
            unit_end.date(),
            date_to,
        )

        while current_day <= last_day:

            work_intervals = self.get_work_intervals_for_day(
                current_day
            )

            for work_start, work_end in work_intervals:

                start = max(
                    unit_start,
                    work_start,
                )

                end = min(
                    unit_end,
                    work_end,
                )

                if start < end:
                    intervals.append(
                        (start, end)
                    )

            current_day += datetime.timedelta(days=1)

        return intervals

    WORKDAY_MINUTES = 8 * 60 - 35  # 445 minut

    def get(self, request, *args, **kwargs):
        today = datetime.date.today()

        date_from = self.parse_date(
            request.GET.get("date_from"),
            today.replace(day=1),
        )

        date_to = self.parse_date(
            request.GET.get("date_to"),
            today,
        )

        if date_from > date_to:
            date_from, date_to = date_to, date_from

        statistics = self.get_statistics(
            date_from=date_from,
            date_to=date_to,
        )

        context = {
            "date_from": date_from,
            "date_to": date_to,
            "statistics": statistics,
        }

        return render(
            request,
            self.template_name,
            context,
        )

    @staticmethod
    def parse_date(value, default):
        if not value:
            return default

        try:
            return datetime.date.fromisoformat(value)
        except ValueError:
            return default

    def get_working_days(self, date_from, date_to):
        holidays = set(
            Holiday.objects.filter(
                holiday_date__range=(date_from, date_to)
            ).values_list(
                "holiday_date",
                flat=True,
            )
        )

        days = []

        current = date_from

        while current <= date_to:

            if (
                current.weekday() < 5
                and current not in holidays
            ):
                days.append(current)

            current += datetime.timedelta(days=1)

        return days

    @staticmethod
    def merge_intervals(intervals):
        """
        Łączy nachodzące na siebie przedziały.

        Przykład:

        08:00 - 10:00
        09:00 - 11:00

        wynik:
        08:00 - 11:00
        """

        if not intervals:
            return []

        intervals = sorted(
            intervals,
            key=lambda interval: interval[0],
        )

        merged = [
            [intervals[0][0], intervals[0][1]]
        ]

        for start, end in intervals[1:]:

            last_start, last_end = merged[-1]

            if start <= last_end:
                merged[-1][1] = max(
                    last_end,
                    end,
                )
            else:
                merged.append(
                    [start, end]
                )

        return merged

    def get_statistics(self, date_from, date_to):
        period_start = datetime.datetime.combine(
            date_from,
            datetime.time.min,
        )

        period_end = datetime.datetime.combine(
            date_to + datetime.timedelta(days=1),
            datetime.time.min,
        )

        working_days = self.get_working_days(
            date_from=date_from,
            date_to=date_to,
        )

        available_minutes = (
                len(working_days)
                * self.WORKDAY_MINUTES
        )

        units = (
            ProductionUnit.objects
            .filter(
                start__isnull=False,
                end__isnull=False,
                start__lt=period_end,
                end__gt=period_start,
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
            units_by_station[
                unit.work_station_id
            ].append(unit)

        stations_results = []

        stations_results = []

        for station in WorkStation.objects.all():
            station_units = units_by_station.get(
                station.id,
                [],
            )

            result = self.calculate_station_statistics(
                station=station,
                units=station_units,
                date_from=date_from,
                date_to=date_to,
                available_minutes=available_minutes,
            )

            if result["occupied_minutes"] > 0:
                stations_results.append(result)

        stations_results.sort(
            key=lambda item: item["occupancy_percent"],
            reverse=True,
        )

        return {
            "working_days": len(working_days),
            "available_minutes": available_minutes,
            "stations": stations_results,
        }

    def calculate_station_statistics(
            self,
            station,
            units,
            date_from,
            date_to,
            available_minutes,
    ):
        station_intervals = []

        worker_minutes = 0
        persons_distribution = defaultdict(float)

        for unit in units:

            unit_intervals = self.get_unit_work_intervals(
                unit_start=unit.start,
                unit_end=unit.end,
                date_from=date_from,
                date_to=date_to,
            )

            if not unit_intervals:
                continue

            persons_count = len(
                unit.persons.all()
            )

            for start, end in unit_intervals:
                minutes = (
                                  end - start
                          ).total_seconds() / 60

                station_intervals.append(
                    (start, end)
                )

                worker_minutes += (
                        minutes * persons_count
                )

                persons_distribution[
                    persons_count
                ] += minutes

        # Stanowisko może mieć kilka nachodzących ProductionUnit.
        # Dla zajętości maszyny nie możemy liczyć ich podwójnie.
        merged_intervals = self.merge_intervals(
            station_intervals
        )

        occupied_minutes = sum(
            (
                    end - start
            ).total_seconds() / 60
            for start, end in merged_intervals
        )

        occupancy_percent = (
            occupied_minutes
            / available_minutes
            * 100
            if available_minutes
            else 0
        )

        distribution = []

        for persons, minutes in sorted(
                persons_distribution.items()
        ):
            distribution.append({
                "persons": persons,
                "minutes": round(minutes, 2),
                "hours": round(minutes / 60, 2),
                "worker_hours": round(
                    minutes * persons / 60,
                    2,
                ),
            })

        return {
            "station": station,

            "available_minutes": round(
                available_minutes,
                2,
            ),

            "available_hours": round(
                available_minutes / 60,
                2,
            ),

            "occupied_minutes": round(
                occupied_minutes,
                2,
            ),

            "occupied_hours": round(
                occupied_minutes / 60,
                2,
            ),

            "occupancy_percent": round(
                occupancy_percent,
                1,
            ),

            "worker_minutes": round(
                worker_minutes,
                2,
            ),

            "worker_hours": round(
                worker_minutes / 60,
                2,
            ),

            "persons_distribution": distribution,

            "units_count": len(units),
        }