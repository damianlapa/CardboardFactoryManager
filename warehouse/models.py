import datetime
import math
import re
from django.db.models import F, Q
from warehousemanager.models import Buyer
from django.db.models import Exists, OuterRef
from django.db.models import Sum
from decimal import Decimal, ROUND_HALF_UP
from utils.money import money, D, money_sum
from django.db import models, transaction
from django.core.exceptions import ValidationError
from django.db.models.functions import Coalesce
from warehouse.services.stock_moves import move_ws
import logging
logger = logging.getLogger(__name__)
from warehouse.services.naming import *


UNITS = (
    ('KG', 'KG'),
    ('M2', 'M2'),
    ('PIECE', 'PIECE'),
    ('SET', 'SET')
)


class Palette(models.Model):
    name = models.CharField(max_length=32)

    def __str__(self):
        return f'{self.name}'


class Provider(models.Model):
    name = models.CharField(max_length=64)
    shortcut = models.CharField(max_length=24, null=True, blank=True)

    def __str__(self):
        return f'{self.name}'


class Product(models.Model):
    name = models.CharField(max_length=128, unique=True)
    price = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    dimensions = models.CharField(max_length=32, null=True, blank=True)
    flute = models.CharField(max_length=8, null=True, blank=True)
    gsm = models.PositiveIntegerField(default=0)

    def clean(self):
        if self.name:
            self.name = norm_names(self.name)
        if self.dimensions:
            self.dimensions = norm_dimensions(self.dimensions)
        if self.flute:
            self.flute = norm_spaces(self.flute).upper()
        return super().clean()

    def save(self, *args, **kwargs):
        # zabezpieczenie nawet jak ktoś nie woła full_clean()
        if self.name:
            self.name = norm_names(self.name)
        if self.dimensions:
            self.dimensions = norm_dimensions(self.dimensions)
        if self.flute:
            self.flute = norm_spaces(self.flute).upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.name}'

    class Meta:
        ordering = ['name']


class Order(models.Model):
    customer = models.ForeignKey(Buyer, on_delete=models.PROTECT)
    provider = models.ForeignKey(Provider, on_delete=models.PROTECT)
    order_id = models.CharField(max_length=32, unique=False)
    customer_date = models.DateField()
    order_date = models.DateField(null=True, blank=True)
    order_year = models.CharField(max_length=4, null=True, blank=True)
    delivery_date = models.DateField(null=True, blank=True)
    production_date = models.DateField(null=True, blank=True)
    dimensions = models.CharField(max_length=32)
    name = models.CharField(max_length=32)
    weight = models.PositiveIntegerField(default=0)
    default_pieces = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("1.00"))
    order_quantity = models.PositiveIntegerField()
    delivered_quantity = models.PositiveIntegerField(default=0)
    price = models.PositiveIntegerField(default=0)
    product = models.ForeignKey(Product, null=True, blank=True, on_delete=models.PROTECT)
    delivered = models.BooleanField(default=False)
    finished = models.BooleanField(default=False)
    updated = models.BooleanField(default=False)
    bom = models.ForeignKey("BOM", on_delete=models.PROTECT, null=True, blank=True, related_name="orders")

    def __str__(self):
        return f'{self.provider} {self.order_id} {self.name}'

    def total_sales(self):
        sells = (
            ProductSell3.objects
            .filter(Q(order=self) | Q(order_parts__order=self))
            .distinct()
        )
        return money_sum(s.calculate_value() for s in sells)

    def material_cost(self):
        orders_from = OrderToOrderShift.objects.filter(order_from=self)
        orders_to = OrderToOrderShift.objects.filter(order_to=self)
        items = DeliveryItem.objects.filter(order=self)
        cost = Decimal('0.00')

        for i in items:
            value = i.calculate_value() if i.calculate_value() is not None else Decimal('0')
            cost += value

        for of in orders_from:
            cost -= Decimal(of.get_value())

        for ot in orders_to:
            cost += Decimal(ot.get_value())

        return cost.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def production_cost(self):
        from production.models import ProductionOrder
        production_order = ProductionOrder.objects.filter(id_number=f'{self.provider} {self.order_id}').first()
        if production_order:
            return production_order.work_energy_usage_cost()
        else:
            return Decimal('0.00'), Decimal('0.00'), Decimal('0.00')

    def other_costs(self):
        month, year = self.order_date.month, self.order_date.year
        month_results = MonthResults.objects.get(month=month, year=year)

        value = D(self.material_cost())
        expenses = D(month_results.expenses)

        if expenses == 0:
            return money(0), money(0), money(0), money(0)

        factor = value / expenses

        financial = money(D(month_results.financial_expenses) * factor)
        management = money(D(month_results.management_expenses) * factor)
        logistic = money(D(month_results.logistic_expenses) * factor)
        other = money(D(month_results.other_expenses) * factor)

        return financial, management, logistic, other

    def total_area(self):
        items = DeliveryItem.objects.filter(order=self)
        total = 0

        for item in items:
            area = item.calculate_area()
            total += area

        return int(round(total, 0))

    def check_if_settled(self):
        settlements = OrderSettlement.objects.filter(order=self)
        sales = ProductSell3.objects.filter(order=self)

        if settlements and sales:
            pieces = 0
            sold = 0
            history = WarehouseStockHistory.objects.filter(order_settlement__in=settlements, stock_supply__isnull=False)
            for h in history:
                pieces += (h.quantity_after - h.quantity_before)

            for s in sales:
                sold += s.quantity

            if pieces and sold and pieces == sold:
                return True
        return False

    def check_material_usage(self):
        settlements = OrderSettlement.objects.filter(order=self)
        for s in settlements:
            print(s)

    class Meta:
        ordering = ['order_date', 'provider', 'order_id']
        unique_together = ('provider', 'order_id', 'order_year')


class OrderToOrderShift(models.Model):
    date = models.DateField()
    order_from = models.ForeignKey(Order, related_name='shifts_from', on_delete=models.PROTECT)
    order_to = models.ForeignKey(Order, related_name='shifts_to', on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()

    def __str__(self):
        return f'{self.order_from.order_id} -> {self.order_to.order_id} :: {self.quantity}'

    def get_value(self):
        items = DeliveryItem.objects.filter(order=self.order_from)
        if not items:
            return money(0)
        one_piece_value = items[0].calculate_piece_value()
        return money(D(one_piece_value) * D(self.quantity))

    def get_items(self):
        items = []

        s_items = DeliveryItem.objects.filter(order=self.order_from)
        if s_items:
            items.append(s_items[0])

        stock_supplies = StockSupply.objects.filter(delivery_item__in=items)
        stock_materials = []
        for stock_supply in stock_supplies:
            try:
                stock = Stock.objects.get(name=stock_supply.name)
                warehouse_stock = WarehouseStock.objects.get(stock=stock)
                if warehouse_stock not in stock_materials:
                    stock_materials.append(warehouse_stock)

            except Exception as e:
                pass

        return stock_materials


class Delivery(models.Model):
    number = models.CharField(max_length=64, unique=True)
    provider = models.ForeignKey(Provider, on_delete=models.PROTECT)
    date = models.DateField()
    car_number = models.CharField(max_length=16, null=True, blank=True)
    telephone = models.CharField(max_length=16, null=True, blank=True)
    description = models.CharField(max_length=256, null=True, blank=True)
    palettes = models.ManyToManyField(Palette, through='DeliveryPalette', blank=True)
    processed = models.BooleanField(default=False)
    updated = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.provider}({self.car_number}) {self.date}'

    class Meta:
        ordering = ['-date', 'id']

    def add_to_warehouse(self, warehouse=None):
        if not warehouse:
            warehouse = Warehouse.objects.get(name='MAGAZYN GŁÓWNY')

        with transaction.atomic():
            # blokujemy elementy dostawy, żeby nikt nie przetwarzał równolegle
            items = (
                DeliveryItem.objects
                .select_for_update()
                .filter(delivery=self)
                .select_related("order", "delivery", "delivery__provider")
            )

            for item in items:
                if not item.processed:
                    item.add_to_warehouse(warehouse=warehouse)

            # ustaw processed tylko gdy wszystkie itemy processed
            if not DeliveryItem.objects.filter(delivery=self, processed=False).exists():
                self.processed = True
                self.save(update_fields=["processed"])

    def check_if_processed(self):
        items = DeliveryItem.objects.filter(delivery=self)
        for item in items:
            if not item.processed:
                return False
        return True

    def count_area(self):
        items = DeliveryItem.objects.filter(delivery=self)
        total = 0

        for item in items:
            area = item.calculate_area()
            total += area

        return total

    def all_settle(self):
        items = DeliveryItem.objects.filter(delivery=self)
        return all([i.check_settlement() for i in items])


