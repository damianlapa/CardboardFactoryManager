import datetime
from dataclasses import dataclass

from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404

from warehousemanager.models import Absence, Person


VACATION_TYPES = ("UW", "UŻ")


@dataclass(frozen=True)
class VacationBalance:
    worker: Person
    annual_entitlement: int
    carried_over: int

    used_regular: int
    used_on_demand: int
    used_total: int

    available_total: int
    remaining: int


def resolve_vacation_year(value):
    current_year = datetime.date.today().year

    try:
        year = int(value)
    except (TypeError, ValueError):
        return current_year

    if year < 2000 or year > current_year + 5:
        return current_year

    return year


def get_available_vacation_years():
    current_year = datetime.date.today().year

    return list(
        range(
            2020,
            current_year + 2,
        )
    )


def get_visible_workers(user):
    if user.is_superuser:
        return (
            Person.objects
            .filter(job_end__isnull=True)
            .order_by(
                "last_name",
                "first_name",
            )
        )

    worker = (
        Person.objects
        .filter(user=user)
        .first()
    )

    if not worker:
        return Person.objects.none()

    return Person.objects.filter(id=worker.id)


def get_worker_vacation_balance(worker, year):
    annual_entitlement = (
        worker.worker_vacation_in_year(year) or 0
    )

    vacation_summary = (
        worker.worker_vacations(year) or {}
    )

    used_regular = (
        vacation_summary.get("UW", 0) or 0
    )

    used_on_demand = (
        vacation_summary.get("UŻ", 0) or 0
    )

    used_total = (
        used_regular
        + used_on_demand
    )

    carried_over = (
        worker.vacation_left(year) or 0
    )

    available_total = (
        annual_entitlement
        + carried_over
    )

    remaining = (
        available_total
        - used_total
    )

    return VacationBalance(
        worker=worker,

        annual_entitlement=annual_entitlement,
        carried_over=carried_over,

        used_regular=used_regular,
        used_on_demand=used_on_demand,
        used_total=used_total,

        available_total=available_total,
        remaining=remaining,
    )


def get_vacation_balances(
    *,
    user,
    year,
):
    workers = get_visible_workers(user)

    return [
        get_worker_vacation_balance(
            worker,
            year,
        )
        for worker in workers
    ]


def can_view_worker_vacations(
    *,
    user,
    worker,
):
    if user.is_superuser:
        return True

    return worker.user_id == user.id


def get_vacation_details(
    *,
    user,
    person_id,
    year,
):
    worker = get_object_or_404(
        Person,
        id=person_id,
    )

    if not can_view_worker_vacations(
        user=user,
        worker=worker,
    ):
        raise PermissionDenied

    balance = get_worker_vacation_balance(
        worker,
        year,
    )

    absences = (
        Absence.objects
        .filter(
            worker=worker,
            absence_date__year=year,
        )
        .order_by(
            "-absence_date",
            "-id",
        )
    )

    return {
        "worker": worker,
        "year": year,
        "balance": balance,
        "absences": absences,
    }