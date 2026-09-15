import datetime

from django.db.models import Q

from warehousemanager.models import (
    Buyer,
    Photopolymer,
    PhotopolymerService,
    POLYMERS_PRODUCERS,
)

from collections import defaultdict
from dateutil.relativedelta import relativedelta

from production.models import ProductionOrder
from warehouse.models import Order

from django.shortcuts import get_object_or_404


POLYMER_STATUS_LABELS = {
    "on_site": "Na miejscu",
    "away": "Poza firmą",
    "not_delivered": "Niedostarczony",
    "inactive": "Nieaktywny",
}


def get_polymer_status(
    *,
    polymer,
    current_service_ids,
    today,
):
    if not polymer.active:
        return "inactive"

    if polymer.id in current_service_ids:
        return "away"

    if (
        not polymer.delivery_date
        or polymer.delivery_date > today
    ):
        return "not_delivered"

    return "on_site"


def get_polymer_list_context(
    *,
    search="",
    customer_id="",
    producer="",
    status="",
    historical=""
):
    today = datetime.date.today()

    search = (search or "").strip()
    customer_id = str(customer_id or "").strip()
    producer = (producer or "").strip()
    status = (status or "").strip()
    historical = (historical or "").strip()

    # ======================================================
    # SERVICES
    # ======================================================

    current_services = list(
        PhotopolymerService.objects
        .filter(
            Q(return_date__isnull=True)
            | Q(return_date__gte=today)
        )
        .select_related(
            "photopolymer",
            "photopolymer__customer",
        )
        .order_by(
            "-send_date",
            "photopolymer__identification_number",
        )
    )

    current_service_ids = {
        service.photopolymer_id
        for service in current_services
    }

    history_services = (
        PhotopolymerService.objects
        .filter(
            return_date__lt=today,
        )
        .select_related(
            "photopolymer",
            "photopolymer__customer",
        )
        .order_by(
            "-return_date",
            "-send_date",
        )[:50]
    )


    # ======================================================
    # POLYMERS
    # ======================================================

    historical = (True, False) if historical else (True,)

    polymers_queryset = (
        Photopolymer.objects.filter(active__in=historical)
        .select_related(
            "customer",
        )
        .prefetch_related(
            "colors",
        )
        .order_by(
            "identification_number",
            "identification_letter",
        )
    )


    # ======================================================
    # SEARCH
    # ======================================================

    if search:
        search_query = (
            Q(name__icontains=search)
            | Q(
                customer__name__icontains=
                    search
            )
            | Q(
                identification_letter__icontains=
                    search
            )
        )

        if search.isdigit():
            search_query |= Q(
                identification_number=
                    int(search)
            )

        polymers_queryset = (
            polymers_queryset.filter(
                search_query
            )
        )


    # ======================================================
    # FILTERS
    # ======================================================

    if customer_id:
        polymers_queryset = (
            polymers_queryset.filter(
                customer_id=customer_id
            )
        )

    if producer:
        polymers_queryset = (
            polymers_queryset.filter(
                producer=producer
            )
        )


    # ======================================================
    # ROWS
    # ======================================================

    polymers = []

    for polymer in polymers_queryset:
        polymer_status = get_polymer_status(
            polymer=polymer,
            current_service_ids=
                current_service_ids,
            today=today,
        )

        if (
            status
            and polymer_status != status
        ):
            continue

        polymers.append({
            "object": polymer,
            "number": (
                f"{polymer.identification_number}"
                f"{polymer.identification_letter or ''}"
            ),
            "status": polymer_status,
            "status_label":
                POLYMER_STATUS_LABELS[
                    polymer_status
                ],
            "colors":
                list(
                    polymer.colors.all()
                ),
        })


    # ======================================================
    # SUMMARY
    # ======================================================

    summary = {
        "total": len(polymers),

        "on_site": sum(
            1
            for row in polymers
            if row["status"] == "on_site"
        ),

        "away": sum(
            1
            for row in polymers
            if row["status"] == "away"
        ),

        "not_delivered": sum(
            1
            for row in polymers
            if row["status"]
            == "not_delivered"
        ),

        "inactive": sum(
            1
            for row in polymers
            if row["status"] == "inactive"
        ),
    }


    return {
        "polymers": polymers,

        "current_services":
            current_services,

        "history_services":
            history_services,

        "customers":
            Buyer.objects
            .all()
            .order_by("name"),

        "producers":
            POLYMERS_PRODUCERS,

        "summary":
            summary,

        "filters": {
            "q": search,
            "customer": customer_id,
            "producer": producer,
            "status": status,
        },
    }