class DeliveryItem(models.Model):
    delivery = models.ForeignKey(Delivery, on_delete=models.PROTECT)
    order = models.ForeignKey(Order, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=0)
    palettes_quantity = models.CharField(max_length=256, blank=True, null=True)
    processed = models.BooleanField(default=False)
    updated = models.BooleanField(default=False)

    # NEW (wariant B)
    provider_sku = models.CharField(max_length=128, null=True, blank=True)  # auto z order.name
    stock = models.ForeignKey("Stock", null=True, blank=True, on_delete=models.PROTECT)  # superstock snapshot

    def save(self, *args, **kwargs):
        # automatycznie zapisz kod dostawcy z order.name
        if self.order_id and not self.provider_sku:
            self.provider_sku = (self.order.name or "").strip()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.delivery} :: {self.order}'

    def add_to_warehouse(self, warehouse=None, quantity=False):
        if not warehouse:
            warehouse = Warehouse.objects.get(name='MAGAZYN GŁÓWNY')

        quantity_to_add = int(self.quantity if not quantity else quantity)
        if quantity_to_add <= 0:
            raise ValidationError("Ilość przyjęcia musi być > 0")

        with transaction.atomic():
            # blokujemy item, żeby nie przyjąć drugi raz równolegle
            item = DeliveryItem.objects.select_for_update().select_related(
                "delivery", "delivery__provider", "order"
            ).get(pk=self.pk)

            if item.processed:
                # idempotencja: drugi raz nic nie robi
                return

            # blokujemy order (bo aktualizujemy delivered_quantity)
            order = Order.objects.select_for_update().get(pk=item.order_id)

            if not warehouse:
                warehouse = Warehouse.objects.get(name='MAGAZYN GŁÓWNY')

            # 1) superstock
            target_stock = self.resolve_superstock()
            if not self.stock_id:
                self.stock = target_stock
                self.save(update_fields=["stock"])

            # 2) StockSupply (1:1 z DeliveryItem)
            material_type = StockType.objects.get(stock_type='material', unit='PIECE')

            stock_supply, created = StockSupply.objects.get_or_create(
                delivery_item=item,
                defaults=dict(
                    stock_type=material_type,
                    date=item.delivery.date,
                    dimensions=order.dimensions,
                    quantity=quantity_to_add,
                    name=target_stock.name,
                    value=item.calculate_value(),
                    used=False,
                )
            )

            # jeśli supply istnieje, a quantity/value/date odbiegają -> aktualizujemy (spójność)
            updates = {}
            if stock_supply.stock_type_id != material_type.id:
                updates["stock_type"] = material_type
            if stock_supply.date != item.delivery.date:
                updates["date"] = item.delivery.date
            if stock_supply.dimensions != order.dimensions:
                updates["dimensions"] = order.dimensions
            if stock_supply.name != target_stock.name:
                updates["name"] = target_stock.name
            if int(stock_supply.quantity) != int(quantity_to_add):
                updates["quantity"] = quantity_to_add
            new_value = item.calculate_value()
            if stock_supply.value != new_value:
                updates["value"] = new_value

            if updates:
                for k, v in updates.items():
                    setattr(stock_supply, k, v)
                stock_supply.save(update_fields=list(updates.keys()))

            # 3) WarehouseStock (agregat) – blokujemy, potem ruch tylko przez move_ws
            ws, _ = WarehouseStock.objects.get_or_create(
                warehouse=warehouse,
                stock=target_stock
            )
            ws = WarehouseStock.objects.select_for_update().get(pk=ws.pk)

            # ruch magazynowy (to ma tworzyć historię i aktualizować ilość)
            move_ws(
                ws=ws,
                delta=quantity_to_add,
                date=item.delivery.date,
                stock_supply=stock_supply,
            )

            # 4) order delivered_quantity
            order.delivered_quantity = int(order.delivered_quantity) + quantity_to_add
            if order.order_quantity and order.delivered_quantity / order.order_quantity > 0.92 and not order.delivered:
                order.delivered = True
                order.delivery_date = item.delivery.date
            order.save(update_fields=["delivered_quantity", "delivered", "delivery_date"])

            # 5) processed
            item.processed = True
            item.save(update_fields=["processed"])

    def resolve_superstock(self) -> "Stock":
        material_type = StockType.objects.get(stock_type='material', unit='PIECE')

        # jeśli już wcześniej przypięte — nie zmieniaj
        if self.stock_id:
            return self.stock

        sku = (self.provider_sku or "").strip() or (self.order.name or "").strip()
        dims = (self.order.dimensions or "").strip()

        alias = StockAlias.objects.filter(
            provider=self.delivery.provider,
            provider_sku=sku,
            dimensions=dims,
            is_active=True
        ).select_related("stock").first()

        if alias:
            return alias.stock

        # BRAK ALIASU -> TWORZYMY STOCK UNIKALNY (dla 90% przypadków)
        provider_tag = (self.delivery.provider.shortcut or self.delivery.provider.name or "").strip()
        base_name = f"{provider_tag} {sku}[{dims}]".strip()

        # Stock.name ma max_length=64 -> przytnij bezpiecznie
        name = base_name[:64]

        stock, _ = Stock.objects.get_or_create(
            name=name,
            stock_type=material_type
        )
        return stock

    def check_settlement(self):
        settlement = OrderSettlement.objects.filter(order=self.order)
        return settlement

    def calculate_piece_value(self):
        try:
            dims = list(map(int, self.order.dimensions.lower().strip().split('x')))
            area_m2 = (Decimal(dims[0]) * Decimal(dims[1])) / Decimal("1000000")
            price = Decimal(self.order.price)  # u Ciebie price jest intem
            value = (area_m2 * price) / Decimal("1000")
            return value.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)  # dokładniej za sztukę
        except:
            return Decimal("0")

    def calculate_value(self):
        value = self.calculate_area() * self.order.price / 1000
        return money(value)

    def calculate_area(self):
        try:
            dimensions = self.order.dimensions
            dimensions = dimensions.lower().split('x')
            dimensions = list(map(int, dimensions))
            area = round(dimensions[0] * dimensions[1] / 1000000, 5) * self.quantity

            return area
        except Exception as e:
            return 0


