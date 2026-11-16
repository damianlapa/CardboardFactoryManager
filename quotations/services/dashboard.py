import datetime
from urllib.parse import urlencode

from django.core.paginator import Paginator
from django.db.models import Count, Q

from ..models import Quotation, QuotationCustomer, QuotationItem


def get_dashboard_context(params):
    today = datetime.date.today()
    month_start = today.replace(day=1)
    next_month = (month_start + datetime.timedelta(days=32)).replace(day=1)

    counters = Quotation.objects.aggregate(
        total=Count("pk"),
        month=Count("pk", filter=Q(date__gte=month_start, date__lt=next_month)),
    )
    counters["customers"] = QuotationCustomer.objects.count()
    counters["items"] = QuotationItem.objects.count()

    filters = {
        "search": params.get("search", "").strip()[:200],
        "date_from": params.get("date_from", "").strip(),
        "date_to": params.get("date_to", "").strip(),
    }
    dates = {}
    errors = []
    for name, label in (("date_from", "Data od"), ("date_to", "Data do")):
        if filters[name]:
            try:
                dates[name] = datetime.date.fromisoformat(filters[name])
            except ValueError:
                errors.append(f"{label}: podaj poprawną datę w formacie RRRR-MM-DD.")

    if len(dates) == 2 and dates["date_from"] > dates["date_to"]:
        errors.append("Data początkowa nie może być późniejsza niż data końcowa.")

    quotations = Quotation.objects.select_related("customer")
    search = filters["search"]
    if search:
        condition = Q(customer__name__icontains=search)
        number = search.removeprefix("#")
        if number.isascii() and number.isdecimal() and len(number) <= 18:
            condition |= Q(pk=int(number))
        quotations = quotations.filter(condition)

    if errors:
        # Invalid dates must not silently produce an unfiltered result list.
        quotations = quotations.none()
    else:
        if "date_from" in dates:
            quotations = quotations.filter(date__gte=dates["date_from"])
        if "date_to" in dates:
            quotations = quotations.filter(date__lte=dates["date_to"])

    quotations = quotations.annotate(items_count=Count("items")).order_by("-date", "-pk")
    page_obj = Paginator(quotations, 15).get_page(params.get("page"))

    return {
        "today": today,
        "counters": counters,
        "filters": filters,
        "filter_errors": errors,
        "has_filters": any(filters.values()),
        "filter_query": urlencode({key: value for key, value in filters.items() if value}),
        "page_obj": page_obj,
    }
