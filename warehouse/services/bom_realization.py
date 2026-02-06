# warehouse/services/bom_realization.py
import datetime
from django.db import transaction
from django.core.exceptions import ValidationError
from django.db.models import Sum
from decimal import Decimal

from warehouse.models import (
    Warehouse,
    WarehouseStock,
    WarehouseStockHistory,
    OrderSettlement,
    StockSupply,
    StockSupplySettlement,
    StockType,
    Stock,
)

MAIN_WAREHOUSE_NAME = "MAGAZYN GŁÓWNY"
from decimal import Decimal

FG_WAREHOUSE_NAME = "MAGAZYN WYROBÓW GOTOWYCH"

def _receipt_finished_good(*, order, product, quantity: int, receipt_date, value: Decimal):
    """
    Przyjęcie gotowca:
    - tworzy StockSupply (value = suma kosztów materiałów)
    - zwiększa WarehouseStock + history
    - tworzy OrderSettlement 'wynikowy'
    - tworzy StockSupplySettlement z as_result=True
    """
    fg_wh = Warehouse.objects.get(name=FG_WAREHOUSE_NAME)

    st, _ = StockType.objects.get_or_create(stock_type="product", unit="PIECE")

    stock, created = Stock.objects.get_or_create(
        name=product.name,
        defaults={"stock_type": st, "quantity": 0},
    )
    if not created and stock.stock_type_id != st.id:
        raise ValidationError(
            f"Stock dla gotowca '{stock.name}' ma inny StockType ({stock.stock_type}) niż Box[PIECE]."
        )

    ws, _ = WarehouseStock.objects.get_or_create(warehouse=fg_wh, stock=stock)

    value = (value or Decimal("0.00")).quantize(Decimal("0.01"))

    # StockSupply = przyjęcie gotowca z wartością = koszt materiałów
    supply = StockSupply.objects.create(
        stock_type=st,
        delivery_item=None,
        dimensions=None,
        date=receipt_date,
        quantity=quantity,
        name=stock.name,
        used=False,
        value=value,
    )

    before = ws.quantity
    ws.increase_quantity(quantity)
    after = ws.quantity

    WarehouseStockHistory.objects.create(
        warehouse_stock=ws,
        stock_supply=supply,
        quantity_before=before,
        quantity_after=after,
        date=receipt_date,
    )

    # Settlement "wynikowy" (żeby mieć do czego podpiąć StockSupplySettlement as_result=True)
    result_settlement = OrderSettlement.objects.create(
        order=order,
        material=ws,
        material_quantity=quantity,
        settlement_date=receipt_date,
    )

    # as_result=True — ślad, że to jest wynik realizacji (wartość policzy się z supply.value)
    StockSupplySettlement.objects.create(
        stock_supply=supply,
        settlement=result_settlement,
        quantity=quantity,
        as_result=True,
    )

    return supply, ws, result_settlement




def _fifo_consume_stock_supply(*, stock_name: str, stock_type: StockType, quantity: int, settlement: OrderSettlement) -> Decimal:
    supplies = list(
        StockSupply.objects
        .select_for_update()
        .filter(name=stock_name, stock_type=stock_type)  # ✅ nie mieszamy typów
        .order_by("date", "id")
    )

    if not supplies:
        raise ValidationError(f"Brak dostaw (StockSupply) dla: {stock_name}")

    def supply_left(s: StockSupply) -> int:
        # ✅ uwzględnia: settlementy as_result=False + sprzedaże
        return int(s.available_quantity())

    qty_left = int(quantity)
    consumed_value = Decimal("0.00")

    for s in supplies:
        left = supply_left(s)
        if left <= 0:
            s.refresh_used_flag()
            continue
        ...
        s.refresh_used_flag()

        take = min(left, qty_left)

        sss = StockSupplySettlement.objects.create(
            stock_supply=s,
            settlement=settlement,
            quantity=take,
            as_result=False,
        )
        # value jest ustawiane w save() -> po create() już jest
        consumed_value += (sss.value or Decimal("0.00"))

        qty_left -= take

        s.refresh_used_flag()

        if qty_left == 0:
            return consumed_value

    raise ValidationError(f"Brak wystarczającej ilości dostaw dla: {stock_name} (brakuje {qty_left})")


