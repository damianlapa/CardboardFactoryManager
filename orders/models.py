from decimal import Decimal, ROUND_CEILING

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


# ============================================================
# CUSTOMER ORDER
# ============================================================

class CustomerOrder(models.Model):

    class Status(models.TextChoices):
        NEW = "NEW", "Nowe"
        MATERIAL_PENDING = "MATERIAL_PENDING", "Oczekuje na materiał"
        MATERIAL_READY = "MATERIAL_READY", "Materiał gotowy"
        READY_FOR_PRODUCTION = "READY_FOR_PRODUCTION", "Gotowe do produkcji"
        IN_PRODUCTION = "IN_PRODUCTION", "W produkcji"
        COMPLETED = "COMPLETED", "Zakończone"
        CANCELLED = "CANCELLED", "Anulowane"

    class Priority(models.IntegerChoices):
        LOW = 1, "Niski"
        HIGH = 2, "Wysoki"
        CRITICAL = 3, "Krytyczny"

    customer = models.ForeignKey(
        "warehousemanager.Buyer",
        on_delete=models.PROTECT,
        related_name="customer_orders",
    )

    product = models.ForeignKey(
        "warehouse.Product",
        on_delete=models.PROTECT,
        related_name="customer_orders",
    )

    number = models.PositiveIntegerField(
        null=True,
        blank=True,
        editable=False,
        db_index=True,
    )

    year = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        editable=False,
        db_index=True,
    )

    quantity = models.PositiveIntegerField(
        help_text="Ilość produktu zamówiona przez klienta",
    )

    order_date = models.DateField(
        null=True,
        blank=True,
        help_text="Data zamówienia klienta",
    )

    requested_delivery_date = models.DateField(
        null=True,
        blank=True,
        help_text="Oczekiwany termin dostawy produktu",
    )

    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.NEW,
        db_index=True,
    )

    priority = models.PositiveSmallIntegerField(
        choices=Priority.choices,
        null=True,
        blank=True,
    )

    priority_date = models.DateField(
        null=True,
        blank=True,
    )

    notes = models.TextField(
        blank=True,
        default="",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_customer_orders",
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="updated_customer_orders",
    )

    # tylko na czas migracji
    legacy_production_order = models.OneToOneField(
        "production.ProductionOrder",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="new_customer_order",
    )

    class Meta:
        ordering = ["-created_at", "-id"]

        constraints = [
            models.UniqueConstraint(
                fields=["year", "number"],
                name="orders_unique_customer_order_number_year",
            ),
        ]

        indexes = [
            models.Index(
                fields=["customer", "created_at"],
                name="orders_customer_created_idx",
            ),
            models.Index(
                fields=["status", "priority"],
                name="orders_status_priority_idx",
            ),
        ]

    def __str__(self):
        return (
            f"{self.order_number} | "
            f"{self.customer} | "
            f"{self.product} | "
            f"{self.quantity} szt."
        )

    @property
    def order_number(self):
        if not self.number or not self.year:
            return "-"

        return f"{self.number}/{str(self.year)[-2:]}"


# ============================================================
# MATERIAL REQUIREMENT
# ============================================================

