import calendar
import datetime

from django.shortcuts import get_object_or_404

from deliveries.models import (
    EVENT_TYPES,
    Event,
)


POLISH_MONTHS = {
    1: "Styczeń",
    2: "Luty",
    3: "Marzec",
    4: "Kwiecień",
    5: "Maj",
    6: "Czerwiec",
    7: "Lipiec",
    8: "Sierpień",
    9: "Wrzesień",
    10: "Październik",
    11: "Listopad",
    12: "Grudzień",
}


POLISH_WEEKDAYS = {
    0: "Poniedziałek",
    1: "Wtorek",
    2: "Środa",
    3: "Czwartek",
    4: "Piątek",
    5: "Sobota",
    6: "Niedziela",
}


EVENT_STYLE_KEYS = {
    "PLANOWANA DOSTAWA": "planned",
    "ZREALIZOWANA DOSTAWA": "completed",
    "SPOTKANIE": "meeting",
    "ODBIÓR OSOBISTY": "pickup",
    "SPEDYCJA": "shipping",
    "INNE": "other",
}


EVENT_SHORT_LABELS = {
    "PLANOWANA DOSTAWA": "Dostawa",
    "ZREALIZOWANA DOSTAWA": "Zrealizowana",
    "SPOTKANIE": "Spotkanie",
    "ODBIÓR OSOBISTY": "Odbiór",
    "SPEDYCJA": "Spedycja",
    "INNE": "Inne",
}


def get_event_types():
    return [
        {
            "value": value,
            "label": label,
        }
        for value, label in EVENT_TYPES
    ]


def serialize_event(event):
    return {
        "id": event.id,
        "type": event.event_type,
        "type_label": EVENT_SHORT_LABELS.get(
            event.event_type,
            event.event_type,
        ),
        "style_key": EVENT_STYLE_KEYS.get(
            event.event_type,
            "other",
        ),
        "title": event.title,
        "details": event.details or "",
        "day": event.day.isoformat(),
        "is_completed": (
            event.event_type
            == "ZREALIZOWANA DOSTAWA"
        ),
    }


def get_events_by_date(
    *,
    date_from,
    date_to,
):
    events = (
        Event.objects
        .filter(
            day__gte=date_from,
            day__lte=date_to,
        )
        .order_by(
            "day",
            "event_type",
            "title",
        )
    )

    events_by_day = {}

    for event in events:
        events_by_day.setdefault(
            event.day,
            [],
        ).append(
            serialize_event(event)
        )

    return events_by_day


# ==========================================================
# MONTH
# ==========================================================

def get_month_context(
    *,
    year=None,
    month=None,
):
    today = datetime.date.today()

    current_week_start = (
            today
            - datetime.timedelta(
        days=today.weekday()
    )
    )

    current_week_end = (
            current_week_start
            + datetime.timedelta(days=6)
    )

    year = year or today.year
    month = month or today.month

    current_month = datetime.date(
        year,
        month,
        1,
    )

    previous_month = (
        current_month
        - datetime.timedelta(days=1)
    ).replace(day=1)

    if month == 12:
        next_month = datetime.date(
            year + 1,
            1,
            1,
        )
    else:
        next_month = datetime.date(
            year,
            month + 1,
            1,
        )

    calendar_builder = calendar.Calendar(
        firstweekday=calendar.MONDAY,
    )

    raw_weeks = (
        calendar_builder.monthdatescalendar(
            year,
            month,
        )
    )

    visible_start = raw_weeks[0][0]
    visible_end = raw_weeks[-1][-1]

    events_by_day = get_events_by_date(
        date_from=visible_start,
        date_to=visible_end,
    )

    weeks = []

    for raw_week in raw_weeks:
        week = []

        for day in raw_week:
            week.append({
                "date": day,

                "weekday_name":
                    POLISH_WEEKDAYS[
                        day.weekday()
                    ],

                "is_current_month":
                    day.month == month,

                "is_today":
                    day == today,

                "is_current_week": (
                        current_week_start
                        <= day
                        <= current_week_end
                ),

                "events":
                    events_by_day.get(
                        day,
                        [],
                    ),
            })

        weeks.append(week)

    return {
        "today": today,

        "calendar_view": "month",

        "year": year,
        "month": month,

        "month_name":
            POLISH_MONTHS[month],

        "month_label":
            f"{POLISH_MONTHS[month]} {year}",

        "weeks": weeks,

        "previous_month":
            previous_month,

        "next_month":
            next_month,

        "event_types":
            get_event_types(),
    }


