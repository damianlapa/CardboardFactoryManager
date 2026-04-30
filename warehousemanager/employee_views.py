# warehousemanager/employee_views.py

from django.http import JsonResponse
import datetime
from decimal import Decimal
from collections import defaultdict

from django.views import View
from django.shortcuts import render, get_object_or_404
from django.utils.dateparse import parse_date
from django.db import models

from warehousemanager.models import Person, Absence, Holiday, ExtraHour
from production.models import ProductionUnit


class EmployeeListView(View):
    template_name = "whm/employees/employee_list.html"

    def get(self, request):
        show_all = request.GET.get("all") == "1"

        workers_qs = Person.objects.all()

        if not show_all:
            workers_qs = workers_qs.filter(job_end__isnull=True)

        workers = []
        today = datetime.date.today()

        for w in workers_qs:
            end = w.job_end or today
            delta = end - w.job_start
            years = delta.days // 365
            months = (delta.days % 365) // 30

            workers.append({
                "worker": w,
                "seniority": f"{years} lat {months} mies." if years else f"{months} mies.",
                "status": "Aktywny" if not w.job_end else "Nieaktywny",
                "medical_expired": not w.medical_examination or w.medical_examination < today,
            })

        return render(request, self.template_name, {
            "workers": workers,
            "show_all": show_all,
        })


class EmployeeWorkTimeReportView(View):
    template_name = "whm/employees/work_time_report.html"

    BREAK_MINUTES_PER_DAY = 35
    WORK_MINUTES_PER_DAY = 8 * 60

    ABSENCE_FULL_DAY_TYPES = ["UW", "UB", "CH", "OP", "NN", "KW", "UO"]

    def _default_range(self):
        today = datetime.date.today()
        start = today.replace(day=1)
        end = today
        return start, end

    def _date_range(self, start, end):
        day = start
        while day <= end:
            yield day
            day += datetime.timedelta(days=1)

    def _safe_parse_date(self, value, default):
        if not value:
            return default
        parsed = parse_date(value)
        return parsed or default

    def _workdays_count(self, start, end):
        holidays = set(
            Holiday.objects
            .filter(holiday_date__gte=start, holiday_date__lte=end)
            .values_list("holiday_date", flat=True)
        )

        count = 0
        for day in self._date_range(start, end):
            if day.weekday() < 5 and day not in holidays:
                count += 1

        return count

    def _active_in_period_qs(self, start, end):
        return (
            Person.objects
            .filter(job_start__lte=end)
            .filter(
                # aktywni w zakresie
                # czyli nie zakończyli pracy albo zakończyli po początku zakresu
                models.Q(job_end__isnull=True) | models.Q(job_end__gte=start)
            )
            .order_by("last_name", "first_name")
        )

    def _person_available_minutes(self, person, start, end):
        """
        Liczymy dzień po dniu:
        - tylko dni robocze
        - tylko dni, gdy osoba była zatrudniona
        - odejmujemy pełne nieobecności
        - uwzględniamy ExtraHour:
            full_day=True  -> 480 + extra
            full_day=False -> tylko podana liczba godzin, np. 4h
        """

        holidays = set(
            Holiday.objects
            .filter(holiday_date__gte=start, holiday_date__lte=end)
            .values_list("holiday_date", flat=True)
        )

        absences = {
            a.absence_date: a
            for a in Absence.objects.filter(
                worker=person,
                absence_date__gte=start,
                absence_date__lte=end,
            )
        }

        extra_hours = {
            e.extras_date: e
            for e in ExtraHour.objects.filter(
                worker=person,
                extras_date__gte=start,
                extras_date__lte=end,
            )
        }

        workdays = 0
        physical_minutes = 0
        absence_days = 0
        partial_days = 0

        for day in self._date_range(start, end):
            if day.weekday() >= 5:
                continue

            if day in holidays:
                continue

            if person.job_start and day < person.job_start:
                continue

            if person.job_end and day > person.job_end:
                continue

            workdays += 1

            absence = absences.get(day)
            if absence and absence.absence_type in self.ABSENCE_FULL_DAY_TYPES:
                absence_days += 1
                continue

            minutes = self.WORK_MINUTES_PER_DAY

            extra = extra_hours.get(day)
            if extra:
                extra_minutes = int(Decimal(extra.quantity) * Decimal("60"))

                if extra.full_day:
                    minutes = self.WORK_MINUTES_PER_DAY + extra_minutes
                else:
                    minutes = extra_minutes
                    partial_days += 1

            physical_minutes += minutes

        break_minutes = max((workdays - absence_days), 0) * self.BREAK_MINUTES_PER_DAY
        net_minutes = max(physical_minutes - break_minutes, 0)

        return {
            "workdays": workdays,
            "base_minutes": workdays * self.WORK_MINUTES_PER_DAY,
            "absence_days": absence_days,
            "partial_days": partial_days,
            "physical_minutes": physical_minutes,
            "break_minutes": break_minutes,
            "net_minutes": net_minutes,
        }

    def _production_unit_minutes_by_person(self, start, end):
        """
        Zakładam, że ProductionUnit ma:
        - start
        - end
        - workers / worker / employee

        Niżej daję wariant najczęstszy: ManyToMany workers.
        Jeśli u Ciebie pole nazywa się inaczej, podmienimy jedną linijkę.
        """

        result = defaultdict(int)

        units = (
            ProductionUnit.objects
            .filter(start__date__gte=start, start__date__lte=end)
            .exclude(start__isnull=True)
            .exclude(end__isnull=True)
            .prefetch_related("persons")
        )

        for unit in units:
            minutes = int((unit.end - unit.start).total_seconds() / 60)

            workers = unit.persons.all()
            workers_count = workers.count()

            if workers_count == 0:
                continue

            minutes_per_worker = minutes / workers_count

            for worker in workers:
                result[worker.id] += minutes_per_worker

        return result

    def _percent(self, value, total):
        if not total:
            return 0
        return round((value / total) * 100, 1)

    def get(self, request):

        default_start, default_end = self._default_range()

        start = self._safe_parse_date(request.GET.get("start"), default_start)
        end = self._safe_parse_date(request.GET.get("end"), default_end)

        if end < start:
            start, end = end, start

        production_minutes_by_person = self._production_unit_minutes_by_person(start, end)

        rows = []

        totals = {
            "base_minutes": 0,
            "physical_minutes": 0,
            "net_minutes": 0,
            "production_minutes": 0,
        }

        show_all = request.GET.get("all") == "1"

        workers = self._active_in_period_qs(start, end)

        if not show_all:
            workers = workers.filter(occupancy_type="PRODUCTION")

        for person in workers:
            availability = self._person_available_minutes(person, start, end)
            production_minutes = int(production_minutes_by_person.get(person.id, 0))

            row = {
                "person": person,

                "workdays": availability["workdays"],
                "absence_days": availability["absence_days"],
                "partial_days": availability["partial_days"],

                "base_minutes": availability["base_minutes"],
                "physical_minutes": availability["physical_minutes"],
                "physical_percent": self._percent(
                    availability["physical_minutes"],
                    availability["base_minutes"],
                ),

                "break_minutes": availability["break_minutes"],
                "net_minutes": availability["net_minutes"],
                "net_percent": self._percent(
                    availability["net_minutes"],
                    availability["base_minutes"],
                ),

                "production_minutes": production_minutes,
                "production_vs_physical_percent": self._percent(
                    production_minutes,
                    availability["physical_minutes"],
                ),
                "production_vs_net_percent": self._percent(
                    production_minutes,
                    availability["net_minutes"],
                ),
            }

            rows.append(row)

            totals["base_minutes"] += availability["base_minutes"]
            totals["physical_minutes"] += availability["physical_minutes"]
            totals["net_minutes"] += availability["net_minutes"]
            totals["production_minutes"] += production_minutes

        context = {
            "start": start,
            "end": end,
            "rows": rows,
            "totals": {
                **totals,
                "physical_percent": self._percent(totals["physical_minutes"], totals["base_minutes"]),
                "net_percent": self._percent(totals["net_minutes"], totals["base_minutes"]),
                "production_vs_physical_percent": self._percent(totals["production_minutes"], totals["physical_minutes"]),
                "production_vs_net_percent": self._percent(totals["production_minutes"], totals["net_minutes"]),
            },
            "show_all": show_all,
        }

        return render(request, self.template_name, context)


