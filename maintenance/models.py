from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Sum
from decimal import Decimal
from django.db import transaction
from warehouse.models import WarehouseStock, StockSupply
from warehouse.services.stock_moves import move_ws
from django.utils import timezone


class Machine(models.Model):
    name = models.CharField(max_length=120)
    code = models.CharField(max_length=50, unique=True)
    serial_number = models.CharField(max_length=100, blank=True, null=True)
    manufacturer = models.CharField(max_length=100, blank=True, null=True)
    location = models.CharField(max_length=120, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["code", "name"]

    def __str__(self):
        return f"{self.code} - {self.name}"


class PartCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ["name"]
    def __str__(self):
        return self.name


class MachinePart(models.Model):
    name = models.CharField(max_length=150)
    code = models.CharField(max_length=80, unique=True)
    category = models.ForeignKey(
        PartCategory,
        on_delete=models.PROTECT,
        related_name="parts",
        blank=True,
        null=True,
    )
    producer = models.CharField(max_length=100, blank=True, null=True)
    unit = models.CharField(max_length=20, default="PIECE")
    description = models.TextField(blank=True, null=True)

    supplier = models.ForeignKey(
        "maintenance.MaintenanceSupplier",
        on_delete=models.PROTECT,
        related_name="parts",
        blank=True,
        null=True,
    )

    supplier_code = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    # Powiązanie z istniejącym magazynem
    stock = models.OneToOneField(
        "warehouse.Stock",
        on_delete=models.PROTECT,
        related_name="machine_part",
        blank=True,
        null=True,
    )

    min_quantity = models.PositiveIntegerField(default=0)
    recommended_quantity = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name", "code"]

    def __str__(self):
        return f"{self.code} - {self.name}"

    def current_quantity(self):
        if not self.stock_id:
            return 0
        return (
                self.stock.warehouse_stocks.aggregate(
                    total=Sum("quantity")
                )["total"] or 0
        )

    def is_below_minimum(self):
        return self.current_quantity() < self.min_quantity


class MachinePartAssignment(models.Model):
    machine = models.ForeignKey(
        Machine,
        on_delete=models.CASCADE,
        related_name="part_assignments",
    )
    part = models.ForeignKey(
        MachinePart,
        on_delete=models.CASCADE,
        related_name="machine_assignments",
    )
    quantity_needed = models.PositiveIntegerField(default=1)
    is_critical = models.BooleanField(default=False)
    notes = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        unique_together = ("machine", "part")
        ordering = ["machine__code", "part__name"]

    def __str__(self):
        return f"{self.machine} -> {self.part} ({self.quantity_needed})"


class MaintenanceEvent(models.Model):
    EVENT_TYPES = (
        ("failure", "Awaria"),
        ("repair", "Naprawa"),
        ("inspection", "Przegląd"),
        ("replacement", "Wymiana części"),
    )

    machine = models.ForeignKey(
        Machine,
        on_delete=models.PROTECT,
        related_name="events",
    )
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES)
    date = models.DateField()
    description = models.TextField(blank=True, null=True)
    downtime_hours = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="maintenance_events",
        blank=True,
        null=True,
    )

    class Meta:
        ordering = ["-date", "-id"]

    def __str__(self):
        return f"{self.machine} | {self.get_event_type_display()} | {self.date}"


