# warehouse/services/stock_moves.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from django.db import transaction
from django.utils import timezone


@dataclass(frozen=True)
class MoveResult:
    before: int
    after: int


@transaction.atomic
def rebuild_ws_history_from_date(*, ws, from_date=None) -> None:
    """
    Przelicza quantity_before/after dla WS historii od from_date do końca,
    używając pola delta.

    Działa poprawnie nawet gdy wpisy były dopisywane "wstecz" datą.
    """
    from warehouse.models import WarehouseStock, WarehouseStockHistory  # local import

    ws_locked = WarehouseStock.objects.select_for_update().get(pk=ws.pk)

    if from_date is None:
        # pełny rebuild od początku
        prev_running = 0
        qs = (
            WarehouseStockHistory.objects
            .select_for_update()
            .filter(warehouse_stock=ws_locked)
            .order_by("date", "id")
        )
    else:
        # stan wejściowy = ostatni quantity_after przed from_date
        prev = (
            WarehouseStockHistory.objects
            .filter(warehouse_stock=ws_locked, date__lt=from_date)
            .order_by("-date", "-id")
            .first()
        )
        prev_running = int(prev.quantity_after) if prev else 0

        qs = (
            WarehouseStockHistory.objects
            .select_for_update()
            .filter(warehouse_stock=ws_locked, date__gte=from_date)
            .order_by("date", "id")
        )

    rows = list(qs)
    running = prev_running

    for h in rows:
        h.quantity_before = running
        after = running + int(h.delta)
        if after < 0:
            raise ValueError(
                f"History rebuild would go negative: WS id={ws_locked.id}, "
                f"date={h.date}, running={running}, delta={h.delta}"
            )
        h.quantity_after = after
        running = after

    if rows:
        WarehouseStockHistory.objects.bulk_update(rows, ["quantity_before", "quantity_after"])

    # zsynchronizuj agregat WS.quantity z końcem historii
    ws_locked.quantity = max(0, int(running))
    ws_locked.save(update_fields=["quantity"])


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
    - dopisuje WarehouseStockHistory (z delta!)
    - jeśli dopisujemy "wstecz" datą -> rebuild historii od tej daty
    """
    from warehouse.models import WarehouseStock, WarehouseStockHistory  # import lokalny = brak circular

    if delta == 0:
        return MoveResult(before=int(ws.quantity), after=int(ws.quantity))

    date = date or timezone.now().date()

    ws_locked = WarehouseStock.objects.select_for_update().get(pk=ws.pk)

    # sprawdź czy dopisujemy "wstecz"
    last = (
        WarehouseStockHistory.objects
        .filter(warehouse_stock=ws_locked)
        .order_by("-date", "-id")
        .first()
    )
    max_date = last.date if last else None

    before = int(ws_locked.quantity)
    after = before + int(delta)
    if after < 0:
        raise ValueError(f"WarehouseStock id={ws_locked.id} would go negative: {before} + ({delta}) = {after}")

    # aktualizuj agregat (na chwilę). Jeśli robimy rebuild, to i tak zsynchronizujemy końcówkę.
    ws_locked.quantity = after
    ws_locked.save(update_fields=["quantity"])

    # zapis historii z delta
    h = WarehouseStockHistory.objects.create(
        warehouse_stock=ws_locked,
        stock_supply=stock_supply,
        order_settlement=order_settlement,
        assembly=assembly,
        delta=int(delta),
        quantity_before=before,   # wstępnie (może zostać przeliczone)
        quantity_after=after,     # wstępnie (może zostać przeliczone)
        date=date,
        sell=sell,
    )

    # jeśli data jest wcześniejsza niż max_date, trzeba przeliczyć łańcuch od tej daty
    if max_date is not None and date < max_date:
        rebuild_ws_history_from_date(ws=ws_locked, from_date=date)

    return MoveResult(before=before, after=after)
