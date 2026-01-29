# warehouse/services/stock_moves.py
from __future__ import annotations

from dataclasses import dataclass
from django.db import transaction
from django.utils import timezone


@dataclass(frozen=True)
class MoveResult:
    before: int
    after: int


@transaction.atomic
def move_ws(
    *,
    ws,
    delta: int,
    date=None,
    stock_supply=None,
    order_settlement=None,
    assembly=None,
    sell=None,
) -> MoveResult:
    """
    Jedyny legalny sposób zmiany ws.quantity.
    Zawsze:
    - blokuje rekord (select_for_update)
    - aktualizuje WarehouseStock.quantity
    - dopisuje WarehouseStockHistory
    """
    from warehouse.models import WarehouseStock, WarehouseStockHistory  # import lokalny = brak circular

    if delta == 0:
        # nic nie rób, ale też nie twórz historii "0"
        return MoveResult(before=int(ws.quantity), after=int(ws.quantity))

    date = date or timezone.now().date()

    ws_locked = (
        WarehouseStock.objects
        .select_for_update()
        .get(pk=ws.pk)
    )

    before = int(ws_locked.quantity)
    after = before + int(delta)

    if after < 0:
        raise ValueError(f"WarehouseStock id={ws_locked.id} would go negative: {before} + ({delta}) = {after}")

    ws_locked.quantity = after
    ws_locked.save(update_fields=["quantity"])

    WarehouseStockHistory.objects.create(
        warehouse_stock=ws_locked,
        stock_supply=stock_supply,
        order_settlement=order_settlement,
        assembly=assembly,
        quantity_before=before,
        quantity_after=after,
        date=date,
        sell=sell,
    )

    return MoveResult(before=before, after=after)
