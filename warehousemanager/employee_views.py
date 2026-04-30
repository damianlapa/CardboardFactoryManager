# warehousemanager/employee_views.py

import datetime
from collections import defaultdict
from decimal import Decimal

from django.utils import timezone

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
from warehouse.models import MonthResults


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


class EmployeeWorkTimeBaseMixin:
    WORK_START = datetime.time(7, 0)
    WORK_END = datetime.time(15, 0)

    WORK_MINUTES_PER_DAY = 8 * 60
    BREAK_MINUTES_PER_DAY = 35
    GAP_TOLERANCE_MINUTES = 10

    FULL_DAY_ABSENCES = ["UW", "UB", "CH", "OP", "NN", "KW", "UO"]

    BREAKS = [
        (datetime.time(9, 0), datetime.time(9, 5)),
        (datetime.time(11, 0), datetime.time(11, 20)),
        (datetime.time(12, 30), datetime.time(12, 35)),
        (datetime.time(14, 0), datetime.time(14, 5)),
    ]

    def _work_windows_for_day(self, day):
        windows = []

        current_start = self.WORK_START

        # piątek = 4
        work_end = datetime.time(14, 0) if day.weekday() == 4 else self.WORK_END

        for break_start, break_end in self.BREAKS:
            # jeżeli przerwa zaczyna się po końcu dnia, pomijamy ją
            if break_start >= work_end:
                break

            if current_start < break_start:
                windows.append((
                    self._aware_combine(day, current_start),
                    self._aware_combine(day, min(break_start, work_end)),
                ))

            current_start = break_end

            if current_start >= work_end:
                break

        if current_start < work_end:
            windows.append((
                self._aware_combine(day, current_start),
                self._aware_combine(day, work_end),
            ))

        return windows

    def _expected_production_minutes_for_day(self, day):
        total = 0

        for start, end in self._work_windows_for_day(day):
            total += int((end - start).total_seconds() / 60)

        return total

    def _safe_parse_date(self, value, default):
        if not value:
            return default
        parsed = parse_date(value)
        return parsed or default

    def _default_range(self):
        today = datetime.date.today()
        return today.replace(day=1), today

    def _date_range(self, start, end):
        day = start
        while day <= end:
            yield day
            day += datetime.timedelta(days=1)

    def _aware_combine(self, day, time_value):
        dt = datetime.datetime.combine(day, time_value)
        tz = timezone.get_current_timezone()

        if timezone.is_naive(dt):
            return timezone.make_aware(dt, tz)

        return timezone.localtime(dt, tz)

    def _to_current_timezone(self, dt):
        if not dt:
            return dt

        tz = timezone.get_current_timezone()

        if timezone.is_naive(dt):
            return timezone.make_aware(dt, tz)

        return timezone.localtime(dt, tz)

    def _expected_day_for_person(self, person, day):
        if day.weekday() >= 5:
            return {
                "should_work": False,
                "expected_minutes": 0,
                "absence": None,
                "extra": None,
                "start": None,
                "end": None,
                "reason": "weekend",
            }

        if person.job_start and day < person.job_start:
            return {
                "should_work": False,
                "expected_minutes": 0,
                "absence": None,
                "extra": None,
                "start": None,
                "end": None,
                "reason": "before_job_start",
            }

        if person.job_end and day > person.job_end:
            return {
                "should_work": False,
                "expected_minutes": 0,
                "absence": None,
                "extra": None,
                "start": None,
                "end": None,
                "reason": "after_job_end",
            }

        holiday = Holiday.objects.filter(holiday_date=day).first()
        if holiday:
            return {
                "should_work": False,
                "expected_minutes": 0,
                "absence": None,
                "extra": None,
                "start": None,
                "end": None,
                "reason": "holiday",
            }

        absence = Absence.objects.filter(worker=person, absence_date=day).first()

        if absence and absence.absence_type in self.FULL_DAY_ABSENCES:
            return {
                "should_work": False,
                "expected_minutes": 0,
                "absence": absence,
                "extra": None,
                "start": None,
                "end": None,
                "reason": "absence",
            }

        extra = ExtraHour.objects.filter(worker=person, extras_date=day).first()

        expected_start = self._aware_combine(day, self.WORK_START)
        expected_end = self._aware_combine(day, self.WORK_END)
        expected_minutes = self._expected_production_minutes_for_day(day)

        if extra:
            extra_minutes = int(Decimal(extra.quantity) * Decimal("60"))

            if extra.full_day:
                expected_minutes = self._expected_production_minutes_for_day(day) + extra_minutes
                expected_end = expected_end + datetime.timedelta(minutes=extra_minutes)
            else:
                expected_minutes = extra_minutes
                expected_end = expected_start + datetime.timedelta(minutes=extra_minutes)

        return {
            "should_work": True,
            "expected_minutes": expected_minutes,
            "absence": absence,
            "extra": extra,
            "start": expected_start,
            "end": expected_end,
            "reason": "workday",
        }

    def _split_unit_by_day(self, unit, person=None):
        result = []

        start = self._to_current_timezone(unit.start)
        end = self._to_current_timezone(unit.end)

        if not start or not end or end <= start:
            return result

        current_day = start.date()
        last_day = end.date()

        while current_day <= last_day:

            # 🔴 sprawdzamy czy pracownik powinien pracować tego dnia
            if person:
                expected = self._expected_day_for_person(person, current_day)
                if not expected["should_work"]:
                    current_day += datetime.timedelta(days=1)
                    continue
            else:
                if current_day.weekday() >= 5:
                    current_day += datetime.timedelta(days=1)
                    continue

            # 🔥 NAJWAŻNIEJSZE — używamy okien pracy
            work_windows = self._work_windows_for_day(current_day)

            for window_start, window_end in work_windows:
                part_start = max(start, window_start)
                part_end = min(end, window_end)

                if part_end > part_start:
                    result.append({
                        "day": current_day,
                        "unit": unit,
                        "start": part_start,
                        "end": part_end,
                        "minutes": int((part_end - part_start).total_seconds() / 60),
                        "persons_count": unit.persons.count(),
                    })

            current_day += datetime.timedelta(days=1)

        return result

    def _analyze_intervals(self, intervals, expected_start, expected_end):
        intervals = sorted(intervals, key=lambda x: x["start"])

        total_minutes = 0
        union_minutes = 0
        overlaps = []
        gaps = []
        outside = []

        previous_end = None

        for interval in intervals:
            start = interval["start"]
            end = interval["end"]
            minutes = int((end - start).total_seconds() / 60)

            total_minutes += minutes

            if expected_start and expected_end:
                if start < expected_start or end > expected_end:
                    outside.append(interval)

            if previous_end and start < previous_end:
                overlap_end = min(end, previous_end)
                overlap_minutes = int((overlap_end - start).total_seconds() / 60)

                if overlap_minutes > 0:
                    overlaps.append({
                        "interval": interval,
                        "minutes": overlap_minutes,
                    })

                if end > previous_end:
                    union_minutes += int((end - previous_end).total_seconds() / 60)
                    previous_end = end
            else:
                union_minutes += minutes
                previous_end = end

        if expected_start and expected_end:
            work_windows = self._work_windows_for_day(expected_start.date())

            for window_start, window_end in work_windows:
                pointer = window_start

                for interval in intervals:
                    start = max(interval["start"], window_start)
                    end = min(interval["end"], window_end)

                    if end <= window_start or start >= window_end:
                        continue

                    gap_minutes = int((start - pointer).total_seconds() / 60)

                    if gap_minutes > self.GAP_TOLERANCE_MINUTES:
                        gaps.append({
                            "start": pointer,
                            "end": start,
                            "minutes": gap_minutes,
                        })

                    if end > pointer:
                        pointer = end

                final_gap = int((window_end - pointer).total_seconds() / 60)

                if final_gap > self.GAP_TOLERANCE_MINUTES:
                    gaps.append({
                        "start": pointer,
                        "end": window_end,
                        "minutes": final_gap,
                    })

        return {
            "total_minutes": total_minutes,
            "union_minutes": union_minutes,
            "overlaps": overlaps,
            "gaps": gaps,
            "outside": outside,
        }

    def _audit_person_days(self, person, start, end):
        units = (
            ProductionUnit.objects
            .filter(
                persons=person,
                start__date__lte=end,
                end__date__gte=start,
            )
            .exclude(start__isnull=True)
            .exclude(end__isnull=True)
            .select_related("production_order", "work_station")
            .prefetch_related("persons")
            .order_by("start", "end")
        )

        units_by_day = defaultdict(list)

        for unit in units:
            for part in self._split_unit_by_day(unit, person=person):
                if start <= part["day"] <= end:
                    units_by_day[part["day"]].append(part)

        days = []

        totals = {
            "total_minutes": 0,
            "union_minutes": 0,
            "gaps": 0,
            "overlaps": 0,
            "outside": 0,
            "problem_days": 0,
        }

        for day in self._date_range(start, end):
            expected = self._expected_day_for_person(person, day)
            intervals = units_by_day.get(day, [])

            analysis = self._analyze_intervals(
                intervals=intervals,
                expected_start=expected["start"],
                expected_end=expected["end"],
            )

            problems = []

            if not expected["should_work"] and intervals:
                problems.append("Praca w dzień wolny / nieobecność")

            if expected["should_work"] and not intervals:
                problems.append("Brak ewidencji ProductionUnit")

            if analysis["gaps"]:
                problems.append("Dziury w ewidencji")

            if analysis["overlaps"]:
                problems.append("Nakładania ProductionUnit")

            if analysis["outside"]:
                problems.append("Praca poza oczekiwanym zakresem")

            if expected["expected_minutes"] and analysis["union_minutes"] > expected["expected_minutes"]:
                problems.append("PU przekracza dostępny czas pracy")

            totals["total_minutes"] += analysis["total_minutes"]
            totals["union_minutes"] += analysis["union_minutes"]
            totals["gaps"] += len(analysis["gaps"])
            totals["overlaps"] += len(analysis["overlaps"])
            totals["outside"] += len(analysis["outside"])

            if problems:
                totals["problem_days"] += 1

            days.append({
                "day": day,
                "expected": expected,
                "intervals": intervals,
                "analysis": analysis,
                "problems": problems,
            })

        return days, totals

    def _person_available_minutes(self, person, start, end):
        workdays = 0
        physical_minutes = 0
        absence_days = 0
        partial_days = 0

        for day in self._date_range(start, end):
            expected = self._expected_day_for_person(person, day)

            if expected["reason"] in ["weekend", "holiday", "before_job_start", "after_job_end"]:
                continue

            workdays += 1

            if expected["reason"] == "absence":
                absence_days += 1
                continue

            if expected["extra"] and not expected["extra"].full_day:
                partial_days += 1

            physical_minutes += expected["expected_minutes"]

        break_minutes = max(workdays - absence_days, 0) * self.BREAK_MINUTES_PER_DAY
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

    def _percent(self, value, total):
        if not total:
            return 0
        return round((value / total) * 100, 1)

    def _month_cost_summary(self, start, workers, net_minutes, production_minutes):
        month = start.month
        year = start.year

        salary_date = datetime.datetime.combine(start, datetime.time(12, 0))

        production_salary_sum = Decimal("0.00")

        for person in workers:
            if person.occupancy_type != "PRODUCTION":
                continue

            salary = person.contract(date=salary_date) or 0
            production_salary_sum += Decimal(salary)

        month_result = MonthResults.objects.filter(
            month=month,
            year=year,
        ).first()

        financial = Decimal("0.00")
        management = Decimal("0.00")
        logistic = Decimal("0.00")
        other = Decimal("0.00")

        if month_result:
            financial = Decimal(month_result.financial_expenses or 0)
            management = Decimal(month_result.management_expenses or 0)
            logistic = Decimal(month_result.logistic_expenses or 0)
            other = Decimal(month_result.other_expenses or 0)

        indirect_costs = financial + management + logistic + other
        total_costs = production_salary_sum + indirect_costs

        net_hours = Decimal(net_minutes) / Decimal("60") if net_minutes else Decimal("0")
        production_hours = Decimal(production_minutes) / Decimal("60") if production_minutes else Decimal("0")

        pure_production_rate = Decimal("0.00")
        break_even_rate = Decimal("0.00")
        break_even_rate_by_pu = Decimal("0.00")

        if net_hours:
            pure_production_rate = production_salary_sum / net_hours
            break_even_rate = total_costs / net_hours

        if production_hours:
            break_even_rate_by_pu = total_costs / production_hours

        return {
            "month": month,
            "year": year,
            "month_result_exists": bool(month_result),

            "production_salary_sum": round(production_salary_sum, 2),
            "financial": round(financial, 2),
            "management": round(management, 2),
            "logistic": round(logistic, 2),
            "other": round(other, 2),
            "indirect_costs": round(indirect_costs, 2),
            "total_costs": round(total_costs, 2),

            "net_hours": round(net_hours, 2),
            "production_hours": round(production_hours, 2),

            "pure_production_rate": round(pure_production_rate, 2),
            "break_even_rate": round(break_even_rate, 2),
            "break_even_rate_by_pu": round(break_even_rate_by_pu, 2),
        }


