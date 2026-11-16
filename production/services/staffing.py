from collections import defaultdict

from django.db import transaction
from django.shortcuts import get_object_or_404

from production.models import (
    ProductionUnit,
)
from warehousemanager.models import Person, WorkStationQualification


class StaffingError(Exception):
    pass


# ============================================================
# WORKERS
# ============================================================


def get_staffing_workers():
    """
    Pracownicy dostępni na planszy obsady.

    Na razie nie ingerujemy w model ani logikę dostępności
    czasowej. Pokazujemy aktywnych pracowników produkcji.
    """

    return (
        Person.objects
        .filter(
            occupancy_type="PRODUCTION",
            job_end__isnull=True,
        )
        .order_by(
            "last_name",
            "first_name",
        )
    )


# ============================================================
# QUALIFICATIONS
# ============================================================


def get_worker_qualification_map():
    result = defaultdict(set)

    qualifications = (
        WorkStationQualification.objects
        .all()
        .values_list(
            "person_id",
            "workstation_id",
        )
    )

    for person_id, workstation_id in qualifications:
        result[person_id].add(
            workstation_id
        )

    return result


def worker_is_qualified(
    *,
    worker_id,
    workstation_id,
    qualification_map,
):
    if not workstation_id:
        return False

    return (
        workstation_id
        in qualification_map.get(
            worker_id,
            set(),
        )
    )


# ============================================================
# UNITS
# ============================================================


def get_staffing_units():
    """
    Jednostki, dla których można ustalać obsadę.

    Na etapie testowym:
    - pomijamy zakończone,
    - pokazujemy także PLANNED / NOT STARTED / IN PROGRESS.
    """

    return (
        ProductionUnit.objects
        .exclude(
            status="FINISHED"
        )
        .select_related(
            "production_order",
            "production_order__customer",
            "work_station",
        )
        .order_by(
            "work_station__name",
            "-production_order__priority",
            "production_order__id_number",
            "sequence",
        )
    )


# ============================================================
# STAFFING STATE
# ============================================================


def get_unit_staffing_state(
    *,
    unit,
    qualification_map,
):
    """
    Wylicza aktualną obsadę jednostki.

    Operator = osoba mająca kwalifikację
    do stanowiska jednostki.

    Pomocnik = osoba przypisana do jednostki,
    ale bez kwalifikacji do tego stanowiska.
    """

    persons = list(
        unit.persons
        .all()
        .order_by(
            "last_name",
            "first_name",
        )
    )

    qualified_persons = []
    helper_persons = []

    for person in persons:

        is_qualified = (
            unit.work_station.id
            in qualification_map.get(
                person.id,
                set(),
            )
        )

        if is_qualified:
            qualified_persons.append(
                person
            )
        else:
            helper_persons.append(
                person
            )


    required_operators = (
        unit.required_operators
        or 0
    )

    required_helpers = (
        unit.required_helpers
        or 0
    )

    operator_count = len(
        qualified_persons
    )

    helper_count = len(
        helper_persons
    )

    operators_complete = (
        operator_count
        >= required_operators
    )

    helpers_complete = (
        helper_count
        >= required_helpers
    )

    quantity = (
            unit.production_order.quantity
            or 0
    )

    estimated_time = (
            unit.estimated_time
            or 0
    )

    persons_count = len(
        persons
    )

    sheets_per_hour = None
    sheets_per_person_hour = None

    if (
            quantity
            and estimated_time
    ):
        sheets_per_hour = round(
            quantity
            * 60
            / estimated_time
        )

        if persons_count:
            sheets_per_person_hour = round(
                sheets_per_hour
                / persons_count
            )

    return {
        "persons":
            persons,

        "qualified_persons":
            qualified_persons,

        "helper_persons":
            helper_persons,

        "required_operators":
            required_operators,

        "required_helpers":
            required_helpers,

        "operator_count":
            operator_count,

        "helper_count":
            helper_count,

        "operators_complete":
            operators_complete,

        "helpers_complete":
            helpers_complete,

        "missing_operators":
            max(
                0,
                required_operators
                - operator_count,
            ),

        "missing_helpers":
            max(
                0,
                required_helpers
                - helper_count,
            ),

        "is_complete":
            (
                operators_complete
                and helpers_complete
            ),

        "persons_count":
            persons_count,

        "sheets_per_hour":
            sheets_per_hour,

        "sheets_per_person_hour":
            sheets_per_person_hour,
    }


