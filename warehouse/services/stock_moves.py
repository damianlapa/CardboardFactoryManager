# warehouse/services/stock_moves.py
from django.db import transaction
from django.utils import timezone
from warehouse.models import WarehouseStock, WarehouseStockHistory

@transaction.atomic
def move_ws(*, ws: WarehouseStock, delta: int, date=None,
            stock_supply=None, order_settlement=None, assembly=None, sell=None):
    """
    Jedyny legalny sposób zmiany ws.quantity:
    - delta > 0 przyjęcie
    - delta < 0 rozchód
    """
    date = date or timezone.now().date()

    ws_locked = WarehouseStock.objects.select_for_update().get(pk=ws.pk)

    before = ws_locked.quantity
    after = before + int(delta)

    ws_locked.quantity = after
    ws_locked.save(update_fields=["quantity"])

    WarehouseStockHistory.objects.create(
        warehouse_stock=ws_locked,
        date=date,
        quantity_before=before,
        quantity_after=after,
        stock_supply=stock_supply,
        order_settlement=order_settlement,
        assembly=assembly,
        sell=sell,
    )
    return ws_locked