class DeliveryPalette(models.Model):
    delivery = models.ForeignKey(Delivery, on_delete=models.PROTECT)
    palette = models.ForeignKey(Palette, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f'{self.delivery} :: {self.palette} :: {self.quantity}'


class DeliverySpecial(models.Model):
    name = models.CharField(max_length=64, unique=True)
    provider = models.CharField(max_length=64)
    date = models.DateField()
    description = models.CharField(max_length=256, null=True, blank=True)
    processed = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.provider} {self.date}'

    class Meta:
        ordering = ['-date', 'id']

    def add_to_warehouse(self, warehouse=None):
        if not warehouse:
            warehouse = Warehouse.objects.get(name='MAGAZYN MATERIAŁÓW POMOCNICZYCH')
            if 'gotowe' in str(self.name).lower():
                warehouse = Warehouse.objects.get(name='MAGAZYN WYROBÓW GOTOWYCH')
            elif 'wyprzedażowe' in str(self.name).lower():
                warehouse = Warehouse.objects.get(name='MAGAZYN WYPRZEDAŻOWY')

        with transaction.atomic():
            items = (
                DeliverySpecialItem.objects
                .select_for_update()
                .filter(delivery=self)
                .select_related("delivery")  # provider jest CharField, więc bez delivery__provider
            )

            for item in items:
                item.add_to_warehouse(warehouse=warehouse)

            if self.check_if_processed():
                self.processed = True
                self.save(update_fields=["processed"])

    def check_if_processed(self):
        items = DeliverySpecialItem.objects.filter(delivery=self)
        for item in items:
            if not item.processed:
                return False
        return True

    def all_settle(self):
        items = DeliverySpecialItem.objects.filter(delivery=self)
        return all([i.check_settlement() for i in items])


class DeliverySpecialItem(models.Model):
    delivery = models.ForeignKey(DeliverySpecial, on_delete=models.PROTECT)
    name = models.CharField(max_length=64)
    quantity = models.PositiveIntegerField(default=0)
    price = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    processed = models.BooleanField(default=False)
    provider_sku = models.CharField(max_length=128, null=True, blank=True)
    stock = models.ForeignKey("Stock", null=True, blank=True, on_delete=models.PROTECT)

    def __str__(self):
        return f'{self.delivery} :: {self.name} :: {self.quantity}'

    def save(self, *args, **kwargs):
        if self.name:
            self.name = self.name.strip()
        super().save(*args, **kwargs)

    def calculate_value(self):
        return money(D(self.price) * D(self.quantity))

    def add_to_warehouse(self, warehouse=None, quantity=False):

        # -----------------------------------
        with transaction.atomic():
            quantity_to_add = int(self.quantity if not quantity else quantity)
            if quantity_to_add <= 0:
                raise ValidationError("Ilość przyjęcia musi być > 0")

            # blokujemy item, żeby nie przyjąć drugi raz równolegle
            item = DeliverySpecialItem.objects.select_for_update().select_related(
                "delivery",
            ).get(pk=self.pk)

            if item.processed:
                # idempotencja: drugi raz nic nie robi
                return

            if not warehouse:
                warehouse = Warehouse.objects.get(name='MAGAZYN MATERIAŁÓW POMOCNICZYCH')
                if 'gotowe' in str(self.delivery.name).lower():
                    warehouse = Warehouse.objects.get(name='MAGAZYN WYROBÓW GOTOWYCH')
                elif 'wyprzedażowe' in str(self.delivery.name).lower():
                    warehouse = Warehouse.objects.get(name='MAGAZYN WYPRZEDAŻOWY')

            if 'gotowe' in str(self.delivery.name).lower():
                material_type = StockType.objects.get(stock_type='product', unit='PIECE')
            elif 'wyprzedażowe' in str(self.delivery.name).lower():
                material_type = StockType.objects.get(stock_type='product', unit='PIECE')
            else:
                material_type = StockType.objects.get(stock_type='special', unit='PIECE')

            # 1) superstock
            target_stock = self.resolve_superstock(material_type)
            if not self.stock_id:
                self.stock = target_stock
                self.save(update_fields=["stock"])

            # 2) StockSupply (1:1 z DeliveryItem)

            stock_supply, created = StockSupply.objects.get_or_create(
                delivery_special_item=item,
                defaults=dict(
                    stock_type=material_type,
                    date=item.delivery.date,
                    dimensions="",
                    quantity=quantity_to_add,
                    name=target_stock.name,
                    value=item.calculate_value(),
                    used=False,
                )
            )

            # jeśli supply istnieje, a quantity/value/date odbiegają -> aktualizujemy (spójność)
            updates = {}
            if stock_supply.stock_type_id != material_type.id:
                updates["stock_type"] = material_type
            if stock_supply.date != item.delivery.date:
                updates["date"] = item.delivery.date
            if stock_supply.name != target_stock.name:
                updates["name"] = target_stock.name
            if int(stock_supply.quantity) != int(quantity_to_add):
                updates["quantity"] = quantity_to_add
            new_value = item.calculate_value()
            if stock_supply.value != new_value:
                updates["value"] = new_value

            if updates:
                for k, v in updates.items():
                    setattr(stock_supply, k, v)
                stock_supply.save(update_fields=list(updates.keys()))

            # 3) WarehouseStock (agregat) – blokujemy, potem ruch tylko przez move_ws
            ws, _ = WarehouseStock.objects.get_or_create(
                warehouse=warehouse,
                stock=target_stock
            )
            ws = WarehouseStock.objects.select_for_update().get(pk=ws.pk)

            # ruch magazynowy (to ma tworzyć historię i aktualizować ilość)
            move_ws(
                ws=ws,
                delta=quantity_to_add,
                date=item.delivery.date,
                stock_supply=stock_supply,
            )

            # 5) processed
            item.processed = True
            item.save(update_fields=["processed"])

    def resolve_superstock(self, material_type=None) -> "Stock":
        """
        Dla DeliverySpecialItem próbujemy znaleźć 'superstock' przez StockAlias:
          Provider (zmapowany z delivery.provider -> Provider.shortcut/name),
          provider_sku (wyciągnięty z self.name),
          dimensions (wyciągnięte z self.name, np. 1200x800)

        Jeśli nie znajdziemy aliasu, fallback: Stock(name=self.name, stock_type='special').
        """
        if not material_type:
            special_type = StockType.objects.get(stock_type="special", unit="PIECE")
        else:
            special_type = material_type

        raw = (self.name or "").strip()
        raw_upper = raw.upper()

        # 1) Mapowanie provider-string -> Provider (FK)
        #    Najpierw dokładne dopasowanie shortcut / name, potem luźniejsze contains.
        provider_txt = (self.delivery.provider or "").strip()

        provider_obj = (
                Provider.objects.filter(
                    Q(shortcut__iexact=provider_txt) | Q(name__iexact=provider_txt)
                ).first()
                or Provider.objects.filter(
            Q(shortcut__icontains=provider_txt) | Q(name__icontains=provider_txt)
        ).first()
        )

        # 2) Wyciągnij dimensions (np. 1200x800) z nazwy
        #    Dopuszczamy "1200x800", "1200X800", "1200 x 800"
        dims = None
        m_dims = re.search(r"(\d{2,5})\s*[xX]\s*(\d{2,5})", raw)
        if m_dims:
            dims = f"{m_dims.group(1)}x{m_dims.group(2)}"

        # 3) Wyciągnij SKU z nazwy (pierwszy sensowny token)
        #    Preferujemy tokeny typu T30B1TWT0372, K04, itp.
        sku = None
        # podziel po popularnych separatorach
        tokens = re.split(r"[\s\|\[\]\(\)\{\},;:/\\\-]+", raw_upper)
        tokens = [t for t in tokens if t]

        # odfiltruj tokeny które są tylko liczbami oraz same wymiary
        for t in tokens:
            if t.isdigit():
                continue
            if dims and t.replace("X", "x") == dims:
                continue
            # preferujemy alfanumeryczne długości >= 3
            if re.fullmatch(r"[A-Z0-9]{3,}", t):
                sku = t
                break

        # Jeśli nie mamy provider_obj / sku / dims -> aliasu nie znajdziemy pewnie,
        # ale spróbujemy tylko gdy mamy komplet
        if provider_obj and sku and dims:
            alias = (
                StockAlias.objects.filter(
                    provider=provider_obj,
                    provider_sku=sku,
                    dimensions=dims,
                    is_active=True,
                )
                .select_related("stock")
                .first()
            )
            if alias:
                return alias.stock

        # 4) Fallback: stock "special" po nazwie (nie robimy tu materiałowego superstocka)
        stock, _ = Stock.objects.get_or_create(
            name=raw,
            stock_type=special_type,
        )
        return stock


