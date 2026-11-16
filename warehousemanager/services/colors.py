import datetime
from collections import defaultdict
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.shortcuts import get_object_or_404

from warehousemanager.models import (
    Color,
    ColorBucket,
    Photopolymer,
)


def get_stock_level(weight):
    weight = Decimal(str(weight or 0))

    if weight <= 0:
        return "empty"

    if weight <= 5:
        return "critical"

    if weight <= 10:
        return "low"

    if weight <= 20:
        return "warning"

    return "healthy"


def parse_decimal(value):
    if value is None:
        return None

    try:
        return Decimal(
            str(value).replace(",", ".")
        )
    except (InvalidOperation, ValueError):
        return None


def parse_bucket_usage(usage):
    if not usage:
        return []

    entries = []

    for raw_entry in usage.split("/"):
        raw_entry = raw_entry.strip()

        if not raw_entry:
            continue

        parts = raw_entry.split(";")

        if len(parts) != 3:
            continue

        date_raw, before_raw, after_raw = parts

        try:
            date = datetime.date.fromisoformat(
                date_raw
            )
        except ValueError:
            continue

        before = parse_decimal(before_raw)
        after = parse_decimal(after_raw)

        if before is None or after is None:
            continue

        entries.append({
            "date": date,
            "before": before,
            "after": after,
            "used": before - after,
        })

    return sorted(
        entries,
        key=lambda item: item["date"],
        reverse=True,
    )


def get_color_hex(color):
    try:
        return color.hex()
    except (AttributeError, TypeError, ValueError):
        return "#94a3b8"


def get_color_list():
    colors = Color.objects.all().order_by("name")

    rows = []

    for color in colors:
        buckets = ColorBucket.objects.filter(
            color=color,
        )

        current_weight = sum(
            Decimal(str(bucket.weight or 0))
            for bucket in buckets
        )

        active_buckets = [
            bucket
            for bucket in buckets
            if Decimal(str(bucket.weight or 0)) > 0
        ]

        rows.append({
            "color": color,
            "hex": get_color_hex(color),
            "current_weight": current_weight,
            "bucket_count": buckets.count(),
            "active_buckets": len(active_buckets),
            "stock_level": get_stock_level(
                current_weight
            ),
        })

    rows.sort(
        key=lambda row: row["current_weight"],
        reverse=True,
    )

    return rows


def get_color_details(color_id):
    color = get_object_or_404(
        Color,
        id=color_id,
    )

    buckets = list(
        ColorBucket.objects
        .filter(color=color)
        .select_related("color")
        .order_by(
            "-production_date",
            "-id",
        )
    )

    polymers = (
        Photopolymer.objects
        .filter(colors=color)
        .order_by("name")
    )

    current_weight = sum(
        Decimal(str(bucket.weight or 0))
        for bucket in buckets
    )

    active_buckets = [
        bucket
        for bucket in buckets
        if Decimal(str(bucket.weight or 0)) > 0
    ]

    usage_by_date = defaultdict(
        lambda: Decimal("0")
    )

    total_usage = Decimal("0")

    for bucket in buckets:
        for entry in parse_bucket_usage(
            bucket.usage
        ):
            usage = max(
                entry["used"],
                Decimal("0"),
            )

            usage_by_date[entry["date"]] += usage
            total_usage += usage

    cumulative = Decimal("0")
    chart = []

    for date in sorted(usage_by_date):
        cumulative += usage_by_date[date]

        chart.append({
            "date": date.isoformat(),
            "usage": float(
                usage_by_date[date]
            ),
            "cumulative": float(cumulative),
        })

    return {
        "color": color,
        "color_hex": get_color_hex(color),
        "buckets": buckets,
        "active_buckets": active_buckets,
        "polymers": polymers,
        "current_weight": current_weight,
        "total_usage": total_usage,
        "chart_data": chart,
    }


def get_bucket_details(bucket_id):
    bucket = get_object_or_404(
        ColorBucket.objects.select_related(
            "color"
        ),
        id=bucket_id,
    )

    history = parse_bucket_usage(
        bucket.usage
    )

    total_usage = sum(
        (
            max(
                item["used"],
                Decimal("0"),
            )
            for item in history
        ),
        Decimal("0"),
    )

    return {
        "bucket": bucket,
        "color": bucket.color,
        "color_hex": get_color_hex(
            bucket.color
        ),
        "history": history,
        "total_usage": total_usage,
        "today": datetime.date.today(),
    }


@transaction.atomic
def register_bucket_usage(
    *,
    bucket_id,
    usage_date,
    weight_before,
    weight_after,
):
    bucket = (
        ColorBucket.objects
        .select_for_update()
        .get(id=bucket_id)
    )

    try:
        date = datetime.date.fromisoformat(
            usage_date
        )
    except (TypeError, ValueError):
        raise ValueError(
            "Nieprawidłowa data."
        )

    before = parse_decimal(weight_before)
    after = parse_decimal(weight_after)

    if before is None or after is None:
        raise ValueError(
            "Podaj prawidłowe wartości masy."
        )

    if before < 0 or after < 0:
        raise ValueError(
            "Masa nie może być ujemna."
        )

    # if after > before:
    #     raise ValueError(
    #         "Masa po użyciu nie może być większa "
    #         "od masy przed użyciem."
    #     )

    current_weight = Decimal(
        str(bucket.weight or 0)
    )

    if before != current_weight:
        raise ValueError(
            (
                "Masa początkowa nie odpowiada "
                "aktualnemu stanowi wiadra."
            )
        )

    new_entry = (
        f"{date.isoformat()};"
        f"{before};"
        f"{after}"
    )

    bucket.usage = (
        f"{bucket.usage}/{new_entry}"
        if bucket.usage
        else new_entry
    )

    bucket.weight = after

    bucket.save(
        update_fields=[
            "usage",
            "weight",
        ]
    )

    return bucket