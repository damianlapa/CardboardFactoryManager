# warehouse/services/bom_preview.py
import math
from decimal import Decimal
from django.db.models import Sum
from django.core.exceptions import ValidationError

from warehouse.models import (
    WarehouseStock, StockSupply, StockSupplySettlement
)

def _supply_left(supply) -> int:
    used = (
        StockSupplySettlement.objects
        .filter(stock_supply=supply, as_result=False)
        .aggregate(total=Sum("quantity"))
        .get("total") or 0
    )
    left = int(supply.quantity) - int(used)
    return max(left, 0)

def bom_preview_for_order(order) -> dict:
    if not order.bom_id:
        raise ValidationError("To zlecenie nie ma przypisanego BOM.")

    bom = order.bom
    qty = order.order_quantity

    items = []
    ok_all = True

    for bp in bom.parts.select_related("part", "part__stock_type"):
        stock = bp.part
        unit = stock.stock_type.unit

        required_dec = bp.quantity * Decimal(qty)

        if unit in ("PIECE", "SET"):
            required = int(math.ceil(required_dec))
        else:
            raise ValidationError(f"Unit {unit} nieobsłużony przy rozchodzie BOM (masz stany int).")

        wh_total = (
            WarehouseStock.objects
            .filter(stock=stock)
            .aggregate(total=Sum("quantity"))
            .get("total") or 0
        )
        wh_total = int(wh_total)

        supplies = list(
            StockSupply.objects
            .filter(name=stock.name, used=False)
            .order_by("date", "id")
        )

        supply_rows = []
        supply_left_sum = 0
        for s in supplies:
            left = _supply_left(s)
            if left <= 0:
                continue
            supply_left_sum += left
            supply_rows.append({
                "id": s.id,
                "date": s.date.isoformat() if s.date else None,
                "qty_total": int(s.quantity),
                "qty_left": int(left),
                "value": str(s.value),
            })

        enough = (wh_total >= required) and (supply_left_sum >= required)
        if not enough:
            ok_all = False

        items.append({
            "stock_id": stock.id,
            "stock_name": stock.name,
            "unit": unit,
            "required": required,
            "warehouse_total": wh_total,
            "missing": max(required - wh_total, 0),
            "supplies_total_left": supply_left_sum,
            "supplies": supply_rows,
            "enough": enough,
        })

    return {
        "order_id": order.id,
        "bom_id": bom.id,
        "product": str(bom.product),
        "order_quantity": qty,
        "ok": ok_all,
        "items": items,
    }
