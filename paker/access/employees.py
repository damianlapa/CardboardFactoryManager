from paker.access.common import (
    is_boss,
    is_office_worker,
    is_production_worker,
    is_warehouse_worker
)


def is_own_employee_profile(
    user,
    employee,
):
    if not user.is_authenticated:
        return False

    return employee.user_id == user.id


def can_view_employee_list(user):
    return (
        is_boss(user)
        or is_office_worker(user)
        or is_production_worker(user)
    )


def can_view_employee(
    user,
    employee,
):
    if is_boss(user):
        return True

    if is_office_worker(user):
        return True

    return is_own_employee_profile(
        user,
        employee,
    )


def can_edit_employee(user):
    return is_boss(user)


def can_view_employment_data(
    user,
    employee,
):
    return can_view_employee(
        user,
        employee,
    )


def can_view_contracts(user):
    return is_boss(user)


def can_view_salary(user):
    return is_boss(user)


def can_view_absences(
    user,
    employee,
):
    return can_view_employee(
        user,
        employee,
    )


def can_view_vacations(
    user,
    employee,
):
    return can_view_employee(
        user,
        employee,
    )


def can_view_work_time(
    user,
    employee,
):
    return can_view_employee(
        user,
        employee,
    )