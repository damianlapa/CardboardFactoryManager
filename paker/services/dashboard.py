# paker/services/dashboard.py

from datetime import date

from paker.access.dashboard import (
    get_dashboard_access,
    get_dashboard_role,
)

from warehousemanager.models import (
    Absence,
    ExtraHour,
    Person,
)

from deliveries.models import Event


POLISH_WEEKDAYS = {
    0: "Poniedziałek",
    1: "Wtorek",
    2: "Środa",
    3: "Czwartek",
    4: "Piątek",
    5: "Sobota",
    6: "Niedziela",
}

ABSENCE_LABELS = {
    "UW": "Urlop wypoczynkowy",
    "UŻ": "Urlop na żądanie",
    "UB": "Urlop bezpłatny",
    "UO": "Urlop okolicznościowy",
    "CH": "Choroba",
    "OP": "Opieka",
    "NN": "Nieobecność nieusprawiedliwiona",
    "KW": "Kwarantanna",
    "IZ": "Izolacja",
    "D": "Delegacja",
    "SP": "Spóźnienie",
    "IN": "Inna nieobecność",
}


def get_personal_dashboard_data(user):
    employee = (
        Person.objects
        .filter(user=user)
        .first()
    )

    if not employee:
        return {
            "employee": None,
            "today_absence": None,
            "extra_hours_year": 0,
        }

    today = date.today()

    today_absence = (
        Absence.objects
        .filter(
            worker=employee,
            absence_date=today,
        )
        .first()
    )

    extra_hours_year = sum(
        (
            item.quantity
            for item in ExtraHour.objects.filter(
                worker=employee,
                extras_date__year=today.year,
            )
        ),
        0,
    )

    return {
        "employee": employee,
        "today_absence": today_absence,
        "extra_hours_year":
            extra_hours_year,
    }


def get_dashboard_context(*, user):
    today = date.today()

    access = get_dashboard_access(user)

    context = {
        "today": today,
        "weekday_name": POLISH_WEEKDAYS[
            today.weekday()
        ],
        "dashboard_role": get_dashboard_role(user),
        "access": access,
    }

    if access["company_overview"]:
        context["company_overview"] = (
            get_company_overview()
        )

    if access["production"]:
        context["production"] = (
            get_production_dashboard_data()
        )

    if access["deliveries"]:
        context["deliveries"] = (
            get_delivery_dashboard_data()
        )

    if access["absences"]:
        context["absences"] = (
            get_absence_dashboard_data()
        )

    if access["inventory"]:
        context["inventory"] = (
            get_inventory_dashboard_data()
        )

    if access["financial"]:
        context["financial"] = (
            get_financial_dashboard_data()
        )

    if access["personal"]:
        context["personal"] = (
            get_personal_dashboard_data(user)
        )

    return context


def get_company_overview():
    return {}


def get_production_dashboard_data():
    return {}


def get_delivery_dashboard_data():
    today = date.today()

    delivery_types = [
        "PLANOWANA DOSTAWA",
        "ZREALIZOWANA DOSTAWA",
        "SPEDYCJA",
        "ODBIÓR OSOBISTY",
    ]

    events = (
        Event.objects
        .filter(
            day=today,
            event_type__in=delivery_types,
        )
        .order_by(
            "event_type",
            "title",
        )
    )

    rows = []

    for event in events:
        rows.append({
            "event": event,
            "type": event.event_type,
            "title": event.title,
            "details": event.details,
            "is_completed":
                event.event_type == "ZREALIZOWANA DOSTAWA",
        })

    return {
        "count": len(rows),

        "planned_count": sum(
            1
            for row in rows
            if row["type"] == "PLANOWANA DOSTAWA"
        ),

        "completed_count": sum(
            1
            for row in rows
            if row["is_completed"]
        ),

        "shipping_count": sum(
            1
            for row in rows
            if row["type"] == "SPEDYCJA"
        ),

        "pickup_count": sum(
            1
            for row in rows
            if row["type"] == "ODBIÓR OSOBISTY"
        ),

        "rows": rows,
    }


def get_absence_dashboard_data():
    ABSENCE_CSS_KEYS = {
        "UW": "uw",
        "UŻ": "uz",
        "UB": "ub",
        "UO": "uo",
        "CH": "ch",
        "OP": "op",
        "NN": "nn",
        "KW": "kw",
        "IZ": "iz",
        "D": "delegation",
        "SP": "late",
        "IN": "other",
    }
    today = date.today()

    absences = (
        Absence.objects
        .filter(absence_date=today)
        .select_related("worker")
        .order_by(
            "worker__last_name",
            "worker__first_name",
        )
    )

    rows = []

    for absence in absences:
        rows.append({
            "worker": absence.worker,
            "type": absence.absence_type,
            "css_key": ABSENCE_CSS_KEYS.get(
                absence.absence_type,
                "other",
            ),
            "label": ABSENCE_LABELS.get(
                absence.absence_type,
                absence.absence_type,
            ),
            "value": absence.value,
            "additional_info":
                absence.additional_info,
        })

    return {
        "count": len(rows),
        "rows": rows,
    }


def get_inventory_dashboard_data():
    return {}


def get_financial_dashboard_data():
    return {}


def get_personal_dashboard_data(user):
    return {}