class StockType(models.Model):
    stock_type = models.CharField(max_length=64)
    unit = models.CharField(max_length=16, choices=UNITS)

    def __str__(self):
        return f'{self.stock_type} [{self.unit}]'

    def get_stock_type(self):
        return f'{self.stock_type}'


class StockSupply(models.Model):
    stock_type = models.ForeignKey(StockType, on_delete=models.PROTECT)
    delivery_item = models.ForeignKey(DeliveryItem, on_delete=models.PROTECT, null=True, blank=True)
    delivery_special_item = models.ForeignKey(DeliverySpecialItem, on_delete=models.PROTECT, null=True, blank=True)
    dimensions = models.CharField(max_length=32, null=True, blank=True)
    date = models.DateField(null=True, blank=True)
    quantity = models.PositiveIntegerField(default=0)
    name = models.CharField(max_length=64)
    used = models.BooleanField(default=False)
    value = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        ordering = ['-date']
        constraints = [
            models.UniqueConstraint(
                fields=["delivery_item"],
                condition=Q(delivery_item__isnull=False),
                name="uniq_supply_per_delivery_item",
            ),
            models.UniqueConstraint(
                fields=["delivery_special_item"],
                condition=Q(delivery_special_item__isnull=False),
                name="uniq_supply_per_delivery_special_item",
            )
        ]

    def save(self, *args, **kwargs):
        if self.name:
            # 1) trim + collapse whitespace
            n = " ".join(self.name.strip().split())

            # 2) jeżeli są " | " segmenty, ustandaryzuj
            if "|" in n:
                parts = [p.strip() for p in n.split("|")]
                while parts and parts[-1] == "":
                    parts.pop()
                n = " | ".join(parts)

            self.name = n
        super().save(*args, **kwargs)

    def __str__(self):
        return f'[{self.date}] {self.dimensions} {self.name}'

    def piece_value(self):
        return money(D(self.value) / D(self.quantity)) if self.quantity else money(0)

    def used_quantity(self) -> int:
        settled = (
            StockSupplySettlement.objects
            .filter(stock_supply=self, as_result=False)
            .aggregate(s=Coalesce(Sum("quantity"), 0))["s"]
        )
        sold = (
            StockSupplySell.objects
            .filter(stock_supply=self)
            .aggregate(s=Coalesce(Sum("quantity"), 0))["s"]
        )
        return int(settled) + int(sold)

    def available_quantity(self) -> int:
        """Ile jeszcze zostało w tej partii."""
        return int(self.quantity) - int(self.used_quantity())

    def refresh_used_flag(self, save: bool = True) -> bool:
        """
        used=True tylko gdy partia jest wyzerowana (available <= 0).
        used=False gdy zostało cokolwiek.
        """
        new_used = self.available_quantity() <= 0
        if self.used != new_used:
            self.used = new_used
            if save:
                self.save(update_fields=["used"])
        return self.used

    def remaining_value(self) -> Decimal:
        """
        Wartość pozostała w tej partii (proporcjonalnie do dostępnej ilości).
        """
        qty = int(self.quantity or 0)
        if qty <= 0:
            return Decimal("0.00")

        avail = int(self.available_quantity())
        if avail <= 0:
            return Decimal("0.00")

        total_value = Decimal(self.value or 0)
        return (total_value * Decimal(avail) / Decimal(qty)).quantize(Decimal("0.01"))


class Stock(models.Model):
    stock_type = models.ForeignKey(StockType, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=0)
    name = models.CharField(max_length=64)

    class Meta:
        ordering = ['stock_type__stock_type', 'name']
        constraints = [
            models.UniqueConstraint(fields=["stock_type", "name"], name="uniq_stock_type_name"),
        ]

    def __str__(self):
        return f'{self.stock_type.stock_type}: {self.name}'

    def save(self, *args, **kwargs):
        if self.name:
            # 1) trim + collapse whitespace
            n = " ".join(self.name.strip().split())

            # 2) jeżeli są " | " segmenty, ustandaryzuj
            if "|" in n:
                parts = [p.strip() for p in n.split("|")]
                while parts and parts[-1] == "":
                    parts.pop()
                n = " | ".join(parts)

            self.name = n
        super().save(*args, **kwargs)

    def update_stock(self, supply_quantity):
        self.quantity += supply_quantity
        self.save()

    def __decrease_stock(self, supply: StockSupply):
        if supply not in self.supplies.all():
            self.supplies.remove(supply)
            self.quantity -= supply.quantity
            self.save()


class Warehouse(models.Model):
    name = models.CharField(max_length=64)
    description = models.TextField(null=True, blank=True)

    def __str__(self):
        return f'{self.name}'

    def add_stock(self, stock, quantity):
        warehouse_stock, created = WarehouseStock.objects.get_or_create(warehouse=self, stock=stock)
        warehouse_stock.increase_quantity(quantity)

    def count_warehouse_value(self):
        stocks = WarehouseStock.objects.filter(warehouse=self, quantity__gt=0)
        value = 0
        for s in stocks:
            value += s.count_value()
        return value


