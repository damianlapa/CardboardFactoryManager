# warehouse/services/bom_preview.py
import math
from decimal import Decimal
from django.db.models import Sum
from django.core.exceptions import ValidationError

from warehouse.models import (
    WarehouseStock, StockSupply
)


def bom_preview_for_order(order) -> dict:
    """
    Preview BOM:
    - nic nie zapisuje
    - liczy wymagania na podstawie BOMPart.quantity * order.order_quantity
    - sprawdza dostępność w magazynach (WarehouseStock sum)
    - sprawdza dostępność w partiach FIFO (StockSupply.available_quantity) uwzględniając:
        * StockSupplySettlement(as_result=False) (zużycia do produkcji)
        * StockSupplySell (sprzedaże)
      oraz ignorując as_result=True jako "zużycie" (to tylko informacja o pochodzeniu partii).
    """
    if not order.bom_id:
        raise ValidationError("To zlecenie nie ma przypisanego BOM.")

    bom = order.bom
    qty = int(order.order_quantity or 0)

    if qty <= 0:
        raise ValidationError("Zlecenie ma niepoprawną ilość (order_quantity).")

    items = []
    ok_all = True

    for bp in bom.parts.select_related("part", "part__stock_type"):
        stock = bp.part  # Stock
        unit = stock.stock_type.unit

        required_dec = (bp.quantity or Decimal("0")) * Decimal(qty)

        if unit in ("PIECE", "SET"):
            required = int(math.ceil(required_dec))
        else:
            raise ValidationError(
                f"Unit {unit} nieobsłużony przy rozchodzie BOM (masz stany int)."
            )

        # suma stanów magazynowych (agregat fizyczny)
        wh_total = (
            WarehouseStock.objects
            .filter(stock=stock)
            .aggregate(total=Sum("quantity"))
            .get("total") or 0
        )
        wh_total = int(wh_total)

        # partie FIFO dla tego stocka:
        # kluczowe: filtr po (name + stock_type), NIE po used=False
        supplies = (
            StockSupply.objects
            .filter(name=stock.name, stock_type=stock.stock_type)
            .order_by("date", "id")
        )

        supply_rows = []
        supply_left_sum = 0

        for s in supplies:
            left = int(s.available_quantity())  # ✅ uwzględnia sells + settlement(as_result=False)
            if left <= 0:
                continue

            supply_left_sum += left
            supply_rows.append({
                "id": s.id,
                "date": s.date.isoformat() if s.date else None,
                "qty_total": int(s.quantity or 0),
                "qty_left": left,
                "value": str(s.value),
            })

        # spójność: magazyn i partie muszą pokrywać requirement
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
