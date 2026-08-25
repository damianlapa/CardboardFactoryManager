def user_in_group(user, group_name):
    if not user.is_authenticated:
        return False

    return user.groups.filter(
        name=group_name,
    ).exists()


def is_boss(user):
    return (
        user.is_superuser
        or user_in_group(user, "Bosses")
    )


def is_office_worker(user):
    return user_in_group(
        user,
        "OfficeWorkers",
    )


def is_production_worker(user):
    return user_in_group(
        user,
        "ProductionWorker",
    )


def is_warehouse_worker(user):
    return user_in_group(
        user,
        "WarehouseWorker",
    )


def get_home_url_name(user):
    if is_warehouse_worker(user):
        return "warehouse:warehouse-list-view"

    if is_production_worker(user):
        return "dashboard"

    if is_office_worker(user):
        return "dashboard"

    if is_boss(user):
        return "dashboard"

    return "dashboard"