class WarehouseStock(models.Model):
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='warehouse_stocks')
    stock = models.ForeignKey("Stock", on_delete=models.CASCADE, related_name='warehouse_stocks')
    quantity = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["warehouse", "stock"], name="uniq_warehouse_stock_pair"),
        ]
        ordering = ['stock__name']

    def __str__(self):
        return f'{self.stock.name} in {self.warehouse.name}: {self.quantity}'

    def increase_quantity(self, quantity):
        self.quantity += quantity
        self.save()

    def decrease_quantity(self, quantity):
        if quantity > self.quantity:
            raise ValueError("Cannot decrease quantity below zero.")
        self.quantity -= quantity
        self.save()

    def count_value(self):
        """
        Wartość tego WarehouseStock = suma wartości pozostałej w partiach StockSupply
        przypiętych do tego stocku (po nazwie + typie).
        """
        supplies = StockSupply.objects.filter(
            name=self.stock.name,
            stock_type=self.stock.stock_type,
        )

        total = Decimal("0.00")
        for s in supplies:
            total += s.remaining_value()

        return total

    def count_piece_value(self):
        value = self.count_value()
        return money(value/int(self.quantity)) if self.quantity else Decimal("0.00")


    def fifo_sell(self, sell: "ProductSell3"):
        """
        FIFO sprzedaż z magazynu dla danego WarehouseStock:
        - bierze StockSupply (partie) o tej samej nazwie co stock,
        - tylko product/special (tu skupiamy się na product),
        - rozpisuje sprzedaż na partie w StockSupplySell,
        - aktualizuje used cache na StockSupply.
        """
        qty = int(sell.quantity)
        if qty <= 0:
            raise ValidationError("Ilość sprzedaży musi być > 0")

        with transaction.atomic():
            # blokujemy stan magazynowy (żeby 2 sprzedaże naraz nie zjadły tej samej partii)
            ws = WarehouseStock.objects.select_for_update().get(pk=self.pk)

            if ws.quantity < qty:
                raise ValidationError("Nie ma wystarczającej ilości w magazynie!")

            # partie FIFO dla tego produktu (po nazwie)
            # ważne: order_by(date,id) -> FIFO
            supplies = (
                StockSupply.objects
                .select_for_update()
                .filter(
                    name=ws.stock.name,
                    stock_type=ws.stock.stock_type,
                )
                .order_by("date", "id")
            )

            # DEBUG – sprawdzenie spójności FIFO vs stan magazynu
            total_available = sum(s.available_quantity() for s in supplies)

            for s in supplies:
                print(
                    "  Supply:",
                    s.id,
                    "date:", s.date,
                    "qty:", s.quantity,
                    "used:", s.used_quantity(),
                    "available:", s.available_quantity(),
                )



            remaining = qty

            for supply in supplies:
                sold = StockSupplySell.objects.filter(stock_supply=supply).aggregate(t=Sum("quantity"))["t"] or 0
                settled = StockSupplySettlement.objects.filter(stock_supply=supply, as_result=False).aggregate(t=Sum("quantity"))["t"] or 0

                print("    breakdown -> sold:", sold, "settled:", settled)
                if remaining <= 0:
                    break

                available = supply.available_quantity()
                if available <= 0:
                    supply.refresh_used_flag()
                    continue

                take = min(available, remaining)

                StockSupplySell.objects.create(
                    stock_supply=supply,
                    sell=sell,
                    quantity=take
                )

                supply.refresh_used_flag()
                remaining -= take

            if remaining > 0:
                raise ValidationError("FIFO: zabrakło ilości w partiach (niespójność stanów).")

            move_ws(ws=ws, delta=-qty, date=sell.date, sell=sell)

            attach_origin_orders_to_sell(sell)


    def sell_from_order(self, sell: "ProductSell3"):
        import logging
        logger = logging.getLogger(__name__)

        if not sell.order_id:
            raise ValidationError("sell_from_order wymaga ustawionego sell.order")

        qty = int(sell.quantity or 0)
        if qty <= 0:
            raise ValidationError("Ilość sprzedaży musi być > 0")

        with transaction.atomic():
            # blokujemy stan magazynowy (agregat)
            ws = WarehouseStock.objects.select_for_update().get(pk=self.pk)

            if ws.quantity < qty:
                raise ValidationError("Nie ma wystarczającej ilości w magazynie!")

            # ============================================================
            # A) GŁÓWNE: bierzemy partie wyrobu po StockSupplySettlement(as_result=True)
            #    + settlement.order = sell.order
            #    + dopasowanie po StockType (pewne), opcjonalnie też po name
            # ============================================================
            supply_ids = list(
                StockSupply.objects.filter(
                    stocksupplysettlement__as_result=True,
                    stocksupplysettlement__settlement__order=sell.order,
                    stock_type=ws.stock.stock_type,  # ✅ pewne (nie string)
                    name=ws.stock.name,  # ✅ u Ciebie to działa (StockSupply.name)
                )
                .values_list("id", flat=True)
                .distinct()
            )

            # debug (zostaw na chwilę – potem możesz wywalić)
            any_result_ids = list(
                StockSupply.objects.filter(
                    stocksupplysettlement__as_result=True,
                    stocksupplysettlement__settlement__order=sell.order,
                ).values_list("id", flat=True).distinct()[:20]
            )

            if not supply_ids:
                raise ValidationError(
                    "Brak partii wyrobu z tego zlecenia (nie utworzono StockSupplySettlement(as_result=True)). "
                    "Najpierw rozlicz produkcję poprawnie."
                )

            supplies = StockSupply.objects.filter(id__in=supply_ids).order_by("date", "id")
            # ^ show_used() jeśli masz taką metodę managera – jeśli nie masz, usuń .show_used()


            total_available = sum(int(s.available_quantity()) for s in supplies) if supplies.exists() else 0

            if total_available < qty:
                raise ValidationError(
                    f"Brak wyrobu z tego zlecenia w partiach (dostępne {total_available}, wymagane {qty})."
                )

            # ============================================================
            # Rozpisanie sprzedaży na partie (StockSupplySell)
            # ============================================================
            remaining = qty

            for supply in supplies:
                if remaining <= 0:
                    break

                available = int(supply.available_quantity())
                if available <= 0:
                    supply.refresh_used_flag()
                    continue

                take = min(available, remaining)

                StockSupplySell.objects.create(
                    stock_supply=supply,
                    sell=sell,
                    quantity=take
                )

                supply.refresh_used_flag()
                remaining -= take

            if remaining > 0:
                raise ValidationError("Niespójność: zabrakło ilości w partiach przypiętych do zlecenia.")

            # ============================================================
            # Jeden spójny ruch magazynowy + historia (agregat WarehouseStock)
            # ============================================================
            move_ws(ws=ws, delta=-qty, date=sell.date, sell=sell)

    @staticmethod
    def use_specified_stock_supply(order_settlement, quantity: int):
        from warehouse.services.stock_moves import move_ws  # import lokalny

        with transaction.atomic():
            ws_material = order_settlement.material  # WarehouseStock
            order = order_settlement.order

            # 1) preferuj partie przypięte do zlecenia
            stock_supplies = (
                StockSupply.objects
                .select_for_update()
                .filter(delivery_item__order=order, used=False)
            )

            # 2) fallback: jeśli zlecenie nie ma swoich dostaw -> bierz partie po stocku z magazynu
            if not stock_supplies.exists():
                stock_supplies = (
                    StockSupply.objects
                    .select_for_update()
                    .filter(
                        stock_type=ws_material.stock.stock_type,
                        name=ws_material.stock.name,
                    )
                )

            if not stock_supplies.exists():
                raise Exception("No stock supplies for selected warehouse stock")

            total_available = sum(int(s.available_quantity()) for s in stock_supplies)

            if total_available < quantity:
                raise Exception('There is not enough material')

            value = Decimal("0.00")
            remaining = int(quantity)

            # FIFO po dacie
            for s in sorted(list(stock_supplies), key=lambda x: (x.date or datetime.date.min, x.id)):
                if remaining <= 0:
                    break

                available = int(s.available_quantity())

                if available <= 0:
                    s.refresh_used_flag()
                    continue

                take = min(available, remaining)

                # 1) zapis partii (księga partii)
                StockSupplySettlement.objects.create(
                    settlement=order_settlement,
                    stock_supply=s,
                    quantity=take,
                    as_result=False,
                )

                # 2) stan magazynu + historia (księga magazynu)
                move_ws(
                    ws=ws_material,
                    delta=-take,
                    date=order_settlement.settlement_date,
                    stock_supply=s,
                    order_settlement=order_settlement,
                )

                # 3) wartość zużycia proporcjonalnie
                value += Decimal(str(s.piece_value())) * Decimal(str(take))

                s.refresh_used_flag()
                remaining -= take

            return True, value

    def fifo_from_order(self, order, settlement, quantity: int):
        """
        Rozchód FIFO, ale TYLKO z partii (StockSupply) które zostały dostarczone na to konkretne zlecenie:
        StockSupply.delivery_item.order == order
        """
        if quantity <= 0:
            raise ValidationError("quantity musi być > 0")

        value_sum = Decimal("0.00")

        with transaction.atomic():
            # 1) tylko dostawy tego zamówienia
            delivery_items = DeliveryItem.objects.filter(order=order)

            # 2) tylko StockSupply z tych dostaw (i najlepiej nie-zużyte flagą used=False jako cache)
            #    UWAGA: used to cache, ale i tak liczymy dostępność po settlementach.
            supplies = (
                StockSupply.objects
                .select_for_update()
                .filter(delivery_item__in=delivery_items)
                .order_by("date", "id")  # FIFO
            )

            remaining = int(quantity)

            for supply in supplies:
                if remaining <= 0:
                    break

                available = int(supply.available_quantity())

                if available <= 0:
                    # cache
                    supply.refresh_used_flag()
                    continue

                take = min(available, remaining)

                # wartość proporcjonalna do zdjętej ilości
                # (Twoje StockSupplySettlement i tak przelicza value w save(), ale tu sumujemy wartość do zwrotu)
                part_value = (Decimal(str(take)) / Decimal(str(supply.quantity))) * Decimal(str(supply.value or 0))
                part_value = part_value.quantize(Decimal("0.01"))

                ws_material = settlement.material

                StockSupplySettlement.objects.create(
                    settlement=settlement,
                    stock_supply=supply,
                    quantity=take,
                    as_result=False,  # to jest rozchód materiału
                    value=part_value,  # optional: u Ciebie i tak nadpisze save() -> ok
                )

                move_ws(
                    ws=ws_material,
                    delta=-take,
                    date=settlement.settlement_date,
                    stock_supply=supply,
                    order_settlement=settlement,
                )

                # odśwież cache "used"
                supply.refresh_used_flag()

                value_sum += part_value
                remaining -= take

            if remaining > 0:
                raise ValidationError("Nie ma wystarczającej ilości materiału w partiach przypiętych do tego zlecenia.")

            return value_sum

    def fifo(self):
        stock_supplies = self.get_all_stock_supplies()
        return stock_supplies

    def get_all_stock_supplies(self):
        return StockSupply.objects.filter(name=self.stock.name)


