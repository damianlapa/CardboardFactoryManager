from datetime import datetime, timedelta
from django.utils import timezone
from production.models import (
    WeeklyPlan, ProductionUnit, ProductionTask,
    WorkStation
)

from warehousemanager.models import Person, WorkStationQualification

def get_week_start_date(year, week):
    return datetime.strptime(f'{year}-W{int(week)}-1', "%Y-W%W-%w")

def is_person_available(person, start, end):
    return not person.tasks.filter(
        start__lt=end,
        end__gt=start
    ).exists()

def generate_provisional_plan(year, week):
    plan, _ = WeeklyPlan.objects.get_or_create(year=year, week=week)

    units = ProductionUnit.objects.filter(status='NOT STARTED')
    stations = list(WorkStation.objects.all())

    current_time_by_station = {
        station.id: get_week_start_date(year, week).replace(hour=6, minute=0)
        for station in stations
    }

    for unit in units:
        station = unit.work_station
        if not station:
            continue

        est_minutes = unit.estimated_time or 60
        start_time = current_time_by_station[station.id]
        end_time = start_time + timedelta(minutes=est_minutes)

        # Operatorzy
        operator_candidates = Person.objects.filter(
            workstationqualification__workstation=station
        ).distinct()

        available_operators = [
            p for p in operator_candidates
            if is_person_available(p, start_time, end_time)
        ]
        selected_operators = available_operators[:unit.required_operators]

        # Pomocnicy – dowolni dostępni
        all_helpers = Person.objects.exclude(id__in=[p.id for p in selected_operators])
        available_helpers = [
            p for p in all_helpers
            if is_person_available(p, start_time, end_time)
        ]
        selected_helpers = available_helpers[:unit.required_helpers]

        if len(selected_operators) < unit.required_operators or len(selected_helpers) < unit.required_helpers:
            continue

        task = ProductionTask.objects.create(
            plan=plan,
            production_unit=unit,
            work_station=station,
            start=start_time,
            end=end_time,
            is_temporary=True,
        )
        task.persons.set(selected_operators + selected_helpers)

        current_time_by_station[station.id] = end_time