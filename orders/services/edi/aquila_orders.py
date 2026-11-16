from django.core.exceptions import ValidationError

from orders.services.edi.aquila import (
    AquilaOrder,
    AquilaScores,
    build_xml,
    send_order,
)

from orders.services.scores import (
    scores_as_segments,
)


def is_aquila_provider(provider):
    name = (
        str(getattr(provider, "name", "") or "")
        .strip()
        .upper()
    )

    shortcut = (
        str(getattr(provider, "shortcut", "") or "")
        .strip()
        .upper()
    )

    return (
        name == "AQUILA"
        or shortcut == "AQ"
        or shortcut == "AQUILA"
    )


def build_aquila_scores(requirement):
    """
    Requirement przechowuje pozycje absolutne,
    ale Aquila oczekuje kolejne odcinki.

    np.
        pozycje: 111, 333
        szerokość: 444

    -> EDI:
        111 / 222 / 111
    """

    scores_value = scores_as_segments(
        requirement
    )

    if not scores_value:
        return AquilaScores.no_scores(
            width=requirement.sheet_width
        )

    values = [
        int(value)
        for value in scores_value.split("/")
        if value
    ]

    return AquilaScores.regular(
        values
    )


def build_aquila_order(
    *,
    requirement,
    offer,
    order_number,
    delivery_date,
):
    if not offer.get("grade"):
        raise ValidationError(
            "Oferta nie zawiera gatunku tektury."
        )

    if not delivery_date:
        raise ValidationError(
            "Podaj oczekiwaną datę dostawy."
        )

    return AquilaOrder(
        board_grade=offer["grade"].index,

        order_number=order_number,

        length=requirement.sheet_length,
        width=requirement.sheet_width,

        quantity=(
            requirement.required_sheet_quantity
        ),

        delivery_date=delivery_date.strftime(
            "%Y%m%d"
        ),

        webshop_comment=(
            requirement
            .customer_order
            .order_number
        )[:30],

        scores=build_aquila_scores(
            requirement
        ),
    )


def build_aquila_xml_preview(
    *,
    requirement,
    offer,
    order_number,
    delivery_date,
):
    edi_order = build_aquila_order(
        requirement=requirement,
        offer=offer,
        order_number=order_number,
        delivery_date=delivery_date,
    )

    return build_xml(
        edi_order
    )


def send_aquila_purchase(
    *,
    requirement,
    offer,
    order_number,
    delivery_date,
):
    edi_order = build_aquila_order(
        requirement=requirement,
        offer=offer,
        order_number=order_number,
        delivery_date=delivery_date,
    )

    result = send_order(
        edi_order
    )

    status_code = result.get(
        "status_code"
    )

    if (
        not status_code
        or status_code < 200
        or status_code >= 300
    ):
        raise ValidationError(
            (
                "Aquila odrzuciła zamówienie. "
                f"HTTP {status_code or 'brak'}: "
                f"{result.get('response_text', '')}"
            )
        )

    return result
