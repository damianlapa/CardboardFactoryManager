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
    products_per_sheet = models.PositiveIntegerField("Produktów z arkusza", default=1, validators=[MinValueValidator(1)])
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

