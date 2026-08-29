from paker.access.common import (
    is_boss,
    is_office_worker,
    is_production_worker,
    is_warehouse_worker,
)


def can_view_dashboard(user):
    return user.is_authenticated


def can_view_production_menu(user):
    return (
        is_boss(user)
        or is_office_worker(user)
        or is_production_worker(user)
    )


def can_view_warehouse_menu(user):
    return (
        is_boss(user)
        or is_office_worker(user)
        or is_warehouse_worker(user)
    )


def can_view_employees_menu(user):
    return (
        is_boss(user)
        or is_office_worker(user)
        or is_warehouse_worker(user)
        or is_production_worker(user)
    )


def can_view_reports_menu(user):
    return (
        is_boss(user)
        or is_office_worker(user)
    )


def can_view_financial_menu(user):
    return is_boss(user)


def can_view_my_profile_menu(user):
    return user.is_authenticated


def can_view_absences_menu(user):
    return (
        is_boss(user)
        or is_office_worker(user)
        or is_warehouse_worker(user)
        or is_production_worker(user)
    )


def can_view_polymers_menu(user):
    return (
        is_boss(user)
        or is_office_worker(user)
    )


def can_view_punches_menu(user):
    return (
        is_boss(user)
        or is_office_worker(user)
    )


def can_view_deliveries_menu(user):
    return (
        is_boss(user)
        or is_office_worker(user)
    )


def get_sidebar_access(user):
    return {
        "dashboard": can_view_dashboard(user),
        "production": can_view_production_menu(user),
        "warehouse": can_view_warehouse_menu(user),
        "employees": can_view_employees_menu(user),
        "reports": can_view_reports_menu(user),
        "financial": can_view_financial_menu(user),
        "my_profile": can_view_my_profile_menu(user),
        "absences": can_view_absences_menu(user),
        "polymers": can_view_polymers_menu(user),
        "punches": can_view_punches_menu(user),
        "deliveries": can_view_deliveries_menu(user)
    }