class EmployeeProductionUnitsAjaxView(View):
    template_name = "whm/employees/_employee_production_units.html"

    def get(self, request, person_id):
        person = get_object_or_404(Person, id=person_id)

        start = parse_date(request.GET.get("start") or "")
        end = parse_date(request.GET.get("end") or "")

        if not start or not end:
            today = datetime.date.today()
            start = today.replace(day=1)
            end = today

        units = (
            ProductionUnit.objects
            .filter(
                persons=person,
                start__date__gte=start,
                start__date__lte=end,
            )
            .exclude(start__isnull=True)
            .exclude(end__isnull=True)
            .select_related(
                "production_order",
                "work_station",
            )
            .prefetch_related("persons")
            .order_by("start", "end")
        )

        rows = []
        total_minutes = 0

        previous = None

        for unit in units:
            minutes = int((unit.end - unit.start).total_seconds() / 60)

            overlap = False
            overlap_minutes = 0

            if previous and unit.start < previous["end"]:
                overlap = True
                overlap_end = min(unit.end, previous["end"])
                overlap_minutes = int((overlap_end - unit.start).total_seconds() / 60)

            row = {
                "unit": unit,
                "minutes": minutes,
                "persons_count": unit.persons.count(),
                "overlap": overlap,
                "overlap_minutes": max(overlap_minutes, 0),
            }

            rows.append(row)
            total_minutes += minutes

            if not previous or unit.end > previous["end"]:
                previous = {
                    "unit": unit,
                    "start": unit.start,
                    "end": unit.end,
                }

        html = render(
            request,
            self.template_name,
            {
                "person": person,
                "rows": rows,
                "total_minutes": total_minutes,
                "total_hours": round(total_minutes / 60, 2),
                "overlaps_count": sum(1 for r in rows if r["overlap"]),
            }
        ).content.decode("utf-8")

        return JsonResponse({
            "html": html,
            "total_minutes": total_minutes,
        })