class OrderSettlement(models.Model):
    order = models.ForeignKey('Order', on_delete=models.CASCADE, related_name='settlements')
    material = models.ForeignKey(WarehouseStock, on_delete=models.PROTECT, related_name='used_in_settlements')
    material_quantity = models.PositiveIntegerField(default=0)
    settlement_date = models.DateField(default=datetime.date.today)

    def __str__(self):
        return f"Settlement for Order {self.order.order_id} on {self.settlement_date}"


class OrderSettlementProduct(models.Model):
    settlement = models.ForeignKey(OrderSettlement, on_delete=models.CASCADE, related_name='settlement_products')
    stock_supply = models.ForeignKey('StockSupply', on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=0)
    is_semi_product = models.BooleanField(default=False)  # True dla półproduktów

    def __str__(self):
        return f"{self.stock_supply.name} ({self.quantity}) - {'Semi-Product' if self.is_semi_product else 'Product'}"


class StockSupplySettlement(models.Model):
    stock_supply = models.ForeignKey(StockSupply, on_delete=models.PROTECT)
    settlement = models.ForeignKey(OrderSettlement, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    value = models.DecimalField(max_digits=12, decimal_places=2, editable=False, default=Decimal("0.00"))
    as_result = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.settlement.settlement_date} | {self.stock_supply.name} | {self.quantity} | {self.as_result}'

    def calculate_value(self):
        supply_qty = self.stock_supply.quantity or 0
        if supply_qty == 0:
            return Decimal("0.00")

        supply_value = self.stock_supply.value or Decimal("0.00")

        ratio = Decimal(str(self.quantity)) / Decimal(supply_qty)
        result = ratio * supply_value

        return result.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def save(self, *args, **kwargs):
        self.value = self.calculate_value()
        super().save(*args, **kwargs)


class ProductSell3(models.Model):
    customer = models.ForeignKey(Buyer, on_delete=models.PROTECT, null=True, blank=True)
    customer_alter_name = models.CharField(max_length=32, null=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.PROTECT, null=True, blank=True)
    stock = models.ForeignKey("Stock", on_delete=models.PROTECT, null=True, blank=True)
    warehouse_stock = models.ForeignKey(WarehouseStock, on_delete=models.PROTECT, null=True, blank=True)
    order = models.ForeignKey(Order, on_delete=models.PROTECT, null=True, blank=True)
    quantity = models.IntegerField(default=1)
    price = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    date = models.DateField()

    class Meta:
        ordering = ['-date', '-customer', '-product']

    def __str__(self):
        customer = self.customer if self.customer else self.customer_alter_name
        item = self.product if self.product else (self.stock.name if self.stock else "BRAK_TOWARU")
        return f'{self.date} | {item} {self.quantity} -> {customer}'

    def revenue(self) -> Decimal:
        return (Decimal(self.price) * Decimal(self.quantity)).quantize(Decimal("0.01"))

    def cogs(self) -> Decimal:
        """
        Koszt własny sprzedaży na bazie StockSupplySell.
        Liczymy: sum(qty * unit_cost), gdzie unit_cost = stock_supply.value / stock_supply.quantity
        """
        qs = StockSupplySell.objects.filter(sell=self).select_related("stock_supply")
        total = Decimal("0.00")

        for row in qs:
            ss = row.stock_supply
            if not ss or not ss.quantity:
                continue
            unit = (Decimal(ss.value) / Decimal(ss.quantity)) if ss.value is not None else Decimal("0.00")
            total += (unit * Decimal(row.quantity))

        return total.quantize(Decimal("0.01"))

    def profit(self) -> Decimal:
        return (self.revenue() - self.cogs()).quantize(Decimal("0.01"))

    def margin_percent(self) -> Decimal:
        rev = self.revenue()
        if rev == 0:
            return Decimal("0.00")
        return (self.profit() / rev * Decimal("100")).quantize(Decimal("0.01"))

    def calculate_value(self):
        return round(self.price * self.quantity, 2)

    def get_used_materials(self):
        if not self.warehouse_stock:
            return []

        results = []

        history_qs = WarehouseStockHistory.objects.filter(
            warehouse_stock=self.warehouse_stock,
            date__lte=self.date,
            order_settlement__isnull=False
        ).select_related('order_settlement__material__stock')

        for h in history_qs:
            before = h.quantity_before
            after = h.quantity_after
            delta = after - before

            if delta == 0:
                continue  # unikamy dzielenia przez zero

            if self.quantity == delta:
                ratio = 1
            else:
                ratio = self.quantity / delta

            # zaokrąglenie zużycia materiału
            used_qty = math.ceil(h.order_settlement.material_quantity * ratio)

            # nazwa materiału
            name = h.order_settlement.material.stock.name

            # wyciąganie powierzchni
            area_m2 = self._extract_area_from_name(name, used_qty)

            results.append({
                'name': name,
                'used_quantity': used_qty,
                'area_m2': area_m2
            })

        return results

    def _extract_area_from_name(self, name, quantity=1):
        """
        Szuka wzorca [długość x szerokość] w mm w nazwie materiału
        i zwraca powierzchnię w m² dla podanej liczby sztuk.
        """
        pattern = r'\[(\d+)[xX](\d+)\]'
        match = re.search(pattern, name)
        if match:
            length = int(match.group(1))  # mm
            width = int(match.group(2))  # mm
            m2 = (length / 1000) * (width / 1000)  # m² dla 1 sztuki
            return round(m2 * quantity, 2)  # m² łącznie
        return None

    def _resolve_product_from_ws(self):
        """
        Zwraca właściwy Product odpowiadający warehouse_stock.
        Preferuje FK ws.stock.product, a jeśli go nie ma — dopasowanie po nazwie.
        """
        if not self.warehouse_stock_id:
            print('#1')
            return None
        ws = self.warehouse_stock  # zakładamy, że select_related w widoku przyspieszy dostęp
        print(ws.stock.name)
        # 1) jeśli masz FK: Stock -> Product (pole 'product')
        prod = getattr(ws.stock, "product", None)
        if prod:
            return prod
        # 2) fallback po nazwie
        return Product.objects.filter(name=ws.stock.name).first()

    def clean(self):
        # ilość dodatnia
        if self.quantity is not None and self.quantity <= 0:
            raise ValidationError({"quantity": "Ilość musi być większa od zera."})

        # cena nieujemna
        if self.price is not None and self.price < 0:
            raise ValidationError({"price": "Cena nie może być ujemna."})

        # jeśli jest warehouse_stock → zawsze ustaw stock + ewentualnie product (jeśli istnieje)
        if self.warehouse_stock_id:
            ws = self.warehouse_stock

            # ✅ zawsze ustaw stock z WS
            self.stock = ws.stock

            # product powiązany ze stockiem (może nie istnieć dla materiałów)
            resolved_prod = getattr(ws.stock, "product", None)

            if resolved_prod:
                # jeśli product nie podano → ustaw automatycznie
                if self.product_id is None:
                    self.product = resolved_prod
                else:
                    # jeśli podano product → pilnuj spójności
                    if self.product_id != resolved_prod.id:
                        raise ValidationError({"product": "Wybrany produkt nie zgadza się z magazynem."})
            # else:
            #     # ✅ materiał: nie wymuszamy product
            #     # jeśli ktoś ręcznie poda product mimo braku powiązania w stocku → blokujemy (żeby nie robić śmieci)
            #     if self.product_id is not None:
            #         raise ValidationError({"product": "Ten stan magazynowy nie ma powiązanego produktu (materiał)."})
        else:
            # jeśli nie ma warehouse_stock, to wymagamy żeby było przynajmniej product lub stock
            if not self.product_id and not getattr(self, "stock_id", None):
                raise ValidationError({"warehouse_stock": "Wybierz stan magazynowy lub ustaw produkt/stock."})

        return super().clean()

    def save(self, *args, **kwargs):
        # zabezpieczenie na wypadek braku full_clean() w wyższych warstwach
        if self.warehouse_stock_id and self.product_id is None:
            resolved = self._resolve_product_from_ws()
            if resolved:
                self.product = resolved
        return super().save(*args, **kwargs)


