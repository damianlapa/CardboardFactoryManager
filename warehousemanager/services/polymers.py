import datetime

from django.db.models import Q

from warehousemanager.models import (
    Buyer,
    Photopolymer,
    PhotopolymerService,
    POLYMERS_PRODUCERS,
)

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
):
    today = datetime.date.today()

    search = (search or "").strip()
    customer_id = str(customer_id or "").strip()
    producer = (producer or "").strip()
    status = (status or "").strip()


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

    polymers_queryset = (
        Photopolymer.objects
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