class MaterialRequirement(models.Model):

    class Cover(models.TextChoices):
        GREY = "GREY", "Szara"
        WHITE_ONE_SIDE = "WHITE_ONE_SIDE", "Jednostronnie biała"
        WHITE_TWO_SIDES = "WHITE_TWO_SIDES", "Dwustronnie biała"
        OTHER = "OTHER", "Inna"

    customer_order = models.ForeignKey(
        CustomerOrder,
        on_delete=models.CASCADE,
        related_name="material_requirements",
    )

    sheet_length = models.PositiveIntegerField(
        help_text="Długość arkusza w mm",
    )

    sheet_width = models.PositiveIntegerField(
        help_text="Szerokość arkusza w mm",
    )

    pieces_per_sheet = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("1.00"),
    )

    required_sheet_quantity = models.PositiveIntegerField(
        default=0,
        help_text="Ilość potrzebnych arkuszy",
    )

    layers = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
    )

    flute = models.CharField(
        max_length=8,
        blank=True,
        default="",
    )

    min_gsm = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    min_ect = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Minimalne ECT kN/m",
    )

    cover = models.CharField(
        max_length=32,
        choices=Cover.choices,
        null=True,
        blank=True,
    )

    notes = models.TextField(
        blank=True,
        default="",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["customer_order_id", "id"]

    def __str__(self):
        return (
            f"{self.customer_order} | "
            f"{self.sheet_length}x{self.sheet_width} | "
            f"{self.required_sheet_quantity} ark."
        )

    @property
    def sheet_area_m2(self):
        return (
            Decimal(self.sheet_length)
            * Decimal(self.sheet_width)
            / Decimal("1000000")
        )

    @property
    def required_area_m2(self):
        return (
            self.sheet_area_m2
            * Decimal(self.required_sheet_quantity)
        )

    def calculate_required_sheet_quantity(self):
        if not self.pieces_per_sheet:
            return 0

        result = (
            Decimal(self.customer_order.quantity)
            / Decimal(self.pieces_per_sheet)
        )

        return int(
            result.quantize(
                Decimal("1"),
                rounding=ROUND_CEILING,
            )
        )


# ============================================================
# PROVIDER CARDBOARD
# ============================================================

class CardboardGrade(models.Model):

    class Cover(models.TextChoices):
        GREY = "GREY", "Szara"
        WHITE_ONE_SIDE = "WHITE_ONE_SIDE", "Jednostronnie biała"
        WHITE_TWO_SIDES = "WHITE_TWO_SIDES", "Dwustronnie biała"
        OTHER = "OTHER", "Inna"

    provider = models.ForeignKey(
        "warehouse.Provider",
        on_delete=models.PROTECT,
        related_name="cardboard_grades",
    )

    index = models.CharField(
        max_length=128,
        help_text="Indeks tektury u dostawcy",
    )

    layers = models.PositiveSmallIntegerField()

    flute = models.CharField(
        max_length=8,
    )

    gsm = models.PositiveIntegerField()

    ect = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
    )

    composition = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Skład surowcowy wg dostawcy",
    )

    cover = models.CharField(
        max_length=32,
        choices=Cover.choices,
        null=True,
        blank=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    notes = models.TextField(
        blank=True,
        default="",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "provider",
            "layers",
            "flute",
            "gsm",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=["provider", "index"],
                name="orders_unique_provider_cardboard_index",
            ),
        ]

    def __str__(self):
        return (
            f"{self.provider} | "
            f"{self.index} | "
            f"{self.layers}{self.flute} | "
            f"{self.gsm} g/m²"
        )


# ============================================================
# PRICE LISTS
# ============================================================

class CardboardPriceList(models.Model):

    provider = models.ForeignKey(
        "warehouse.Provider",
        on_delete=models.PROTECT,
        related_name="cardboard_price_lists",
    )

    number = models.CharField(
        max_length=128,
        blank=True,
        default="",
    )

    valid_from = models.DateField(
        db_index=True,
    )

    valid_to = models.DateField(
        null=True,
        blank=True,
        db_index=True,
    )

    notes = models.TextField(
        blank=True,
        default="",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_cardboard_price_lists",
    )

    class Meta:
        ordering = [
            "-valid_from",
            "-id",
        ]

    def __str__(self):
        return (
            f"{self.provider} | "
            f"{self.number or self.pk} | "
            f"od {self.valid_from}"
        )