class StockSupplySell(models.Model):
    stock_supply = models.ForeignKey(StockSupply, on_delete=models.PROTECT)
    sell = models.ForeignKey(ProductSell3, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()

    class Meta:
        ordering = ['-sell__date']

    def __str__(self):
        return f'[{self.sell.date}] {self.stock_supply.name} -> {self.sell.customer} ({self.quantity})'


class MonthResults(models.Model):
    month = models.PositiveIntegerField()
    year = models.PositiveIntegerField()
    expenses = models.PositiveIntegerField()
    financial_expenses = models.PositiveIntegerField()
    management_expenses = models.PositiveIntegerField()
    logistic_expenses = models.PositiveIntegerField()
    other_expenses = models.PositiveIntegerField()

    def __str__(self):
        return f'{self.year} {self.month}'


class CustomerPalette(models.Model):
    customer = models.ForeignKey(Buyer, on_delete=models.PROTECT)
    palette = models.ForeignKey(Palette, on_delete=models.PROTECT)
    quantity = models.IntegerField(default=0)

    def __str__(self):
        return f'{self.customer} :: {self.palette} :: {self.quantity}'

    class Meta:
        unique_together = ['customer', 'palette']
        ordering = ['customer']


class ProductComplexAssemblyQuerySet(models.QuerySet):
    def with_locked(self):
        # podzapytanie: WS użyte do PRZYJĘCIA wyrobu gotowego z tej assembly
        fg_ws_ids = WarehouseStockHistory.objects.filter(
            assembly=OuterRef("pk"),
            stock_supply__isnull=False,   # odróżnia „przyjęcie gotowca” od rozchodu części
        ).values("warehouse_stock_id")

        # locked jeśli istnieje sprzedaż z któregokolwiek z tych WS
        return self.annotate(
            _locked=Exists(
                ProductSell3.objects.filter(warehouse_stock_id__in=fg_ws_ids)
            )
        )


class ProductComplexAssembly(models.Model):
    date = models.DateField()
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.IntegerField()
    parts = models.ManyToManyField(WarehouseStock, through='ProductComplexParts', blank=True)
    objects = ProductComplexAssemblyQuerySet.as_manager()

    def __str__(self):
        return f'{self.product} {self.date} -> {self.quantity}'

    class Meta:
        ordering = ['date', 'product']

    @property
    def is_locked(self) -> bool:
        from .models import WarehouseStockHistory, ProductSell3  # jeśli w tym samym pliku, pominąć
        fg_ws_ids = WarehouseStockHistory.objects.filter(
            assembly=self, stock_supply__isnull=False
        ).values_list("warehouse_stock_id", flat=True)
        if not fg_ws_ids:
            return False
        return ProductSell3.objects.filter(warehouse_stock_id__in=fg_ws_ids).exists()

    def clean(self):
        # blokada modyfikacji/rozbiórki po sprzedaży
        if self.pk and self.is_locked:
            raise ValidationError("Nie można modyfikować: wyrób z tego montażu został sprzedany.")
        return super().clean()

    def save(self, *args, **kwargs):
        # przy aktualizacji wymuś walidację -> zadziała blokada
        if self.pk:
            self.full_clean()
        return super().save(*args, **kwargs)


class ProductComplexParts(models.Model):
    assembly = models.ForeignKey(ProductComplexAssembly, on_delete=models.PROTECT, related_name="assembly_parts")
    part = models.ForeignKey(WarehouseStock, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f'{self.part} :: {self.quantity}'

    class Meta:
        ordering = ['assembly', 'part']


class WarehouseStockHistory(models.Model):
    warehouse_stock = models.ForeignKey(WarehouseStock, on_delete=models.CASCADE, related_name="warehouse_stock")
    stock_supply = models.ForeignKey(StockSupply, on_delete=models.PROTECT, null=True, blank=True)
    order_settlement = models.ForeignKey(OrderSettlement, on_delete=models.PROTECT, null=True, blank=True)
    assembly = models.ForeignKey(ProductComplexAssembly, on_delete=models.PROTECT, null=True, blank=True)
    delta = models.IntegerField(default=0)
    quantity_before = models.PositiveIntegerField(default=0)
    quantity_after = models.PositiveIntegerField(default=0)
    date = models.DateField(null=True, blank=True)
    sell = models.ForeignKey("ProductSell3", on_delete=models.PROTECT, null=True, blank=True)

    class Meta:
        ordering = ['-date', '-warehouse_stock']

    def save(self, *args, **kwargs):
        if not self.date:
            if self.sell:
                self.date = self.sell.date
            elif self.stock_supply:
                self.date = self.stock_supply.date
            elif self.order_settlement:
                self.date = self.order_settlement.settlement_date
        super().save(*args, **kwargs)

    def __str__(self):
        if self.sell:
            return f'{self.date} | SELL | {self.warehouse_stock.stock.name} {self.quantity_before} -> {self.quantity_after}'
        elif self.stock_supply:
            return f'{self.date} | {self.warehouse_stock.stock.name} INCREASE {self.quantity_before} -> {self.quantity_after}'
        elif self.order_settlement:
            return f'{self.date} | {self.warehouse_stock.stock.name} DECREASE {self.quantity_before} -> {self.quantity_after}'
        elif self.assembly:
            return f'{self.date} | {self.warehouse_stock.stock.name} DECREASE {self.quantity_before} -> {self.quantity_after}'
        else:
            return f'{self.date} | {self.warehouse_stock.stock.name} DECREASE {self.quantity_before} -> {self.quantity_after}'


class PriceList(models.Model):
    provider = models.ForeignKey(Provider, on_delete=models.PROTECT)
    date_start = models.DateField()
    date_end = models.DateField(null=True, blank=True)

    def __str__(self):
        if self.date_end:
            return f'{self.provider} :: {self.date_start} - {self.date_end}'
        return f'[ACTIVE]{self.provider} :: {self.date_start}'

    class Meta:
        unique_together = ['provider', 'date_start']


class PriceListItem(models.Model):
    price_list = models.ForeignKey(PriceList, on_delete=models.CASCADE)
    name = models.CharField(max_length=16)
    flute = models.CharField(max_length=4)
    weight = models.IntegerField(default=0)
    etc = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    price = models.IntegerField()
    price2 = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f'{self.name} - {self.price}'

    class Meta:
        unique_together = ['price_list', 'name']


class BOM(models.Model):
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="boms")
    version = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["product", "version"],
                name="uniq_bom_product_version",
            ),
        ]

    def __str__(self):
        label = str(self.product)
        return f"{label} v{self.version}"

    def clean(self):
        if self.is_active:
            qs = BOM.objects.filter(product=self.product, is_active=True)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                raise ValidationError("Dla danego produktu może być tylko jeden aktywny BOM.")

    @classmethod
    @transaction.atomic
    def create_next_version(cls, *, product, base_bom=None, activate=True):
        last = (
            cls.objects.select_for_update()
            .filter(product=product)
            .order_by("-version")
            .first()
        )
        next_version = 1 if not last else last.version + 1

        if activate:
            cls.objects.filter(product=product, is_active=True).update(is_active=False)

        new_bom = cls.objects.create(
            product=product,
            version=next_version,
            is_active=activate,
        )

        if base_bom:
            parts = base_bom.parts.all()
            cls._copy_parts(parts, new_bom)

        return new_bom

    @staticmethod
    def _copy_parts(parts_qs, new_bom):
        BOMPart.objects.bulk_create(
            [
                BOMPart(bom=new_bom, part=p.part, quantity=p.quantity)
                for p in parts_qs.select_related("part")
            ]
        )

    def requirements(self, order_quantity: int):
        result = []
        for bp in self.parts.select_related("part", "part__stock_type"):
            required = bp.quantity * Decimal(order_quantity)
            result.append((bp.part, required))
        return result

    def to_int_qty(self, stock: "Stock", qty: Decimal) -> int:
        unit = stock.stock_type.unit
        if unit in ("PIECE", "SET"):
            return int(math.ceil(qty))
        raise ValidationError(
            f"Nieobsługiwana jednostka dla realizacji BOM: {unit}. "
            f"Dla KG/M2 potrzebujesz Decimal w stanach magazynowych."
        )


