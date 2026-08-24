import datetime

from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404

from paker.access.employees import (
    can_edit_employee,
    can_view_absences,
    can_view_contracts,
    can_view_employee,
    can_view_employment_data,
    can_view_salary,
    can_view_vacations,
    can_view_work_time,
)
from warehousemanager.models import (
    Contract,
    Person,
)


def get_employee_list(*, include_inactive=False):
    today = datetime.date.today()

    employees = Person.objects.all()

    if not include_inactive:
        employees = employees.filter(
            job_end__isnull=True,
        )

    employees = employees.order_by(
        "last_name",
        "first_name",
    )

    rows = []

    for employee in employees:
        employment_end = (
            employee.job_end
            or today
        )

        if employee.job_start:
            employment_days = max(
                (employment_end - employee.job_start).days,
                0,
            )
        else:
            employment_days = 0

        years = employment_days // 365
        months = (
            employment_days % 365
        ) // 30

        if years:
            seniority_label = (
                f"{years} lat {months} mies."
            )
        else:
            seniority_label = (
                f"{months} mies."
            )

        medical_expired = (
            not employee.medical_examination
            or employee.medical_examination < today
        )

        rows.append({
            "employee": employee,
            "seniority_days": employment_days,
            "seniority_label": seniority_label,
            "is_active": employee.job_end is None,
            "medical_expired": medical_expired,
        })

    return rows


def get_employee_details(
    *,
    user,
    employee_id,
):
    employee = get_object_or_404(
        Person,
        id=employee_id,
    )

    if not can_view_employee(
        user,
        employee,
    ):
        raise PermissionDenied

    access = {
        "can_edit": can_edit_employee(user),

        "can_view_employment_data":
            can_view_employment_data(
                user,
                employee,
            ),

        "can_view_contracts":
            can_view_contracts(user),

        "can_view_salary":
            can_view_salary(user),

        "can_view_absences":
            can_view_absences(
                user,
                employee,
            ),

        "can_view_vacations":
            can_view_vacations(
                user,
                employee,
            ),

        "can_view_work_time":
            can_view_work_time(
                user,
                employee,
            ),
    }

    contracts = []

    if access["can_view_contracts"]:
        contracts = (
            Contract.objects
            .filter(worker=employee)
            .order_by("-date_start")
        )

    return {
        "employee": employee,
        "contracts": contracts,
        "access": access,
    }