from django.db import models
import datetime
from decimal import Decimal
from django.core.validators import MinValueValidator


class QuotationCustomer(models.Model):
    name = models.CharField(
        "Nazwa firmy",
        max_length=255,
    )

    class Meta:
        verbose_name = "Klient wycen"
        verbose_name_plural = "Klienci wycen"
        ordering = ["name"]

    def __str__(self):
        return self.name


class FefcoType(models.Model):
    code = models.CharField(
        "Kod FEFCO",
        max_length=4,
        unique=True,
    )
    name = models.CharField(
        "Nazwa opakowania",
        max_length=255,
        blank=True,
    )

    class Meta:
        verbose_name = "Typ opakowania FEFCO"
        verbose_name_plural = "Typy opakowań FEFCO"
        ordering = ["code"]

    def __str__(self):
        if self.name:
            return f"FEFCO {self.code} — {self.name}"
        return f"FEFCO {self.code}"


class Quotation(models.Model):
    customer = models.ForeignKey(
        QuotationCustomer,
        on_delete=models.PROTECT,
        related_name="quotations",
        verbose_name="Klient",
    )
    date = models.DateField(
        "Data wyceny",
        default=datetime.date.today,
    )

    class Meta:
        verbose_name = "Wycena"
        verbose_name_plural = "Wyceny"
        ordering = ["-date", "-pk"]

    def __str__(self):
        return f"Wycena #{self.pk} | {self.customer} | {self.date}"


class QuotationItem(models.Model):
    quotation = models.ForeignKey("Quotation", on_delete=models.CASCADE, related_name="items", verbose_name="Wycena")
    packaging_type = models.ForeignKey("FefcoType", on_delete=models.PROTECT, related_name="quotation_items", verbose_name="Typ FEFCO")
    width = models.PositiveIntegerField("W (mm)")
    length = models.PositiveIntegerField("L (mm)")
    height = models.PositiveIntegerField("H (mm)")
    quantity = models.PositiveIntegerField("Ilość sztuk", default=0)
    material = models.ForeignKey(
        "orders.CardboardPriceListItem",
        on_delete=models.PROTECT,
        related_name="quotation_items",
        verbose_name="Materiał",
    )
    products_per_sheet = models.DecimalField(
        "Produktów z arkusza",
        max_digits=8,
        decimal_places=2,
        default=Decimal("1.00"),
        validators=[
            MinValueValidator(Decimal("0.01")),
        ],
    )
    sheet_width = models.PositiveIntegerField("Szerokość arkusza (mm)", default=0)
    sheet_length = models.PositiveIntegerField("Długość arkusza (mm)", default=0)
    material_price = models.DecimalField("Cena za materiał", max_digits=12, decimal_places=2, default=Decimal("0.00"), validators=[MinValueValidator(Decimal("0.00"))])
    # Zachowane stare pole: istniejące dane nie są usuwane ani przeliczane.
    hours = models.DecimalField("Dotychczasowe godziny", max_digits=10, decimal_places=2, default=Decimal("0.00"), validators=[MinValueValidator(Decimal("0.00"))])
    hours_manual = models.BooleanField(
        "Godziny wpisane ręcznie",
        default=False,
    )
    price = models.DecimalField("Końcowa cena opakowania", max_digits=12, decimal_places=2, default=Decimal("0.00"), validators=[MinValueValidator(Decimal("0.00"))])

    class Meta:
        ordering = ["pk"]
        verbose_name = "Pozycja wyceny"
        verbose_name_plural = "Pozycje wyceny"

    def __str__(self):
        return f"{self.packaging_type} | {self.width} × {self.length} × {self.height}"


class QuotationWorkEntry(models.Model):
    item = models.ForeignKey(QuotationItem, on_delete=models.CASCADE, related_name="work_entries")
    work_station = models.ForeignKey("production.WorkStation", on_delete=models.PROTECT, verbose_name="Stanowisko")
    employees = models.PositiveIntegerField("Liczba pracowników", default=1, validators=[MinValueValidator(1)])
    hours = models.DecimalField("Liczba godzin", max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))])

    class Meta:
        ordering = ["pk"]
        verbose_name = "Wpis godzin wyceny"
        verbose_name_plural = "Wpisy godzin wyceny"


