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


def get_month_context(*, year=None, month=None):
    today = datetime.date.today()

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

    next_month = (
        current_month.replace(day=28)
        + datetime.timedelta(days=4)
    ).replace(day=1)

    month_calendar = calendar.Calendar(
        firstweekday=0,
    )

    month_dates = month_calendar.monthdatescalendar(
        year,
        month,
    )

    visible_start = month_dates[0][0]
    visible_end = month_dates[-1][-1]

    events = (
        Event.objects
        .filter(
            day__gte=visible_start,
            day__lte=visible_end,
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
        ).append({
            "event_types": get_event_types(),
            "id": event.id,
            "title": event.title,
            "type": event.event_type,
            "details": event.details,
            "style_key": EVENT_STYLE_KEYS.get(
                event.event_type,
                "other",
            ),
        })

    weeks = []

    for week in month_dates:
        week_data = []

        for day in week:
            week_data.append({
                "date": day,
                "is_current_month":
                    day.month == month,
                "is_today":
                    day == today,
                "events":
                    events_by_day.get(
                        day,
                        [],
                    ),
            })

        weeks.append(
            week_data
        )

    return {
        "today": today,
        "year": year,
        "month": month,
        "month_name": POLISH_MONTHS[month],
        "month_label": (
            f"{POLISH_MONTHS[month]} {year}"
        ),
        "weeks": weeks,
        "previous_month": previous_month,
        "next_month": next_month,
        "event_types": get_event_types(),
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

    title = (title or "").strip()

    if not title:
        raise ValueError(
            "Podaj tytuł wydarzenia."
        )

    try:
        event_day = datetime.date.fromisoformat(
            day
        )
    except (TypeError, ValueError):
        raise ValueError(
            "Nieprawidłowa data wydarzenia."
        )

    event = Event.objects.create(
        event_type=event_type,
        title=title,
        day=event_day,
        details=(details or "").strip(),
    )

    return event


def get_event(event_id):
    return get_object_or_404(
        Event,
        id=event_id,
    )


def update_event(
    *,
    event_id,
    event_type,
    title,
    day,
    details=None,
):
    event = get_event(event_id)

    valid_types = {
        value
        for value, _ in EVENT_TYPES
    }

    if event_type not in valid_types:
        raise ValueError(
            "Nieprawidłowy typ wydarzenia."
        )

    title = (title or "").strip()

    if not title:
        raise ValueError(
            "Podaj tytuł wydarzenia."
        )

    try:
        event_day = datetime.date.fromisoformat(
            day
        )
    except (TypeError, ValueError):
        raise ValueError(
            "Nieprawidłowa data wydarzenia."
        )

    event.event_type = event_type
    event.title = title
    event.day = event_day
    event.details = (details or "").strip()

    event.save(
        update_fields=[
            "event_type",
            "title",
            "day",
            "details",
        ]
    )

    return event


def complete_event(event_id):
    event = get_event(event_id)

    event.event_type = (
        "ZREALIZOWANA DOSTAWA"
    )

    event.save(
        update_fields=[
            "event_type",
        ]
    )

    return event


def delete_event(event_id):
    event = get_event(event_id)

    event.delete()