class CardboardPriceListItem(models.Model):

    class ProviderStatus(models.TextChoices):
        STANDARD = "STANDARD", "Standard"
        NON_STANDARD = "NON_STANDARD", "Niestandardowa"
        SPECIAL = "SPECIAL", "Specjalna"
        OTHER = "OTHER", "Inna"

    price_list = models.ForeignKey(
        CardboardPriceList,
        on_delete=models.CASCADE,
        related_name="items",
    )

    cardboard = models.ForeignKey(
        CardboardGrade,
        on_delete=models.PROTECT,
        related_name="price_list_items",
    )

    provider_status = models.CharField(
        max_length=32,
        choices=ProviderStatus.choices,
        default=ProviderStatus.STANDARD,
    )

    provider_status_raw = models.CharField(
        max_length=64,
        blank=True,
        default="",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "price_list",
                    "cardboard",
                ],
                name="orders_unique_price_list_cardboard",
            ),
        ]

    def __str__(self):
        return f"{self.price_list} | {self.cardboard}"

    def price_for_area(self, area_m2):
        area = Decimal(area_m2)

        tier = (
            self.price_tiers
            .filter(min_area_m2__lte=area)
            .filter(
                Q(max_area_m2__gte=area)
                | Q(max_area_m2__isnull=True)
            )
            .order_by("-min_area_m2")
            .first()
        )

        if not tier:
            return None

        return tier.price_per_1000_m2


class CardboardPriceTier(models.Model):

    item = models.ForeignKey(
        CardboardPriceListItem,
        on_delete=models.CASCADE,
        related_name="price_tiers",
    )

    min_area_m2 = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    max_area_m2 = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )

    price_per_1000_m2 = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    class Meta:
        ordering = [
            "min_area_m2",
        ]

    def __str__(self):
        upper = self.max_area_m2 or "∞"

        return (
            f"{self.min_area_m2} - {upper} m² | "
            f"{self.price_per_1000_m2} PLN/1000m²"
        )


# ============================================================
# CARDBOARD PURCHASE ORDER
# ============================================================

class CardboardOrder(models.Model):

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Robocze"
        SENT = "SENT", "Wysłane"
        PARTIALLY_RECEIVED = "PARTIALLY_RECEIVED", "Częściowo dostarczone"
        RECEIVED = "RECEIVED", "Dostarczone"
        CANCELLED = "CANCELLED", "Anulowane"

    provider = models.ForeignKey(
        "warehouse.Provider",
        on_delete=models.PROTECT,
        related_name="new_cardboard_orders",
    )

    number = models.CharField(
        max_length=64,
    )

    order_date = models.DateField()

    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )

    notes = models.TextField(
        blank=True,
        default="",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_cardboard_orders",
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    # tylko migracja
    legacy_warehouse_order = models.OneToOneField(
        "warehouse.Order",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="new_cardboard_order",
    )

    class Meta:
        ordering = [
            "-order_date",
            "-id",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "provider",
                    "number",
                ],
                name="orders_unique_provider_purchase_number",
            ),
        ]

    def __str__(self):
        return f"{self.provider} | {self.number}"


class CardboardOrderItem(models.Model):

    order = models.ForeignKey(
        CardboardOrder,
        on_delete=models.CASCADE,
        related_name="items",
    )

    requirement = models.ForeignKey(
        MaterialRequirement,
        on_delete=models.PROTECT,
        related_name="purchase_items",
    )

    cardboard = models.ForeignKey(
        CardboardGrade,
        on_delete=models.PROTECT,
        related_name="order_items",
    )

    price_list_item = models.ForeignKey(
        CardboardPriceListItem,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="order_items",
    )

    sheet_length = models.PositiveIntegerField()

    sheet_width = models.PositiveIntegerField()

    quantity = models.PositiveIntegerField()

    price_per_1000_m2 = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = [
            "order",
            "id",
        ]

    def __str__(self):
        return (
            f"{self.order} | "
            f"{self.cardboard.index} | "
            f"{self.sheet_length}x{self.sheet_width} | "
            f"{self.quantity}"
        )

    @property
    def sheet_area_m2(self):
        return (
            Decimal(self.sheet_length)
            * Decimal(self.sheet_width)
            / Decimal("1000000")
        )

    @property
    def total_area_m2(self):
        return (
            self.sheet_area_m2
            * Decimal(self.quantity)
        )

    @property
    def value(self):
        return (
            self.total_area_m2
            * Decimal(self.price_per_1000_m2)
            / Decimal("1000")
        ).quantize(Decimal("0.01"))


# ============================================================
# MATERIAL ALLOCATION
# ============================================================

