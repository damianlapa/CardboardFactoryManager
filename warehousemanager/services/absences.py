import calendar
import datetime
from dataclasses import dataclass

from django.contrib.auth.models import AnonymousUser

from warehousemanager.models import (
    Absence,
    Contract,
    ExtraHour,
    Holiday,
    LocalSetting,
    Person,
)


POLISH_MONTH_NAMES = (
    "styczeń",
    "luty",
    "marzec",
    "kwiecień",
    "maj",
    "czerwiec",
    "lipiec",
    "sierpień",
    "wrzesień",
    "październik",
    "listopad",
    "grudzień",
)

SUPPORTED_CONTRACT_TYPES = {
    "UOP",
    "UZ",
    "FZ",
}


@dataclass(frozen=True)
class CalendarPeriod:
    year: int
    month: int

    def __post_init__(self):
        if self.month < 1 or self.month > 12:
            raise ValueError("Month must be between 1 and 12.")

    @property
    def start(self):
        return datetime.date(
            self.year,
            self.month,
            1,
        )

    @property
    def end(self):
        last_day = calendar.monthrange(
            self.year,
            self.month,
        )[1]

        return datetime.date(
            self.year,
            self.month,
            last_day,
        )

    @property
    def label(self):
        return (
            f"{POLISH_MONTH_NAMES[self.month - 1]} "
            f"{self.year}"
        )

    def shifted(self, months):
        index = (
            self.year * 12
            + self.month
            - 1
            + months
        )

        return CalendarPeriod(
            year=index // 12,
            month=index % 12 + 1,
        )


def resolve_period(year=None, month=None):
    today = datetime.date.today()

    try:
        selected_year = int(year)
    except (TypeError, ValueError):
        selected_year = today.year

    try:
        selected_month = int(month)
    except (TypeError, ValueError):
        selected_month = today.month

    if selected_month not in range(1, 13):
        selected_month = today.month

    return CalendarPeriod(
        year=selected_year,
        month=selected_month,
    )


def resolve_contract_type(value):
    if value in SUPPORTED_CONTRACT_TYPES:
        return value

    return "UOP"


def get_excluded_worker_ids():
    setting = (
        LocalSetting.objects
        .filter(name="excluded_workers")
        .first()
    )

    if not setting or not setting.value:
        return set()

    worker_ids = set()

    for raw_value in setting.value.split(","):
        raw_value = raw_value.strip()

        if not raw_value:
            continue

        try:
            first_name, last_name = raw_value.split(
                "_",
                1,
            )
        except ValueError:
            continue

        worker_id = (
            Person.objects
            .filter(
                first_name=first_name,
                last_name=last_name,
            )
            .values_list("id", flat=True)
            .first()
        )

        if worker_id:
            worker_ids.add(worker_id)

    return worker_ids


def get_visible_workers(
    *,
    user,
    period,
    contract_type,
):
    if isinstance(user, AnonymousUser):
        return Person.objects.none()

    if not user.is_superuser:
        return (
            Person.objects
            .filter(user=user)
            .filter(job_start__lte=period.end)
            .exclude(job_end__lt=period.start)
        )

    active_workers = (
        Person.objects
        .filter(job_start__lte=period.end)
        .exclude(job_end__lt=period.start)
    )

    excluded_ids = get_excluded_worker_ids()

    if excluded_ids:
        active_workers = active_workers.exclude(
            id__in=excluded_ids
        )

    contract_worker_ids = (
        Contract.objects
        .filter(
            worker__in=active_workers,
            type=contract_type,
            date_start__lte=period.end,
        )
        .exclude(
            date_end__lt=period.start,
        )
        .values_list(
            "worker_id",
            flat=True,
        )
        .distinct()
    )

    return (
        active_workers
        .filter(id__in=contract_worker_ids)
        .order_by(
            "last_name",
            "first_name",
        )
    )


def get_calendar_days(period):
    today = datetime.date.today()

    result = []

    for day_number in range(
        1,
        period.end.day + 1,
    ):
        date = datetime.date(
            period.year,
            period.month,
            day_number,
        )

        result.append({
            "number": day_number,
            "date": date,
            "weekday": date.weekday(),
            "is_weekend": date.weekday() >= 5,
            "is_past": date < today,
            "is_today": date == today,
            "is_future": date > today,
        })

    return result


