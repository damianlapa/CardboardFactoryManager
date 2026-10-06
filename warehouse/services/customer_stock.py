from django.db.models import Sum

from orders.models import CardboardOrderItem
from warehouse.models import (
    CustomerStockList,
    CustomerStockItem,
    WarehouseStock,
    Order,
)

from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404


def add_customer_stock_item(*, stock_list, warehouse_stock_id, minimum_quantity):
    try:
        minimum_quantity = int(minimum_quantity)
    except (TypeError, ValueError):
        raise ValidationError("Minimalna ilość musi być liczbą.")

    if minimum_quantity < 0:
        raise ValidationError("Minimalna ilość nie może być ujemna.")

    warehouse_stock = WarehouseStock.objects.get(
        pk=warehouse_stock_id
    )

    item, created = CustomerStockItem.objects.get_or_create(
        stock_list=stock_list,
        warehouse_stock=warehouse_stock,
        defaults={
            "minimum_quantity": minimum_quantity,
        },
    )

    if not created:
        raise ValidationError(
            "Ten stan magazynowy jest już na Twojej liście."
        )

    return item


def get_customer_stock_context(user):
    stock_list, _ = CustomerStockList.objects.get_or_create(
        user=user
    )

    items = (
        stock_list.items
        .select_related(
            "warehouse_stock",
            "warehouse_stock__warehouse",
            "warehouse_stock__stock",
            "warehouse_stock__stock__stock_type",
        )
        .order_by(
            "warehouse_stock__stock__name",
        )
    )

    total = items.count()

    below_minimum = 0
    shortage = 0

    stock_names = list(
        items.values_list(
            "warehouse_stock__stock__name",
            flat=True,
        )
    )

    ordered_by_product = {
        row["requirement__customer_order__product__name"]: row["total"] or 0
        for row in (
            CardboardOrderItem.objects
            .filter(
                requirement__customer_order__product__name__in=stock_names,
            )
            .values(
                "requirement__customer_order__product__name"
            )
            .annotate(
                total=Sum("quantity")
            )
        )
    }

    delivered_by_product = {
        row["product__name"]: row["total"] or 0
        for row in (
            Order.objects
            .filter(
                product__name__in=stock_names,
            )
            .values(
                "product__name"
            )
            .annotate(
                total=Sum("delivered_quantity")
            )
        )
    }

    for item in items:
        if item.below_minimum:
            below_minimum += 1
            shortage += item.shortage

        product_name = item.warehouse_stock.stock.name

        item.ordered_quantity = ordered_by_product.get(
            product_name,
            0,
        )

        item.delivered_quantity = delivered_by_product.get(
            product_name,
            0,
        )

    available_stocks = (
        WarehouseStock.objects
        .select_related(
            "stock",
            "stock__stock_type",
            "warehouse",
        )
        .exclude(
            customer_stock_items__stock_list=stock_list
        )
        .order_by(
            "warehouse__name",
            "stock__name",
        )
    )

    return {
        "stock_list": stock_list,
        "items": items,
        "summary": {
            "total": total,
            "below_minimum": below_minimum,
            "shortage": shortage,
        },
        "available_stocks": available_stocks,
    }


def update_customer_stock_item(
    *,
    stock_list,
    item_id,
    minimum_quantity,
):
    item = get_object_or_404(
        CustomerStockItem,
        pk=item_id,
        stock_list=stock_list,
    )

    try:
        minimum_quantity = int(minimum_quantity)
    except (TypeError, ValueError):
        raise ValidationError(
            "Minimalna ilość musi być liczbą."
        )

    if minimum_quantity < 0:
        raise ValidationError(
            "Minimalna ilość nie może być ujemna."
        )

    item.minimum_quantity = minimum_quantity
    item.save(
        update_fields=["minimum_quantity"]
    )

    return item


def delete_customer_stock_item(
    *,
    stock_list,
    item_id,
):
    item = get_object_or_404(
        CustomerStockItem,
        pk=item_id,
        stock_list=stock_list,
    )

    item.delete()