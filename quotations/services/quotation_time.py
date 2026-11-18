from decimal import Decimal

from django.core.exceptions import ValidationError

from .processes import calculate_rotation_time


def calculate_item_rotation_time(item):
    """
    Oblicza czas rotacji bez nadruku dla pozycji wyceny.

    Obsługuje również niezapisaną instancję QuotationItem.
    Nie zapisuje ani nie zmienia pozycji.
    """
    try:
        quantity = Decimal(str(item.quantity))

        products_per_sheet = Decimal(
            str(item.products_per_sheet)
        )

        if (
            not quantity.is_finite()
            or quantity <= 0
            or quantity != quantity.to_integral_value()
        ):
            raise ValueError

        if (
            not products_per_sheet.is_finite()
            or products_per_sheet <= 0
        ):
            raise ValueError

    except (ValueError, ArithmeticError):
        raise ValidationError(
            "Podaj dodatnią całkowitą ilość pudełek "
            "i dodatnią liczbę produktów z arkusza."
        )

    if not item.material_id:
        raise ValidationError(
            "Wybierz materiał przed obliczeniem czasu."
        )

    # Liczba arkuszy, zawsze zaokrąglona w górę.
    #
    # 1000 pudełek / 1 użytek = 1000 arkuszy
    # 1000 pudełek / 2 użytki = 500 arkuszy
    # 1000 pudełek / 0,5 użytku = 2000 arkuszy
    whole_sheets, remainder = divmod(
        quantity,
        products_per_sheet,
    )

    sheet_quantity = (
        int(whole_sheets)
        + int(remainder != 0)
    )

    flute = (
        item.material.cardboard.flute
        .strip()
        .upper()
    )

    result = calculate_rotation_time(
        quantity=sheet_quantity,
        sheet_width=item.sheet_width,
        sheet_length=item.sheet_length,
        flute=flute,
    )

    return {
        **result,
        "product_quantity": int(quantity),
        "sheet_quantity": sheet_quantity,
        "products_per_sheet": products_per_sheet,
        "flute": flute,
    }