from paker.access.common import (
    is_boss,
    is_office_worker,
    is_production_worker,
    is_warehouse_worker,
)


def get_dashboard_role(user):
    if is_boss(user):
        return "boss"

    if is_office_worker(user):
        return "office"

    if is_production_worker(user):
        return "production"

    if is_warehouse_worker(user):
        return "warehouse"

    return "default"


def can_view_company_overview(user):
    return (
        is_boss(user)
        or is_office_worker(user)
    )


def can_view_production_dashboard(user):
    return (
        is_boss(user)
        or is_office_worker(user)
        or is_production_worker(user)
    )


def can_view_delivery_dashboard(user):
    return (
        is_boss(user)
        or is_office_worker(user)
    )


def can_view_company_absences(user):
    return (
        is_boss(user)
        or is_office_worker(user)
    )


def can_view_inventory_dashboard(user):
    return (
        is_boss(user)
        or is_office_worker(user)
        or is_warehouse_worker(user)
    )


def can_view_financial_dashboard(user):
    return is_boss(user)


def can_view_personal_dashboard(user):
    return user.is_authenticated


def get_dashboard_access(user):
    return {
        "company_overview":
            can_view_company_overview(user),

        "production":
            can_view_production_dashboard(user),

        "deliveries":
            can_view_delivery_dashboard(user),

        "absences":
            can_view_company_absences(user),

        "inventory":
            can_view_inventory_dashboard(user),

        "financial":
            can_view_financial_dashboard(user),

        "personal":
            can_view_personal_dashboard(user),
    }