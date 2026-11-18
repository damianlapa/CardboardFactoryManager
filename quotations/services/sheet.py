from decimal import Decimal, ROUND_CEILING

from orders.models import CardboardPriceListItem

from ..models import FefcoType, QuotationSheetRule
from ..sheet_forms import SheetCalculationForm


def calculate_sheet(params):
    form = SheetCalculationForm(params)

    if not form.is_valid():
        return {
            "ok": False,
            "message": (
                "Uzupełnij FEFCO, materiał, dodatnie "
                "wymiary pudełka i liczbę produktów z arkusza."
            ),
        }

    data = form.cleaned_data

    if data["products_per_sheet"] not in (
        Decimal("1"),
        Decimal("0.5"),
    ):
        return {
            "ok": False,
            "message": (
                "Dla kilku produktów z arkusza "
                "wpisz format ręcznie."
            ),
        }

    fefco = FefcoType.objects.filter(
        pk=data["packaging_type"],
    ).first()

    material = (
        CardboardPriceListItem.objects
        .select_related("cardboard")
        .filter(pk=data["material"])
        .first()
    )

    if not fefco or not material:
        return {
            "ok": False,
            "message": "Nie znaleziono FEFCO lub materiału.",
        }

    code = fefco.code.strip().zfill(4)

    if code != "0201":
        return {
            "ok": False,
            "message": (
                f"FEFCO {code}: wzór nie jest jeszcze "
                "podłączony. Wpisz arkusz ręcznie."
            ),
        }

    flute = material.cardboard.flute.strip().upper()

    rule = QuotationSheetRule.objects.filter(
        packaging_type=fefco,
        flute=flute,
    ).first()

    if not rule:
        return {
            "ok": False,
            "message": (
                f"Brak ustawień dla FEFCO {code}, "
                f"fala {flute}."
            ),
        }

    box_length = Decimal(data["length"])
    box_width = Decimal(data["width"])
    box_height = Decimal(data["height"])

    length_plus_width = box_length + box_width

    halves = (
        length_plus_width > Decimal("1250")
        or data["products_per_sheet"] == Decimal("0.5")
    )

    # S — szerokość arkusza, wymiar obwodowy.
    if halves:
        sheet_width = (
            length_plus_width
            + rule.glue_flap
            + rule.width_allowance
        )
    else:
        sheet_width = (
            Decimal(2) * length_plus_width
            + rule.glue_flap
            + rule.width_allowance
        )

    # D — długość arkusza, wysokość ściany z klapami.
    sheet_length = (
        box_height
        + box_width
        + rule.length_allowance
    )

    sheet_width = int(
        sheet_width.to_integral_value(
            rounding=ROUND_CEILING,
        )
    )

    sheet_length = int(
        sheet_length.to_integral_value(
            rounding=ROUND_CEILING,
        )
    )

    if not (
        1 <= sheet_width <= 2147483647
        and 1 <= sheet_length <= 2147483647
    ):
        return {
            "ok": False,
            "message": (
                "Obliczony format jest poza zakresem "
                "dopuszczalnych wymiarów."
            ),
        }

    variant = "połówki" if halves else "całe pudełko"

    return {
        "ok": True,
        "sheet_width": sheet_width,
        "sheet_length": sheet_length,
        "products_per_sheet": "0.5" if halves else "1",
        "halves": halves,
        "message": (
            f"S × D: {sheet_width} × {sheet_length} mm "
            f"· {variant} · fala {flute}."
        ),
    }