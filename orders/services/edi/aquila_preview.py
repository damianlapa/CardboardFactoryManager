from orders.services.edi.aquila import (
    AquilaOrder,
    AquilaScores,
    build_xml,
)

from orders.services.scores import (
    scores_as_segments,
)


def build_aquila_xml_preview(
    *,
    requirement,
    offer,
    order_number,
    delivery_date,
):
    """
    Buduje XML Aquila bez zapisu do bazy
    i bez wysyłania do EDI.
    """

    scores_value = scores_as_segments(
        requirement
    )

    if scores_value:
        score_values = [
            int(value)
            for value in scores_value.split("/")
            if value
        ]

        scores = AquilaScores.regular(
            score_values
        )

    else:
        scores = AquilaScores.no_scores(
            width=requirement.sheet_width
        )

    edi_order = AquilaOrder(
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

        scores=scores,
    )

    return build_xml(
        edi_order
    )