class EmployeeWorkTimeReportView(EmployeeWorkTimeBaseMixin, View):
    template_name = "whm/employees/employee_work_time_report.html"

    def get(self, request):
        default_start, default_end = self._default_range()

        start = self._safe_parse_date(request.GET.get("start"), default_start)
        end = self._safe_parse_date(request.GET.get("end"), default_end)

        if end < start:
            start, end = end, start

        show_all = request.GET.get("all") == "1"

        workers = (
            Person.objects
            .filter(job_start__lte=end)
            .filter(models.Q(job_end__isnull=True) | models.Q(job_end__gte=start))
            .order_by("last_name", "first_name")
        )

        if not show_all:
            workers = workers.filter(occupancy_type="PRODUCTION")

        workers = list(workers)

        rows = []

        totals = {
            "base_minutes": 0,
            "physical_minutes": 0,
            "net_minutes": 0,
            "production_minutes": 0,
            "production_union_minutes": 0,
            "problem_days": 0,
            "overlaps": 0,
            "gaps": 0,
            "outside": 0,
        }

        for person in workers:
            availability = self._person_available_minutes(person, start, end)
            audit_days, audit_totals = self._audit_person_days(person, start, end)

            production_minutes = audit_totals["total_minutes"]
            production_union_minutes = audit_totals["union_minutes"]

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
                "production_union_minutes": production_union_minutes,

                "production_vs_physical_percent": self._percent(
                    production_minutes,
                    availability["physical_minutes"],
                ),
                "production_vs_net_percent": self._percent(
                    production_minutes,
                    availability["net_minutes"],
                ),

                "problem_days": audit_totals["problem_days"],
                "overlaps_count": audit_totals["overlaps"],
                "gaps_count": audit_totals["gaps"],
                "outside_count": audit_totals["outside"],
            }

            rows.append(row)

            totals["base_minutes"] += availability["base_minutes"]
            totals["physical_minutes"] += availability["physical_minutes"]
            totals["net_minutes"] += availability["net_minutes"]
            totals["production_minutes"] += production_minutes
            totals["production_union_minutes"] += production_union_minutes
            totals["problem_days"] += audit_totals["problem_days"]
            totals["overlaps"] += audit_totals["overlaps"]
            totals["gaps"] += audit_totals["gaps"]
            totals["outside"] += audit_totals["outside"]

        totals["physical_percent"] = self._percent(
            totals["physical_minutes"],
            totals["base_minutes"],
        )
        totals["net_percent"] = self._percent(
            totals["net_minutes"],
            totals["base_minutes"],
        )
        totals["production_vs_physical_percent"] = self._percent(
            totals["production_minutes"],
            totals["physical_minutes"],
        )
        totals["production_vs_net_percent"] = self._percent(
            totals["production_minutes"],
            totals["net_minutes"],
        )

        cost_summary = self._month_cost_summary(
            start=start,
            workers=workers,
            net_minutes=totals["net_minutes"],
            production_minutes=totals["production_minutes"],
        )

        return render(request, self.template_name, {
            "start": start,
            "end": end,
            "rows": rows,
            "totals": totals,
            "show_all": show_all,
            "cost_summary": cost_summary,
        })


class EmployeeProductionUnitsAjaxView(EmployeeWorkTimeBaseMixin, View):
    template_name = "whm/employees/_employee_production_units.html"

    def get(self, request, person_id):
        person = get_object_or_404(Person, id=person_id)

        default_start, default_end = self._default_range()

        start = self._safe_parse_date(request.GET.get("start"), default_start)
        end = self._safe_parse_date(request.GET.get("end"), default_end)

        if end < start:
            start, end = end, start

        days, totals = self._audit_person_days(person, start, end)

        html = render(request, self.template_name, {
            "person": person,
            "start": start,
            "end": end,
            "days": days,
            "totals": totals,
            "total_hours": round(totals["total_minutes"] / 60, 2),
            "union_hours": round(totals["union_minutes"] / 60, 2),
        }).content.decode("utf-8")

        return JsonResponse({
            "html": html,
            "total_minutes": totals["total_minutes"],
            "union_minutes": totals["union_minutes"],
        })