class MaterialAllocation(models.Model):

    class Source(models.TextChoices):
        STOCK = "STOCK", "Magazyn"
        PURCHASE = "PURCHASE", "Zakup"

    requirement = models.ForeignKey(
        MaterialRequirement,
        on_delete=models.CASCADE,
        related_name="allocations",
    )

    source = models.CharField(
        max_length=16,
        choices=Source.choices,
    )

    quantity = models.PositiveIntegerField(
        help_text="Ilość arkuszy przeznaczonych na zlecenie",
    )

    # ręcznie wskazana istniejąca partia
    stock_supply = models.ForeignKey(
        "warehouse.StockSupply",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="order_material_allocations",
    )

    # albo zakup pod to zlecenie
    cardboard_order_item = models.ForeignKey(
        CardboardOrderItem,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="material_allocations",
    )

    notes = models.TextField(
        blank=True,
        default="",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="material_allocations",
    )

    class Meta:
        ordering = [
            "requirement",
            "id",
        ]

        constraints = [
            models.CheckConstraint(
                check=(
                    (
                        Q(source="STOCK")
                        & Q(stock_supply__isnull=False)
                        & Q(cardboard_order_item__isnull=True)
                    )
                    |
                    (
                        Q(source="PURCHASE")
                        & Q(stock_supply__isnull=True)
                        & Q(cardboard_order_item__isnull=False)
                    )
                ),
                name="orders_valid_material_allocation_source",
            ),
        ]

    def clean(self):
        super().clean()

        if self.source == self.Source.STOCK:
            if not self.stock_supply_id:
                raise ValidationError(
                    {
                        "stock_supply":
                            "Dla źródła MAGAZYN należy wskazać partię."
                    }
                )

            if self.cardboard_order_item_id:
                raise ValidationError(
                    "Dla źródła MAGAZYN nie można wskazać zakupu."
                )

        if self.source == self.Source.PURCHASE:
            if not self.cardboard_order_item_id:
                raise ValidationError(
                    {
                        "cardboard_order_item":
                            "Dla źródła ZAKUP należy wskazać pozycję zamówienia."
                    }
                )

            if self.stock_supply_id:
                raise ValidationError(
                    "Dla źródła ZAKUP nie można wskazać partii magazynowej."
                )

    def __str__(self):
        return (
            f"{self.requirement} | "
            f"{self.get_source_display()} | "
            f"{self.quantity}"
        )


class CustomerOrderSequence(models.Model):

    year = models.PositiveSmallIntegerField(
        unique=True,
    )

    last_number = models.PositiveIntegerField(
        default=0,
    )

    def __str__(self):
        return f"{self.year}: {self.last_number}"


class MaterialRequirementScore(models.Model):

    requirement = models.ForeignKey(
        "MaterialRequirement",
        on_delete=models.CASCADE,
        related_name="scores",
    )

    position_mm = models.PositiveIntegerField(
        verbose_name="Pozycja bigu [mm]",
        help_text="Pozycja liczona na szerokości arkusza.",
    )

    class Meta:
        ordering = [
            "position_mm",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "requirement",
                    "position_mm",
                ],
                name="orders_unique_requirement_score",
            ),
        ]

    def __str__(self):
        return f"{self.position_mm} mm"

    def clean(self):
        super().clean()

        if not self.requirement_id:
            return

        width = self.requirement.sheet_width

        if not width:
            return

        if self.position_mm <= 0:
            raise ValidationError(
                {
                    "position_mm":
                        "Pozycja bigu musi być większa od 0."
                }
            )

        if self.position_mm >= width:
            raise ValidationError(
                {
                    "position_mm":
                        (
                            f"Big musi znajdować się wewnątrz "
                            f"szerokości arkusza ({width} mm)."
                        )
                }
            )


class CardboardOrderItemScore(models.Model):

    order_item = models.ForeignKey(
        "CardboardOrderItem",
        on_delete=models.CASCADE,
        related_name="scores",
    )

    position_mm = models.PositiveIntegerField()

    class Meta:
        ordering = [
            "position_mm",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "order_item",
                    "position_mm",
                ],
                name="orders_unique_order_item_score",
            ),
        ]

    def __str__(self):
        return f"{self.position_mm} mm"