# ============================================================
# ASSIGN
# ============================================================


@transaction.atomic
def assign_worker(
    *,
    unit_id,
    worker_id,
):
    unit = get_object_or_404(
        ProductionUnit.objects
        .select_for_update()
        .select_related(
            "work_station",
            "production_order",
        )
        .prefetch_related(
            "persons",
        ),
        pk=unit_id,
    )

    worker = get_object_or_404(
        Person,
        pk=worker_id,
    )


    if unit.status == "FINISHED":
        raise StaffingError(
            (
                "Nie można zmieniać obsady "
                "zakończonej operacji."
            )
        )


    if unit.persons.filter(
        pk=worker.id
    ).exists():

        raise StaffingError(
            (
                "Ten pracownik jest już "
                "przypisany do tej operacji."
            )
        )

    unit.persons.add(
        worker
    )

    if hasattr(
            unit,
            "_prefetched_objects_cache",
    ):
        unit._prefetched_objects_cache.pop(
            "persons",
            None,
        )

    return unit


# ============================================================
# UNASSIGN
# ============================================================


@transaction.atomic
def unassign_worker(
    *,
    unit_id,
    worker_id,
):
    unit = get_object_or_404(
        ProductionUnit.objects
        .select_for_update()
        .prefetch_related(
            "persons",
        ),
        pk=unit_id,
    )

    worker = get_object_or_404(
        Person,
        pk=worker_id,
    )


    if unit.status == "FINISHED":

        raise StaffingError(
            (
                "Nie można zmieniać obsady "
                "zakończonej operacji."
            )
        )


    if not unit.persons.filter(
        pk=worker.id
    ).exists():

        raise StaffingError(
            (
                "Ten pracownik nie jest "
                "przypisany do tej operacji."
            )
        )

    unit.persons.remove(
        worker
    )

    if hasattr(
            unit,
            "_prefetched_objects_cache",
    ):
        unit._prefetched_objects_cache.pop(
            "persons",
            None,
        )

    return unit


# ============================================================
# BOARD CONTEXT
# ============================================================


def get_staffing_context():
    workers = list(
        get_staffing_workers()
    )

    units = list(
        get_staffing_units()
    )

    qualification_map = (
        get_worker_qualification_map()
    )


    # --------------------------------------------------------
    # WORKER ROWS
    # --------------------------------------------------------

    worker_rows = []

    for worker in workers:

        worker_rows.append({
            "worker":
                worker,

            "qualification_ids":
                sorted(
                    qualification_map.get(
                        worker.id,
                        set(),
                    )
                ),
        })


    # --------------------------------------------------------
    # UNIT ROWS
    # --------------------------------------------------------

    unit_rows = []

    complete_count = 0
    incomplete_count = 0

    for unit in units:

        staffing = (
            get_unit_staffing_state(
                unit=unit,
                qualification_map=
                    qualification_map,
            )
        )

        if staffing["is_complete"]:
            complete_count += 1
        else:
            incomplete_count += 1


        unit_rows.append({
            "unit":
                unit,

            "staffing":
                staffing,
        })


    return {
        "workers":
            worker_rows,

        "units":
            unit_rows,

        "worker_count":
            len(worker_rows),

        "unit_count":
            len(unit_rows),

        "complete_count":
            complete_count,

        "incomplete_count":
            incomplete_count,
    }