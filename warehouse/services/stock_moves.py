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

    Przy pełnym rebuildzie (from_date=None) startuje od
    quantity_before pierwszego wpisu historii (realny opening).
    """
    from warehouse.models import WarehouseStock, WarehouseStockHistory  # local import

    ws_locked = WarehouseStock.objects.select_for_update().get(pk=ws.pk)

    if from_date is None:
        # pełny rebuild od początku – respektuj realny opening
        rows = list(
            WarehouseStockHistory.objects
            .select_for_update()
            .filter(warehouse_stock=ws_locked)
            .order_by("date", "id")
        )

        if not rows:
            return

        # 🔥 kluczowa zmiana:
        running = int(rows[0].quantity_before or 0)

    else:
        # stan wejściowy = ostatni quantity_after przed from_date
        prev = (
            WarehouseStockHistory.objects
            .filter(warehouse_stock=ws_locked, date__lt=from_date)
            .order_by("-date", "-id")
            .first()
        )
        running = int(prev.quantity_after) if prev else 0

        rows = list(
            WarehouseStockHistory.objects
            .select_for_update()
            .filter(warehouse_stock=ws_locked, date__gte=from_date)
            .order_by("date", "id")
        )

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
    ws_locked.quantity = int(running)
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
    Jedyny legalny sposób zmiany WS.

    Zabezpieczenie:
    - po każdym backdate (date <= ostatnia data w historii) robimy rebuild od tej daty
    - rebuild nie może zejść poniżej 0; jeśli zejdzie -> ValueError -> rollback
    """
    from warehouse.models import WarehouseStock, WarehouseStockHistory  # local import

    if delta == 0:
        return MoveResult(before=int(ws.quantity), after=int(ws.quantity))

    date = date or timezone.now().date()

    ws_locked = WarehouseStock.objects.select_for_update().get(pk=ws.pk)

    # Ostatni wpis historii (po dacie)
    last = (
        WarehouseStockHistory.objects
        .filter(warehouse_stock=ws_locked)
        .order_by("-date", "-id")
        .first()
    )
    last_date = last.date if last else None

    # Wylicz "stan na tę datę" jako ostatni quantity_after przed ruchem:
    # (nie jako ws.quantity "teraz")
    prev = (
        WarehouseStockHistory.objects
        .filter(warehouse_stock=ws_locked, date__lte=date)
        .order_by("-date", "-id")
        .first()
    )
    before_at_date = int(prev.quantity_after) if prev else 0

    # Szybki check (lokalnie na tej dacie)
    after_at_date = before_at_date + int(delta)
    if after_at_date < 0:
        raise ValueError(
            f"Brak stanu na dzień {date}: before={before_at_date} + delta={delta} -> {after_at_date} (WS id={ws_locked.id})"
        )

    # Zapis historii – before/after ustawiamy "tymczasowo" wg stanu na dacie
    h = WarehouseStockHistory.objects.create(
        warehouse_stock=ws_locked,
        stock_supply=stock_supply,
        order_settlement=order_settlement,
        assembly=assembly,
        delta=int(delta),
        quantity_before=before_at_date,
        quantity_after=after_at_date,
        date=date,
        sell=sell,
    )

    # Jeśli wpisaliśmy w przeszłość albo w ten sam dzień co ostatnia historia:
    # MUSIMY przebudować historię od tej daty, aby zachować spójność (date,id)
    must_rebuild = (last_date is not None and date <= last_date)

    if must_rebuild:
        # To jest kluczowe zabezpieczenie: rebuild wykryje minus w przyszłych wpisach
        rebuild_ws_history_from_date(ws=ws_locked, from_date=date)

        # Po rebuildzie "before/after" mogły się zmienić, więc odczytaj z DB
        h.refresh_from_db(fields=["quantity_before", "quantity_after"])
        return MoveResult(before=int(h.quantity_before), after=int(h.quantity_after))

    # Jeśli to dopisanie na końcu osi czasu, możemy tylko zsynchronizować ws.quantity "teraz"
    # (nie jest to krytyczne dla walidacji historycznej, ale trzyma spójność)
    ws_locked.quantity = int(after_at_date)
    ws_locked.save(update_fields=["quantity"])

    return MoveResult(before=int(before_at_date), after=int(after_at_date))