class MaintenancePartUsage(models.Model):
    event = models.ForeignKey(
        MaintenanceEvent,
        on_delete=models.CASCADE,
        related_name="parts_used",
    )
    part = models.ForeignKey(
        MachinePart,
        on_delete=models.PROTECT,
        related_name="usages",
    )
    warehouse_stock = models.ForeignKey(
        "warehouse.WarehouseStock",
        on_delete=models.PROTECT,
        related_name="maintenance_usages",
    )
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["event__date", "id"]

    def __str__(self):
        return f"{self.event} -> {self.part} x {self.quantity}"

    def clean(self):
        if self.part_id and self.warehouse_stock_id:
            if self.part.stock_id != self.warehouse_stock.stock_id:
                raise ValidationError({
                    "warehouse_stock": "Wybrany stan magazynowy nie należy do tej części."
                })

        if self.warehouse_stock_id and self.quantity > self.warehouse_stock.quantity:
            raise ValidationError({
                "quantity": "Brak wystarczającej ilości na magazynie."
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class MaintenanceSupplier(models.Model):
    name = models.CharField(max_length=120)
    shortcut = models.CharField(max_length=30, blank=True, null=True)
    website = models.URLField(blank=True, null=True)

    city = models.CharField(max_length=100, blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)

    notes = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def main_contact(self):
        return self.contacts.filter(is_main=True).first()


class MaintenanceSupplierContact(models.Model):
    CONTACT_TYPES = (
        ("general", "General"),
        ("sales", "Sales"),
        ("service", "Service"),
        ("parts", "Parts"),
        ("complaint", "Complaint"),
    )

    supplier = models.ForeignKey(
        MaintenanceSupplier,
        on_delete=models.CASCADE,
        related_name="contacts",
    )
    name = models.CharField(max_length=100)
    role = models.CharField(max_length=100, blank=True, null=True)

    contact_type = models.CharField(
        max_length=20,
        choices=CONTACT_TYPES,
        default="general",
    )

    phone = models.CharField(max_length=32, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)

    is_main = models.BooleanField(default=False)
    notes = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        ordering = ["-is_main", "name"]

    def __str__(self):
        return f"{self.supplier} - {self.name}"



    def save(self, *args, **kwargs):
        if self.is_main:
            MaintenanceSupplierContact.objects.filter(
                supplier=self.supplier,
                is_main=True
            ).exclude(pk=self.pk).update(is_main=False)

        super().save(*args, **kwargs)


class MachinePartSupplier(models.Model):
    part = models.ForeignKey(
        MachinePart,
        on_delete=models.CASCADE,
        related_name="part_suppliers",
    )
    supplier = models.ForeignKey(
        MaintenanceSupplier,
        on_delete=models.PROTECT,
        related_name="supplier_parts",
    )
    supplier_code = models.CharField(max_length=100, blank=True, null=True)
    is_preferred = models.BooleanField(default=False)
    lead_time_days = models.PositiveIntegerField(blank=True, null=True)
    notes = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        unique_together = ("part", "supplier")
        ordering = ["-is_preferred", "supplier__name"]

    def __str__(self):
        return f"{self.part} -> {self.supplier}"

    def save(self, *args, **kwargs):
        if self.is_preferred:
            MachinePartSupplier.objects.filter(
                part=self.part,
                is_preferred=True
            ).exclude(pk=self.pk).update(is_preferred=False)

        super().save(*args, **kwargs)


class MaintenanceDelivery(models.Model):
    supplier = models.ForeignKey(
        MaintenanceSupplier,
        on_delete=models.PROTECT,
        related_name="deliveries",
    )
    delivery_date = models.DateField()
    document_number = models.CharField(max_length=100, blank=True, null=True)
    invoice_number = models.CharField(max_length=100, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="maintenance_deliveries",
        blank=True,
        null=True,
    )
    is_received = models.BooleanField(default=False)
    received_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["-delivery_date", "-id"]

    def __str__(self):
        return f"{self.supplier} | {self.delivery_date} | {self.document_number or self.id}"

    @transaction.atomic
    def receive(self):
        if self.is_received:
            return

        for item in self.items.select_related("part", "warehouse"):
            item.add_to_warehouse()

        self.is_received = True
        self.received_at = timezone.now()
        self.save(update_fields=["is_received", "received_at"])


class MaintenanceDeliveryItem(models.Model):
    delivery = models.ForeignKey(
        MaintenanceDelivery,
        on_delete=models.CASCADE,
        related_name="items",
    )
    part = models.ForeignKey(
        MachinePart,
        on_delete=models.PROTECT,
        related_name="delivery_items",
    )
    warehouse = models.ForeignKey(
        "warehouse.Warehouse",
        on_delete=models.PROTECT,
        related_name="maintenance_delivery_items",
    )
    quantity = models.PositiveIntegerField()
    unit_price_net = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    total_price_net = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    supplier_code = models.CharField(max_length=100, blank=True, null=True)
    notes = models.CharField(max_length=255, blank=True, null=True)
    processed = models.BooleanField(default=False)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.delivery} -> {self.part} x {self.quantity}"

    def save(self, *args, **kwargs):
        self.total_price_net = Decimal(self.quantity or 0) * Decimal(self.unit_price_net or 0)
        super().save(*args, **kwargs)

    def add_to_warehouse(self):
        if self.processed:
            return

        if self.quantity <= 0:
            raise ValidationError("Ilość przyjęcia musi być > 0")

        with transaction.atomic():
            item = MaintenanceDeliveryItem.objects.select_for_update().select_related(
                "delivery",
                "part",
                "warehouse",
            ).get(pk=self.pk)

            if item.processed:
                return

            stock_supply, created = StockSupply.objects.get_or_create(
                maintenance_delivery_item=item,
                defaults=dict(
                    stock_type=item.part.stock.stock_type,
                    date=item.delivery.delivery_date,
                    dimensions="",
                    quantity=item.quantity,
                    name=item.part.stock.name,
                    value=item.total_price_net,
                    used=False,
                )
            )

            updates = {}
            if stock_supply.stock_type_id != item.part.stock.stock_type_id:
                updates["stock_type"] = item.part.stock.stock_type
            if stock_supply.date != item.delivery.delivery_date:
                updates["date"] = item.delivery.delivery_date
            if stock_supply.name != item.part.stock.name:
                updates["name"] = item.part.stock.name
            if int(stock_supply.quantity) != int(item.quantity):
                updates["quantity"] = item.quantity
            if stock_supply.value != item.total_price_net:
                updates["value"] = item.total_price_net

            if updates:
                for k, v in updates.items():
                    setattr(stock_supply, k, v)
                stock_supply.save(update_fields=list(updates.keys()))

            ws, _ = WarehouseStock.objects.get_or_create(
                warehouse=item.warehouse,
                stock=item.part.stock,
            )
            ws = WarehouseStock.objects.select_for_update().get(pk=ws.pk)

            move_ws(
                ws=ws,
                delta=item.quantity,
                date=item.delivery.delivery_date,
                stock_supply=stock_supply,
            )

            item.processed = True
            item.save(update_fields=["processed"])