# ==========================================================
# WEEK
# ==========================================================

def get_week_context(
    *,
    selected_date=None,
):
    today = datetime.date.today()

    selected_date = (
        selected_date
        or today
    )

    week_start = (
        selected_date
        - datetime.timedelta(
            days=selected_date.weekday()
        )
    )

    week_end = (
        week_start
        + datetime.timedelta(days=6)
    )

    previous_week = (
        week_start
        - datetime.timedelta(days=7)
    )

    next_week = (
        week_start
        + datetime.timedelta(days=7)
    )

    events_by_day = get_events_by_date(
        date_from=week_start,
        date_to=week_end,
    )

    days = []

    for offset in range(7):
        day = (
            week_start
            + datetime.timedelta(
                days=offset
            )
        )

        days.append({
            "date": day,
            "weekday_name":
                POLISH_WEEKDAYS[
                    day.weekday()
                ],
            "is_today":
                day == today,
            "events":
                events_by_day.get(
                    day,
                    [],
                ),
        })

    return {
        "today": today,

        "calendar_view": "week",

        "week_start":
            week_start,

        "week_end":
            week_end,

        "previous_week":
            previous_week,

        "next_week":
            next_week,

        "days": days,

        "event_types":
            get_event_types(),
        "year": selected_date.year,
        "month": selected_date.month,
    }


# ==========================================================
# DAY EVENTS
# ==========================================================

def get_events_for_day(day):
    events = (
        Event.objects
        .filter(day=day)
        .order_by(
            "event_type",
            "title",
        )
    )

    return [
        serialize_event(event)
        for event in events
    ]


# ==========================================================
# SINGLE EVENT
# ==========================================================

def get_event(event_id):
    return get_object_or_404(
        Event,
        id=event_id,
    )


# ==========================================================
# CREATE
# ==========================================================

def create_event(
    *,
    event_type,
    title,
    day,
    details=None,
):
    valid_types = {
        value
        for value, _ in EVENT_TYPES
    }

    if event_type not in valid_types:
        raise ValueError(
            "Nieprawidłowy typ wydarzenia."
        )

    title = (
        title or ""
    ).strip()

    if not title:
        raise ValueError(
            "Podaj tytuł wydarzenia."
        )

    try:
        event_day = (
            datetime.date.fromisoformat(
                day
            )
        )

    except (TypeError, ValueError):
        raise ValueError(
            "Nieprawidłowa data wydarzenia."
        )

    return Event.objects.create(
        event_type=event_type,
        title=title,
        day=event_day,
        details=(
            details or ""
        ).strip(),
    )


# ==========================================================
# UPDATE
# ==========================================================

def update_event(
    *,
    event_id,
    event_type,
    title,
    day,
    details=None,
):
    event = get_event(
        event_id
    )

    valid_types = {
        value
        for value, _ in EVENT_TYPES
    }

    if event_type not in valid_types:
        raise ValueError(
            "Nieprawidłowy typ wydarzenia."
        )

    title = (
        title or ""
    ).strip()

    if not title:
        raise ValueError(
            "Podaj tytuł wydarzenia."
        )

    try:
        event_day = (
            datetime.date.fromisoformat(
                day
            )
        )

    except (TypeError, ValueError):
        raise ValueError(
            "Nieprawidłowa data wydarzenia."
        )

    event.event_type = event_type
    event.title = title
    event.day = event_day
    event.details = (
        details or ""
    ).strip()

    event.save(
        update_fields=[
            "event_type",
            "title",
            "day",
            "details",
        ]
    )

    return event


# ==========================================================
# COMPLETE
# ==========================================================

def complete_event(event_id):
    event = get_event(
        event_id
    )

    event.event_type = (
        "ZREALIZOWANA DOSTAWA"
    )

    event.save(
        update_fields=[
            "event_type",
        ]
    )

    return event


# ==========================================================
# DELETE
# ==========================================================

def delete_event(event_id):
    event = get_event(
        event_id
    )

    event.delete()


def reopen_event(event_id):
    event = get_event(event_id)

    if event.event_type != "ZREALIZOWANA DOSTAWA":
        raise ValueError(
            "Tylko zrealizowaną dostawę można przywrócić do planowanych."
        )

    event.event_type = "PLANOWANA DOSTAWA"

    event.save(
        update_fields=[
            "event_type",
        ]
    )

    return event