import calendar
import datetime
from decimal import Decimal
from collections import defaultdict

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.shortcuts import render
from django.views import View

from warehousemanager.models import Absence, Contract, Holiday, ExtraHour


HOURS_PER_DAY = Decimal("8.00")
BREAK_HOURS = Decimal("35") / Decimal("60")

ABSENCE_TYPES_OUT_OF_WORK = [
    "CH",  # Chorobowe
    "OP",  # Opieka
    "UW",  # Urlop wypoczynkowy
    "UŻ",  # Urlop na żądanie
    "UO",  # Urlop okolicznościowy
    "UB",  # Urlop bezpłatny
    "NN",  # Nieusprawiedliwiona
    "KW",  # Kwarantanna
    "IZ",  # Izolacja
]


class ProductionEffectiveWorkHoursView(LoginRequiredMixin, View):
    """
    Raport efektywnych godzin pracy pracowników produkcyjnych.

    Założenia:
    - tylko Contract.type == "UOP",
    - tylko worker.occupancy_type == "PRODUCTION",
    - dni robocze = poniedziałek-piątek minus Holiday,
    - dzień bazowy = 8h,
    - absencje z ABSENCE_TYPES_OUT_OF_WORK oznaczają 0h pracy,
    - ExtraHour full_day=True: 8h + quantity,
    - ExtraHour full_day=False: tylko quantity,
    - przerwa płatna 35 minut odejmowana od efektywnej pracy tylko gdy actual_hours > 0.
    """

    login_url = "login"
    template_name = "whm/production_effective_work_hours.html"

    def get(self, request):
        today = datetime.date.today()

        year = self._safe_int(request.GET.get("year"), today.year)
        month = self._safe_int(request.GET.get("month"), today.month)

        if month < 1 or month > 12:
            month = today.month

        month_start = datetime.date(year, month, 1)
        month_end = datetime.date(year, month, calendar.monthrange(year, month)[1])

        previous_month_date = month_start - datetime.timedelta(days=1)
        next_month_date = month_end + datetime.timedelta(days=1)

        contracts = (
            Contract.objects
            .filter(
                type="UOP",
                worker__occupancy_type="PRODUCTION",
                date_start__lte=month_end,
            )
            .filter(
                Q(date_end__isnull=True) | Q(date_end__gte=month_start)
            )
            .select_related("worker")
            .order_by("worker__last_name", "worker__first_name", "date_start")
        )

        holidays = set(
            Holiday.objects
            .filter(
                holiday_date__gte=month_start,
                holiday_date__lte=month_end,
            )
            .values_list("holiday_date", flat=True)
        )

        rows = []

        for contract in contracts:
            worker = contract.worker

            period_start = max(contract.date_start, month_start)
            period_end = min(contract.date_end or month_end, month_end)

            if period_start > period_end:
                continue

            workdays = self._workdays_between(period_start, period_end, holidays)

            planned_hours = Decimal(workdays) * HOURS_PER_DAY

            absence_dates = set(
                Absence.objects
                .filter(
                    worker=worker,
                    absence_type__in=ABSENCE_TYPES_OUT_OF_WORK,
                    absence_date__gte=period_start,
                    absence_date__lte=period_end,
                )
                .values_list("absence_date", flat=True)
            )

            extra_hours_by_date = {
                e.extras_date: e
                for e in ExtraHour.objects.filter(
                    worker=worker,
                    extras_date__gte=period_start,
                    extras_date__lte=period_end,
                )
            }

            actual_hours = Decimal("0.00")
            effective_hours = Decimal("0.00")
            break_hours = Decimal("0.00")

            absence_days = 0
            worked_days = 0
            full_days = 0
            short_days = 0
            overtime_hours = Decimal("0.00")

            day = period_start
            while day <= period_end:
                if not self._is_workday(day, holidays):
                    day += datetime.timedelta(days=1)
                    continue

                if day in absence_dates:
                    absence_days += 1
                    day += datetime.timedelta(days=1)
                    continue

                extra = extra_hours_by_date.get(day)

                if extra:
                    quantity = Decimal(str(extra.quantity))

                    if extra.full_day:
                        day_actual_hours = HOURS_PER_DAY + quantity
                        overtime_hours += quantity
                        full_days += 1
                    else:
                        day_actual_hours = quantity
                        short_days += 1
                else:
                    day_actual_hours = HOURS_PER_DAY
                    full_days += 1

                actual_hours += day_actual_hours

                if day_actual_hours > 0:
                    worked_days += 1
                    day_break = min(BREAK_HOURS, day_actual_hours)
                    break_hours += day_break
                    effective_hours += max(day_actual_hours - day_break, Decimal("0.00"))

                day += datetime.timedelta(days=1)

            unavailable_hours = planned_hours - actual_hours
            if unavailable_hours < 0:
                unavailable_hours = Decimal("0.00")

            avg_actual_hours_per_workday = (
                actual_hours / Decimal(workdays)
                if workdays else Decimal("0.00")
            )

            avg_effective_hours_per_workday = (
                effective_hours / Decimal(workdays)
                if workdays else Decimal("0.00")
            )

            avg_effective_hours_per_worked_day = (
                effective_hours / Decimal(worked_days)
                if worked_days else Decimal("0.00")
            )

            rows.append({
                "worker": worker,
                "contract": contract,
                "period_start": period_start,
                "period_end": period_end,

                "workdays": workdays,
                "planned_hours": self._round(planned_hours),

                "absence_days": absence_days,
                "worked_days": worked_days,
                "full_days": full_days,
                "short_days": short_days,

                "actual_hours": self._round(actual_hours),
                "overtime_hours": self._round(overtime_hours),
                "break_hours": self._round(break_hours),
                "effective_hours": self._round(effective_hours),
                "unavailable_hours": self._round(unavailable_hours),

                "avg_actual_hours_per_workday": self._round(avg_actual_hours_per_workday),
                "avg_effective_hours_per_workday": self._round(avg_effective_hours_per_workday),
                "avg_effective_hours_per_worked_day": self._round(avg_effective_hours_per_worked_day),
            })

        totals = self._totals(rows)

        context = {
            "rows": rows,
            "totals": totals,

            "year": year,
            "month": month,
            "month_start": month_start,
            "month_end": month_end,

            "previous_year": previous_month_date.year,
            "previous_month": previous_month_date.month,
            "next_year": next_month_date.year,
            "next_month": next_month_date.month,

            "hours_per_day": HOURS_PER_DAY,
            "break_minutes": 35,
        }

        return render(request, self.template_name, context)

    @staticmethod
    def _safe_int(value, default):
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _is_workday(day, holidays):
        return day.weekday() < 5 and day not in holidays

    @classmethod
    def _workdays_between(cls, start, end, holidays):
        result = 0
        current = start

        while current <= end:
            if cls._is_workday(current, holidays):
                result += 1
            current += datetime.timedelta(days=1)

        return result

    @staticmethod
    def _round(value):
        return Decimal(value).quantize(Decimal("0.01"))

    @classmethod
    def _totals(cls, rows):
        totals = defaultdict(Decimal)

        decimal_keys = [
            "planned_hours",
            "actual_hours",
            "overtime_hours",
            "break_hours",
            "effective_hours",
            "unavailable_hours",
        ]

        int_keys = [
            "workdays",
            "absence_days",
            "worked_days",
            "full_days",
            "short_days",
        ]

        for row in rows:
            for key in decimal_keys:
                totals[key] += Decimal(str(row[key]))

            for key in int_keys:
                totals[key] += Decimal(row[key])

        totals["workdays"] = int(totals["workdays"])
        totals["absence_days"] = int(totals["absence_days"])
        totals["worked_days"] = int(totals["worked_days"])
        totals["full_days"] = int(totals["full_days"])
        totals["short_days"] = int(totals["short_days"])

        if totals["workdays"]:
            totals["avg_actual_hours_per_workday"] = cls._round(
                totals["actual_hours"] / Decimal(totals["workdays"])
            )
            totals["avg_effective_hours_per_workday"] = cls._round(
                totals["effective_hours"] / Decimal(totals["workdays"])
            )
        else:
            totals["avg_actual_hours_per_workday"] = Decimal("0.00")
            totals["avg_effective_hours_per_workday"] = Decimal("0.00")

        if totals["worked_days"]:
            totals["avg_effective_hours_per_worked_day"] = cls._round(
                totals["effective_hours"] / Decimal(totals["worked_days"])
            )
        else:
            totals["avg_effective_hours_per_worked_day"] = Decimal("0.00")

        for key in decimal_keys:
            totals[key] = cls._round(totals[key])

        return dict(totals)