class BOMPart(models.Model):
    bom = models.ForeignKey(
        BOM,
        on_delete=models.CASCADE,
        related_name="parts",
    )
    part = models.ForeignKey(Stock, on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=10, decimal_places=3)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["bom", "part"],
                name="uniq_bompart_bom_part",
            ),
        ]

    def __str__(self):
        return f"{self.part} x {self.quantity}"


class ProductSellOrderPart(models.Model):
    sell = models.ForeignKey("ProductSell3", on_delete=models.CASCADE, related_name="order_parts")
    order = models.ForeignKey("Order", on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("sell", "order")

    def __str__(self):
        return f"Sell#{self.sell_id} <- Order#{self.order_id} qty={self.quantity}"


def resolve_orders_for_supply(stock_supply):
    """
    Zwraca listę order_id, z których pochodzi dana partia (StockSupply).
    A: StockSupplySettlement(as_result=True) -> settlement -> order
    B: WarehouseStockHistory delta>0 dla tej stock_supply -> order_settlement.order
    """

    # A) po settlementach wynikowych
    qs_a = (
        stock_supply.stocksupplysettlement_set
        .filter(as_result=True, settlement__order_id__isnull=False)
        .values_list("settlement__order_id", flat=True)
        .distinct()
    )
    order_ids_a = list(qs_a)

    if order_ids_a:
        return order_ids_a

    # B) fallback po historii (przyjęcie delta>0)
    hist_qs = (
        WarehouseStockHistory.objects
        .filter(stock_supply=stock_supply, order_settlement__order_id__isnull=False)
        .annotate(delta=F("quantity_after") - F("quantity_before"))
        .values(
            "id", "date",
            "quantity_before", "quantity_after", "delta",
            "order_settlement_id", "order_settlement__order_id",
            "warehouse_stock_id",
        )
        .order_by("id")
    )

    order_ids_b = list(
        WarehouseStockHistory.objects
        .filter(stock_supply=stock_supply, order_settlement__order_id__isnull=False)
        .annotate(delta=F("quantity_after") - F("quantity_before"))
        .filter(delta__gt=0)
        .values_list("order_settlement__order_id", flat=True)
        .distinct()
    )

    return order_ids_b


def attach_origin_orders_to_sell(sell):
    """
    Na podstawie StockSupplySell dopina zlecenia pochodzenia do sprzedaży.
    Zapisuje w ProductSellOrderPart.
    """

    # czyścimy poprzednie przypisania i liczymy od nowa
    deleted = ProductSellOrderPart.objects.filter(sell=sell).delete()

    rows = (
        StockSupplySell.objects
        .filter(sell=sell)
        .select_related("stock_supply")
    )

    agg = {}  # order_id -> qty

    for r in rows:
        ss = r.stock_supply

        if not ss:
            continue

        order_ids = resolve_orders_for_supply(ss)

        if not order_ids:
            continue

        oid = order_ids[0]
        agg[oid] = agg.get(oid, 0) + int(r.quantity)

    for oid, q in agg.items():
        obj, created = ProductSellOrderPart.objects.get_or_create(
            sell=sell,
            order_id=oid,  # FK by id
            defaults={"quantity": q}
        )

        if not created:
            obj.quantity = obj.quantity + q
            obj.save(update_fields=["quantity"])

    final_count = ProductSellOrderPart.objects.filter(sell=sell).count()



class StockAlias(models.Model):
    provider = models.ForeignKey(Provider, on_delete=models.PROTECT)
    provider_sku = models.CharField(max_length=128)   # np. T30B1TWT0372
    dimensions = models.CharField(max_length=64)      # np. 1200x800
    stock = models.ForeignKey("Stock", on_delete=models.PROTECT, related_name="aliases")
    is_active = models.BooleanField(default=True)
    notes = models.CharField(max_length=256, null=True, blank=True)

    class Meta:
        unique_together = ("provider", "provider_sku", "dimensions")
        indexes = [
            models.Index(fields=["provider", "provider_sku", "dimensions"]),
            models.Index(fields=["stock"]),
        ]

    def __str__(self):
        p = getattr(self.provider, "shortcut", None) or getattr(self.provider, "name", "provider")
        return f"{p} :: {self.provider_sku} [{self.dimensions}] -> {self.stock.name}"


from django.db import models
from django.core.exceptions import ValidationError


class ProductPackaging(models.Model):
    product = models.OneToOneField(
        "Product",
        on_delete=models.PROTECT,
        related_name="packaging",
    )
    palette = models.ForeignKey(
        "Palette",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="product_packagings",
    )

    columns = models.PositiveIntegerField(default=0, help_text="Słupki")
    layers = models.PositiveIntegerField(default=0, help_text="Warstwy")
    qty_per_pack = models.PositiveIntegerField(default=0, help_text="Ilość w paczce")

    qty_per_pallet = models.PositiveIntegerField(
        default=0,
        editable=False,
        help_text="Auto: columns * layers * qty_per_pack",
    )

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Product packaging"
        verbose_name_plural = "Product packagings"

    def clean(self):
        # jeśli jest paleta, to wypada mieć komplet parametrów > 0
        if self.palette_id:
            if self.columns <= 0 or self.layers <= 0 or self.qty_per_pack <= 0:
                raise ValidationError(
                    "Jeśli wybrano paletę, to columns, layers i qty_per_pack muszą być > 0."
                )
        return super().clean()

    def recalc(self):
        if self.columns > 0 and self.layers > 0 and self.qty_per_pack > 0:
            self.qty_per_pallet = self.columns * self.layers * self.qty_per_pack
        else:
            self.qty_per_pallet = 0

    def save(self, *args, **kwargs):
        self.recalc()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Packaging: {self.product}"