def get_available_periods(
    start_year=2017,
    months_ahead=12,
):
    today = datetime.date.today()

    current = CalendarPeriod(
        start_year,
        1,
    )

    last = CalendarPeriod(
        today.year,
        today.month,
    ).shifted(months_ahead)

    periods = []

    while (
        current.year,
        current.month,
    ) <= (
        last.year,
        last.month,
    ):
        periods.append({
            "year": current.year,
            "month": current.month,
            "value": (
                f"{current.year}-"
                f"{current.month:02d}"
            ),
            "label": current.label,
        })

        current = current.shifted(1)

    return periods


def build_calendar_context(
    *,
    user,
    year=None,
    month=None,
    contract_type=None,
):
    period = resolve_period(
        year=year,
        month=month,
    )

    contract_type = resolve_contract_type(
        contract_type
    )

    workers = get_visible_workers(
        user=user,
        period=period,
        contract_type=contract_type,
    )

    previous_period = period.shifted(-1)
    next_period = period.shifted(1)

    return {
        "selected_period": period,
        "selected_year": period.year,
        "selected_month": period.month,
        "selected_month_label": period.label,

        "previous_period": previous_period,
        "next_period": next_period,

        "calendar_days": get_calendar_days(
            period,
        ),

        "workers": workers,

        "contract_type": contract_type,
        "contract_types": (
            ("UOP", "Umowa o pracę"),
            ("UZ", "Umowa zlecenie"),
        ),

        "available_periods": get_available_periods(),

        "report_year": period.year,
        "report_month": period.month,
    }


def build_calendar_data(
    *,
    user,
    year=None,
    month=None,
    contract_type=None,
):
    period = resolve_period(
        year=year,
        month=month,
    )

    contract_type = resolve_contract_type(
        contract_type
    )

    workers = list(
        get_visible_workers(
            user=user,
            period=period,
            contract_type=contract_type,
        )
    )

    worker_ids = [
        worker.id
        for worker in workers
    ]

    absences = (
        Absence.objects
        .filter(
            worker_id__in=worker_ids,
            absence_date__range=(
                period.start,
                period.end,
            ),
        )
        .select_related("worker")
    )

    extra_hours = (
        ExtraHour.objects
        .filter(
            worker_id__in=worker_ids,
            extras_date__range=(
                period.start,
                period.end,
            ),
        )
        .select_related("worker")
    )

    holidays = Holiday.objects.filter(
        holiday_date__range=(
            period.start,
            period.end,
        )
    )

    absence_items = []

    for absence in absences:
        absence_items.append({
            "id": absence.id,
            "worker_id": absence.worker_id,
            "day": absence.absence_date.day,
            "date": absence.absence_date.isoformat(),
            "type": absence.absence_type,
            "value": absence.value,
            "additional_info": (
                absence.additional_info or ""
            ),
        })

    extra_hour_items = []

    for extra_hour in extra_hours:
        extra_hour_items.append({
            "id": extra_hour.id,
            "worker_id": extra_hour.worker_id,
            "day": extra_hour.extras_date.day,
            "date": extra_hour.extras_date.isoformat(),
            "quantity": float(extra_hour.quantity),
            "full_day": extra_hour.full_day,
        })

    holiday_items = [
        {
            "day": holiday.holiday_date.day,
            "date": holiday.holiday_date.isoformat(),
            "name": holiday.name,
        }
        for holiday in holidays
    ]

    employment_exclusions = []

    for worker in workers:
        excluded_days = []

        for day_number in range(
            1,
            period.end.day + 1,
        ):
            date = datetime.date(
                period.year,
                period.month,
                day_number,
            )

            if worker.job_start and date < worker.job_start:
                excluded_days.append(day_number)
                continue

            if worker.job_end and date > worker.job_end:
                excluded_days.append(day_number)

        if excluded_days:
            employment_exclusions.append({
                "worker_id": worker.id,
                "days": excluded_days,
            })

    return {
        "period": {
            "year": period.year,
            "month": period.month,
            "label": period.label,
        },

        "absences": absence_items,
        "extra_hours": extra_hour_items,
        "holidays": holiday_items,
        "employment_exclusions": employment_exclusions,
    }