def _warehouse_ordering_key(ws: WarehouseStock):
    """
    Najpierw MAGAZYN GŁÓWNY, potem reszta alfabetycznie.
    """
    return (0 if ws.warehouse.name == MAIN_WAREHOUSE_NAME else 1, ws.warehouse.name)


@transaction.atomic
def realize_order_bom(
    *,
    order,
    settlement_date=None,
):
    """
    Realizuje BOM przypięty do orderu (order.bom):
    - szuka stanów na WSZYSTKICH magazynach
    - zdejmuje najpierw z MAGAZYN GŁÓWNY, potem z innych
    - tworzy OrderSettlement + WarehouseStockHistory per magazyn (per "kawałek" rozchodu)
    - rozksięgowuje FIFO przez StockSupplySettlement

    Uwaga: powstanie kilka settlementów na ten sam materiał, jeśli rozchód idzie z wielu magazynów.
    """
    total_material_value = Decimal("0.00")
    if not order.bom_id:
        raise ValidationError("To zlecenie nie ma przypisanego BOM.")

    bom = order.bom

    # twarda spójność: BOM musi pasować do produktu
    if order.product_id and bom.product_id != order.product_id:
        raise ValidationError("BOM nie pasuje do produktu zlecenia.")

    # guard: nie wykonuj 2x (najprościej)
    if OrderSettlement.objects.filter(order=order).exists():
        raise ValidationError("To zlecenie jest już rozliczone / zrealizowane (są settlementy).")

    if settlement_date is None:
        settlement_date = datetime.date.today()

    # policz wymagania (Stock, Decimal)
    reqs = bom.requirements(order.order_quantity)

    # przejdziemy po każdym składniku BOM
    created_settlements = []

    for stock, required_dec in reqs:
        required = bom.to_int_qty(stock, required_dec)  # int, wg Twoich unitów

        # pobierz WS z wszystkich magazynów i zablokuj
        ws_qs = (
            WarehouseStock.objects
            .select_for_update()
            .select_related("warehouse", "stock")
            .filter(stock=stock, quantity__gt=0)
        )
        ws_list = list(ws_qs)
        ws_list.sort(key=_warehouse_ordering_key)

        if not ws_list:
            raise ValidationError(f"Brak materiału na magazynach: {stock.name}")

        total_available = sum(ws.quantity for ws in ws_list)
        if total_available < required:
            raise ValidationError(
                f"Brak materiału: {stock.name}. Potrzeba {required}, jest {total_available} (wszystkie magazyny)."
            )

        qty_left = required

        for ws in ws_list:
            if qty_left <= 0:
                break

            take = min(ws.quantity, qty_left)
            if take <= 0:
                continue

            before = ws.quantity
            ws.decrease_quantity(take)  # zapisuje
            after = ws.quantity

            # settlement odnosi się do konkretnego WS (magazyn + stock)
            settlement = OrderSettlement.objects.create(
                order=order,
                material=ws,
                material_quantity=take,
                settlement_date=settlement_date,
            )

            WarehouseStockHistory.objects.create(
                warehouse_stock=ws,
                order_settlement=settlement,
                quantity_before=before,
                quantity_after=after,
                date=settlement_date,
            )

            # FIFO kosztowe po StockSupply (globalnie po nazwie materiału)
            total_material_value += _fifo_consume_stock_supply(
                stock_name=ws.stock.name,
                stock_type=ws.stock.stock_type,  # ✅ kluczowe
                quantity=take,
                settlement=settlement
            )

            created_settlements.append(settlement)
            qty_left -= take

        if qty_left != 0:
            # teoretycznie nie powinno się zdarzyć przez walidację total_available
            raise ValidationError(f"Nie udało się w pełni zrealizować materiału {stock.name} (brakuje {qty_left}).")

        _receipt_finished_good(
            order=order,
            product=bom.product,
            quantity=order.order_quantity,
            receipt_date=settlement_date,
            value=total_material_value,
        )

    return created_settlements
