from django.db import IntegrityError, transaction
from warehouse.models import Product
from warehouse.services.naming import build_product_name
from django.db.models import Q


def safe_get_or_create_product(customer, flute, dimensions, extra=""):
    name = build_product_name(customer, flute, dimensions, extra)
    print("created name:", name)
    try:
        with transaction.atomic():
            product, _ = Product.objects.get_or_create(
                name=name,
                defaults={
                    # "dimensions": dimensions,
                    "flute": flute,
                    "gsm": 0,
                }
            )
            print('sgcop returns:', product)
            return product
    except IntegrityError:
        # jeśli drugi proces zdążył wstawić
        return Product.objects.get(name=name)


from django.db.models import Exists, F, OuterRef, Q
from warehouse.models import Product, ProductPackaging
from orders.models import ProductMaterialRequirement


def products_queryset(search="", status="all"):
    packaging_ok = ProductPackaging.objects.filter(
        product_id=OuterRef("pk"), palette__isnull=False,
        columns__gt=0, layers__gt=0, qty_per_pack__gt=0,
        qty_per_pallet=F("columns") * F("layers") * F("qty_per_pack"),
    )
    material_ok = ProductMaterialRequirement.objects.filter(
        product_id=OuterRef("pk"), sheet_length__gt=0,
        sheet_width__gt=0, pieces_per_sheet__gt=0,
        layers__gt=0, min_gsm__gt=0, min_ect__gt=0,
    ).exclude(flute__isnull=True).exclude(flute="").exclude(cover__isnull=True).exclude(cover="")

    qs = Product.objects.annotate(
        has_valid_packaging=Exists(packaging_ok),
        has_valid_material=Exists(material_ok),
    )
    search = search.strip()
    if search:
        qs = qs.filter(
            Q(name__icontains=search) | Q(alter_name__icontains=search)
            | Q(dimensions__icontains=search) | Q(flute__icontains=search)
        )
    if status == "complete":
        qs = qs.filter(has_valid_packaging=True, has_valid_material=True)
    elif status == "missing":
        qs = qs.filter(Q(has_valid_packaging=False) | Q(has_valid_material=False))
    elif status == "packaging":
        qs = qs.filter(has_valid_packaging=False)
    elif status == "material":
        qs = qs.filter(has_valid_material=False)
    return qs.order_by("name", "pk")


def summarize_product(product):
    packaging = getattr(product, "packaging", None)
    material = getattr(product, "material_requirement_template", None)
    packaging_missing = []
    material_missing = []

    if packaging is None:
        packaging_missing.append("Brak konfiguracji pakowania")
    else:
        if not packaging.palette_id:
            packaging_missing.append("Brak palety")
        if not packaging.columns:
            packaging_missing.append("Brak liczby słupków")
        if not packaging.layers:
            packaging_missing.append("Brak liczby warstw")
        if not packaging.qty_per_pack:
            packaging_missing.append("Brak liczby sztuk w paczce")
        expected = packaging.columns * packaging.layers * packaging.qty_per_pack
        if expected > 0 and packaging.qty_per_pallet != expected:
            packaging_missing.append("Niezgodna liczba sztuk na palecie")

    if material is None:
        material_missing.append("Brak wymagań materiałowych")
    else:
        checks = (
            (material.sheet_length, "Brak długości arkusza"),
            (material.sheet_width, "Brak szerokości arkusza"),
            (material.pieces_per_sheet, "Brak liczby produktów z arkusza"),
            (material.layers, "Brak liczby warstw"),
            ((material.flute or "").strip(), "Brak fali"),
            (material.min_gsm, "Brak minimalnej gramatury"),
            (material.min_ect, "Brak minimalnego ECT"),
            ((material.cover or "").strip(), "Brak pokrycia"),
        )
        material_missing = [message for value, message in checks if not value]

    return {
        "product": product,
        "packaging": packaging,
        "material": material,
        "packaging_missing": packaging_missing,
        "material_missing": material_missing,
        "missing_count": len(packaging_missing) + len(material_missing),
        "complete": not packaging_missing and not material_missing,
    }