def get_polymer_detail_context(*, polymer_id):
    from production.models import ProductionOrder
    from warehouse.models import Order

    today = datetime.date.today()

    polymer = get_object_or_404(
        Photopolymer.objects
        .select_related(
            "customer",
        )
        .prefetch_related(
            "colors",
        ),
        id=polymer_id,
    )

    # ======================================================
    # SERVICES
    # ======================================================

    services = list(
        PhotopolymerService.objects
        .filter(
            photopolymer=polymer,
        )
        .order_by(
            "-send_date",
            "-id",
        )
    )

    current_services = []
    history_services = []

    for service in services:
        if (
            service.return_date is None
            or service.return_date >= today
        ):
            current_services.append(service)
        else:
            history_services.append(service)

    current_service_ids = {
        polymer.id
        if current_services
        else None
    }

    status = get_polymer_status(
        polymer=polymer,
        current_service_ids=current_service_ids,
        today=today,
    )

    # ======================================================
    # PRODUCTION HISTORY
    #
    # NOWA LOGIKA:
    # Photopolymer -> ProductionOrder.photopolymer
    # ======================================================

    production_orders = list(
        ProductionOrder.objects
        .filter(
            photopolymer=polymer,
        )
        .select_related(
            "customer",
        )
    )

    # ======================================================
    # WAREHOUSE ORDERS
    #
    # ProductionOrder.id_number:
    #   "JASS 123/26"
    #
    # Order.order_id:
    #   "123/26"
    # ======================================================

    order_numbers = []

    for production_order in production_orders:
        if not production_order.id_number:
            continue

        order_number = (
            production_order.id_number
            .rsplit(" ", 1)[-1]
            .strip()
        )

        if order_number:
            order_numbers.append(
                order_number
            )

    warehouse_orders = list(
        Order.objects
        .filter(
            order_id__in=order_numbers,
        )
        .select_related(
            "provider",
            "customer",
        )
    )

    # ======================================================
    # MAPA ZAMÓWIEŃ
    #
    # klucz:
    # "JASS 123/26"
    # ======================================================

    warehouse_order_map = {
        f"{order.provider} {order.order_id}":
            order
        for order in warehouse_orders
    }

    # ======================================================
    # PRODUCTION USAGE
    # ======================================================

    production_usage = []

    for production_order in production_orders:

        warehouse_order = (
            warehouse_order_map.get(
                production_order.id_number
            )
        )

        order_date = (
            warehouse_order.order_date
            if warehouse_order
            else None
        )

        quantity = (
            production_order.quantity
            or 0
        )

        production_usage.append({
            "production_order":
                production_order,

            "warehouse_order":
                warehouse_order,

            "number":
                production_order.id_number,

            "customer":
                production_order.customer,

            "quantity":
                quantity,

            # zgodnie z założeniem:
            # pokazujemy datę zamówienia
            "order_date":
                order_date,
        })

    # ======================================================
    # SORTOWANIE
    # najnowsze zamówienia najpierw
    # ======================================================

    production_usage.sort(
        key=lambda row: (
            row["order_date"]
            is not None,

            row["order_date"]
            or datetime.date.min,
        ),
        reverse=True,
    )

    # ======================================================
    # SUMMARY
    # ======================================================

    production_total_quantity = sum(
        row["quantity"]
        for row in production_usage
    )

    production_dates = [
        row["order_date"]
        for row in production_usage
        if row["order_date"]
    ]

    production_first_date = (
        min(production_dates)
        if production_dates
        else None
    )

    production_last_date = (
        max(production_dates)
        if production_dates
        else None
    )

    production_orders_count = len(
        production_usage
    )

    # ======================================================
    # CONTEXT
    # ======================================================

    return {
        "polymer":
            polymer,

        "number": (
            f"{polymer.identification_number}"
            f"{polymer.identification_letter or ''}"
        ),

        "status":
            status,

        "status_label":
            POLYMER_STATUS_LABELS[
                status
            ],

        "colors":
            list(
                polymer.colors.all()
            ),

        "current_services":
            current_services,

        "history_services":
            history_services,

        # production
        "production_usage":
            production_usage,

        "production_total_quantity":
            production_total_quantity,

        "production_orders_count":
            production_orders_count,

        "production_first_date":
            production_first_date,

        "production_last_date":
            production_last_date,
    }

def get_polymer_service(*, service_id):
    return get_object_or_404(
        PhotopolymerService.objects
        .select_related(
            "photopolymer",
            "photopolymer__customer",
        ),
        id=service_id,
    )


def get_polymer_service_context(
    *,
    service_id,
):
    service = get_polymer_service(
        service_id=service_id,
    )

    return {
        "service": service,
        "polymer": service.photopolymer,
        "is_current": (
            service.return_date is None
            or service.return_date
            >= datetime.date.today()
        ),
    }


