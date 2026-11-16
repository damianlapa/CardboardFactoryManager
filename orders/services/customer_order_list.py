import re

from django.core.paginator import Paginator
from django.db.models import Exists, OuterRef, Q

from orders.models import (
    CustomerOrder,
    MaterialRequirement,
    MaterialAllocation,
)

from warehouse.models import Product
from warehousemanager.models import Buyer


PAGE_SIZE = 25


def _parse_order_number(value):
    """
    Obsługuje:
        188
        188/26
        188/2026
    """

    value = (value or "").strip()

    match = re.fullmatch(
        r"(\d+)(?:/(\d{2}|\d{4}))?",
        value,
    )

    if not match:
        return None

    number = int(match.group(1))

    year = match.group(2)

    if year:
        year = int(year)

        if year < 100:
            year += 2000

    return number, year


def get_customer_orders_queryset():
    """
    Bazowy queryset dla listy zamówień.
    """

    requirement_qs = (
        MaterialRequirement.objects
        .filter(
            customer_order_id=OuterRef("pk")
        )
    )

    stock_allocation_qs = (
        MaterialAllocation.objects
        .filter(
            requirement__customer_order_id=OuterRef("pk"),
            source=MaterialAllocation.Source.STOCK,
        )
    )

    purchase_allocation_qs = (
        MaterialAllocation.objects
        .filter(
            requirement__customer_order_id=OuterRef("pk"),
            source=MaterialAllocation.Source.PURCHASE,
        )
    )

    return (
        CustomerOrder.objects
        .select_related(
            "customer",
            "product",
            "created_by",
        )
        .annotate(
            has_requirement=Exists(
                requirement_qs
            ),
            has_stock_allocation=Exists(
                stock_allocation_qs
            ),
            has_purchase_allocation=Exists(
                purchase_allocation_qs
            ),
        )
        .order_by(
            "-year",
            "-number",
            "-id",
        )
    )


def apply_customer_order_filters(
    queryset,
    *,
    query=None,
    status=None,
    customer=None,
    year=None,
    material=None,
):
    """
    Nakłada filtry z list view.
    """

    query = (query or "").strip()

    if query:

        parsed_number = _parse_order_number(
            query
        )

        if parsed_number:

            number, parsed_year = parsed_number

            queryset = queryset.filter(
                number=number,
            )

            if parsed_year:
                queryset = queryset.filter(
                    year=parsed_year,
                )

        else:

            queryset = queryset.filter(
                Q(customer__name__icontains=query)
                |
                Q(product__name__icontains=query)
                |
                Q(notes__icontains=query)
            )

    if status:
        queryset = queryset.filter(
            status=status,
        )

    if customer:
        queryset = queryset.filter(
            customer_id=customer,
        )

    if year:
        queryset = queryset.filter(
            year=year,
        )

    if material == "missing":

        queryset = queryset.filter(
            has_requirement=False,
        )

    elif material == "pending":

        queryset = queryset.filter(
            has_requirement=True,
            has_stock_allocation=False,
            has_purchase_allocation=False,
        )

    elif material == "stock":

        queryset = queryset.filter(
            has_stock_allocation=True,
        )

    elif material == "purchase":

        queryset = queryset.filter(
            has_purchase_allocation=True,
        )

    return queryset


def get_filter_options():

    customer_ids = (
        CustomerOrder.objects
        .values_list(
            "customer_id",
            flat=True,
        )
        .distinct()
    )

    product_ids = (
        CustomerOrder.objects
        .values_list(
            "product_id",
            flat=True,
        )
        .exclude(
            product_id__isnull=True,
        )
        .distinct()
    )

    years = (
        CustomerOrder.objects
        .exclude(
            year__isnull=True,
        )
        .values_list(
            "year",
            flat=True,
        )
        .distinct()
        .order_by("-year")
    )

    return {
        "customers": (
            Buyer.objects
            .filter(
                id__in=customer_ids
            )
            .order_by("name")
        ),

        "products": (
            Product.objects
            .filter(
                id__in=product_ids
            )
            .order_by("name")
        ),

        "years": years,

        "statuses": (
            CustomerOrder.Status.choices
        ),
    }


def get_customer_order_list_context(
    request,
):

    filters = {
        "query": request.GET.get(
            "q",
            "",
        ).strip(),

        "status": request.GET.get(
            "status",
            "",
        ),

        "customer": request.GET.get(
            "customer",
            "",
        ),

        "year": request.GET.get(
            "year",
            "",
        ),

        "material": request.GET.get(
            "material",
            "",
        ),
    }

    queryset = (
        get_customer_orders_queryset()
    )

    queryset = apply_customer_order_filters(
        queryset,
        **filters,
    )

    # ========================================================
    # SUMMARY
    # ========================================================

    summary = {
        "total": queryset.count(),

        "without_requirement": (
            queryset
            .filter(
                has_requirement=False
            )
            .count()
        ),

        "stock": (
            queryset
            .filter(
                has_stock_allocation=True
            )
            .count()
        ),

        "purchase": (
            queryset
            .filter(
                has_purchase_allocation=True
            )
            .count()
        ),
    }

    # ========================================================
    # PAGINATION
    # ========================================================

    paginator = Paginator(
        queryset,
        PAGE_SIZE,
    )

    page_obj = paginator.get_page(
        request.GET.get(
            "page",
            1,
        )
    )

    query_params = request.GET.copy()

    if "page" in query_params:
        query_params.pop("page")

    return {
        "orders": page_obj.object_list,
        "page_obj": page_obj,
        "filters": filters,
        "filter_options": get_filter_options(),
        "summary": summary,
        "query_string": query_params.urlencode(),
    }