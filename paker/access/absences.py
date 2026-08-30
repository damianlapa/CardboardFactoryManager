from paker.access.common import (
    is_boss,
    is_office_worker,
    is_production_worker,
    is_warehouse_worker
)


def can_manage_absences(user):
    return is_boss(user)