class QuotationSheetRule(models.Model):
    FLUTE_CHOICES = [
        ("B", "B"),
        ("C", "C"),
        ("E", "E"),
        ("EB", "EB"),
        ("BC", "BC"),
    ]

    packaging_type = models.ForeignKey(
        FefcoType,
        on_delete=models.PROTECT,
        related_name="sheet_rules",
        verbose_name="Typ FEFCO",
    )
    flute = models.CharField(
        "Fala",
        max_length=2,
        choices=FLUTE_CHOICES,
    )
    glue_flap = models.DecimalField(
        "Zakładka (mm)",
        max_digits=7,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal("0.00")),
        ],
    )
    length_allowance = models.DecimalField(
        "Dodatek do długości (mm)",
        max_digits=7,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal("0.00")),
        ],
    )
    width_allowance = models.DecimalField(
        "Dodatek do szerokości (mm)",
        max_digits=7,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal("0.00")),
        ],
    )

    class Meta:
        verbose_name = "Ustawienie arkusza"
        verbose_name_plural = "Ustawienia arkuszy"
        ordering = ["packaging_type__code", "flute"]

        constraints = [
            models.UniqueConstraint(
                fields=["packaging_type", "flute"],
                name="quotations_unique_sheet_rule",
            ),
        ]

    def __str__(self):
        return (
            f"FEFCO {self.packaging_type.code} "
            f"| fala {self.flute}"
        )


class QuotationProcessProfile(models.Model):
    code = models.CharField(
        "Kod procesu",
        max_length=32,
        unique=True,
    )
    setup_minutes = models.DecimalField(
        "Przygotowanie (min)",
        max_digits=8,
        decimal_places=2,
        default=Decimal("20.00"),
        validators=[MinValueValidator(0)],
    )
    setup_workers = models.PositiveIntegerField(
        "Obsada przygotowania",
        default=2,
        validators=[MinValueValidator(1)],
    )
    run_workers = models.PositiveIntegerField(
        "Obsada pracy",
        default=2,
        validators=[MinValueValidator(1)],
    )
    first_batch_quantity = models.PositiveIntegerField(
        "Pierwsza partia (arkusze)",
        default=100,
        validators=[MinValueValidator(1)],
    )
    full_speed_area = models.DecimalField(
        "Pełne tempo do powierzchni (m²)",
        max_digits=8,
        decimal_places=3,
        default=Decimal("1.200"),
        validators=[
            MinValueValidator(Decimal("0.001")),
        ],
    )
    min_speed_area = models.DecimalField(
        "Minimalne tempo od powierzchni (m²)",
        max_digits=8,
        decimal_places=3,
        default=Decimal("4.000"),
        validators=[
            MinValueValidator(Decimal("0.001")),
        ],
    )

    def __str__(self):
        return self.code


class QuotationProcessFluteRule(models.Model):
    profile = models.ForeignKey(
        QuotationProcessProfile,
        on_delete=models.CASCADE,
        related_name="flute_rules",
    )
    flute = models.CharField(
        "Fala",
        max_length=2,
    )
    first_batch_minutes = models.DecimalField(
        "Pierwsza partia (min)",
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    max_speed = models.DecimalField(
        "Pełne tempo (ark./h)",
        max_digits=10,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal("0.01")),
        ],
    )
    min_speed = models.DecimalField(
        "Minimalne tempo (ark./h)",
        max_digits=10,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal("0.01")),
        ],
    )

    work_station = models.ForeignKey(
        "production.WorkStation",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name="Stanowisko produkcyjne",
    )

    quantity_basis = models.CharField(
        "Wydajność liczona dla",
        max_length=16,
        choices=[
            ("SHEETS", "Arkuszy"),
            ("PRODUCTS", "Gotowych opakowań"),
        ],
        default="SHEETS",
    )

    setup_per_color_minutes = models.DecimalField(
        "Dodatkowe przygotowanie na kolor (min)",
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
    )

    setup_per_pass = models.BooleanField(
        "Przygotowanie przy każdym przelocie",
        default=False,
    )

    first_batch_per_pass = models.BooleanField(
        "Pierwsza partia przy każdym przelocie",
        default=False,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["profile", "flute"],
                name="quotations_unique_process_flute",
            ),
        ]


class QuotationPrintColor(models.Model):
    item = models.ForeignKey(
        "QuotationItem",
        on_delete=models.CASCADE,
        related_name="print_colors",
        verbose_name="Pozycja wyceny",
    )
    color_name = models.CharField(
        "Kolor / kod koloru",
        max_length=100,
    )
    consumption_per_1000 = models.DecimalField(
        "Zużycie na 1000 sztuk",
        max_digits=12,
        decimal_places=4,
        default=Decimal("0.0000"),
        validators=[
            MinValueValidator(Decimal("0.0000")),
        ],
    )

    class Meta:
        ordering = ["pk"]
        verbose_name = "Kolor nadruku wyceny"
        verbose_name_plural = "Kolory nadruku wyceny"

    def __str__(self):
        return self.color_name