def get_unused_polymers_context(*, months=12):
    today = datetime.date.today()

    try:
        months = int(months)
    except (TypeError, ValueError):
        months = 12

    months = max(1, min(months, 120))

    cutoff_date = today - relativedelta(
        months=months
    )

    # ======================================================
    # POLYMERS
    # ======================================================

    polymers = list(
        Photopolymer.objects.filter(active=True)
        .select_related(
            "customer",
        )
        .order_by(
            "customer__name",
            "name",
            "identification_number",
            "identification_letter",
        )
    )

    polymer_ids = [
        polymer.id
        for polymer in polymers
    ]

    # ======================================================
    # PRODUCTION ORDERS
    #
    # nowa logika:
    # ProductionOrder.photopolymer
    # ======================================================

    production_orders = list(
        ProductionOrder.objects
        .filter(
            photopolymer_id__in=polymer_ids,
        )
        .select_related(
            "photopolymer",
        )
    )

    # ======================================================
    # ODCZYT NUMERÓW ORDER
    # ======================================================

    order_numbers = set()

    for production_order in production_orders:
        if not production_order.id_number:
            continue

        try:
            order_number = (
                production_order.id_number
                .rsplit(" ", 1)[-1]
                .strip()
            )

            if order_number:
                order_numbers.add(
                    order_number
                )

        except (AttributeError, IndexError):
            continue

    # ======================================================
    # WAREHOUSE ORDERS
    # ======================================================

    warehouse_orders = (
        Order.objects
        .filter(
            order_id__in=order_numbers,
        )
        .select_related(
            "provider",
        )
    )

    warehouse_order_map = {
        f"{order.provider} {order.order_id}":
            order
        for order in warehouse_orders
    }

    # ======================================================
    # LAST USE PER POLYMER
    # ======================================================

    polymer_last_use = {}

    polymer_orders_count = defaultdict(int)

    for production_order in production_orders:

        warehouse_order = (
            warehouse_order_map.get(
                production_order.id_number
            )
        )

        if not warehouse_order:
            continue

        order_date = warehouse_order.order_date

        if not order_date:
            continue

        polymer_id = (
            production_order.photopolymer_id
        )

        polymer_orders_count[
            polymer_id
        ] += 1

        current_last_use = (
            polymer_last_use.get(
                polymer_id
            )
        )

        if (
            current_last_use is None
            or order_date > current_last_use
        ):
            polymer_last_use[
                polymer_id
            ] = order_date

    # ======================================================
    # GROUPING
    #
    # grupa = customer + normalized name
    #
    # brak nazwy:
    # każdy polimer osobno
    # ======================================================

    groups = {}

    for polymer in polymers:

        normalized_name = (
            (polymer.name or "")
            .strip()
            .casefold()
        )

        if normalized_name:

            group_key = (
                polymer.customer_id,
                normalized_name,
            )

        else:

            # bez nazwy nie grupujemy przypadkowych
            # polimerów razem
            group_key = (
                polymer.customer_id,
                f"__polymer_{polymer.id}",
            )

        if group_key not in groups:

            groups[group_key] = {
                "customer":
                    polymer.customer,

                "name":
                    polymer.name or "Bez nazwy",

                "polymers":
                    [],

                "last_use":
                    None,

                "orders_count":
                    0,
            }

        last_use = polymer_last_use.get(
            polymer.id
        )

        groups[group_key][
            "polymers"
        ].append({
            "object":
                polymer,

            "number": (
                f"{polymer.identification_number}"
                f"{polymer.identification_letter or ''}"
            ),

            "last_use":
                last_use,

            "orders_count":
                polymer_orders_count.get(
                    polymer.id,
                    0,
                ),
        })

        groups[group_key][
            "orders_count"
        ] += polymer_orders_count.get(
            polymer.id,
            0,
        )

        # data całej grupy =
        # najnowsze użycie dowolnego polimeru
        if last_use:

            current_group_last_use = (
                groups[group_key][
                    "last_use"
                ]
            )

            if (
                current_group_last_use is None
                or last_use >
                current_group_last_use
            ):
                groups[group_key][
                    "last_use"
                ] = last_use

    # ======================================================
    # FILTER UNUSED
    # ======================================================

    unused_groups = []

    for group in groups.values():

        last_use = group["last_use"]

        # brak historii traktujemy jako
        # "nigdy nieużywany"
        if (
            last_use is None
            or last_use <= cutoff_date
        ):

            group["is_group"] = (
                len(group["polymers"]) > 1
            )

            group["polymers_count"] = (
                len(group["polymers"])
            )

            unused_groups.append(group)

    # ======================================================
    # SORTOWANIE
    #
    # najstarsze / nigdy używane najpierw
    # ======================================================

    unused_groups.sort(
        key=lambda group: (
            group["last_use"] is not None,
            group["last_use"]
            or datetime.date.min,
            str(group["customer"]),
            group["name"],
        )
    )

    never_used_count = sum(
        1
        for group in unused_groups
        if group["last_use"] is None
    )

    return {
        "groups":
            unused_groups,

        "months":
            months,

        "cutoff_date":
            cutoff_date,

        "groups_count":
            len(unused_groups),

        "polymers_count":
            sum(
                group["polymers_count"]
                for group in unused_groups
            ),

        "never_used_count":
            never_used_count,
    }
