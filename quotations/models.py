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
        default=datetime.date.today(),
    )

    class Meta:
        verbose_name = "Wycena"
        verbose_name_plural = "Wyceny"
        ordering = ["-date", "-pk"]

    def __str__(self):
        return f"Wycena #{self.pk} | {self.customer} | {self.date}"


class QuotationItem(models.Model):
    quotation = models.ForeignKey(
        Quotation,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="Wycena",
    )
    packaging_type = models.ForeignKey(
        FefcoType,
        on_delete=models.PROTECT,
        related_name="quotation_items",
        verbose_name="Typ opakowania FEFCO",
    )
    width = models.PositiveIntegerField(
        "Szerokość W (mm)", null=True, blank=True
    )
    length = models.PositiveIntegerField(
        "Długość L (mm)", null=True, blank=True
    )
    height = models.PositiveIntegerField(
        "Wysokość H (mm)", null=True, blank=True
    )
    material = models.ForeignKey(
        "warehouse.PriceListItem",
        on_delete=models.PROTECT,
        related_name="quotation_items",
        verbose_name="Materiał z cennika",
    )
    hours = models.DecimalField(
        "Liczba godzin",
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    price = models.DecimalField(
        "Cena",
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )

    class Meta:
        verbose_name = "Pozycja wyceny"
        verbose_name_plural = "Pozycje wyceny"
        ordering = ["pk"]

    def __str__(self):
        return (
            f"{self.packaging_type} | "
            f"{self.width} × {self.length} × {self.height} mm | "
            f"{self.material}"
        )
