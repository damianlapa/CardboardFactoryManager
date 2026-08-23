from warehousemanager.models import Punch


PUNCH_TYPE_LABELS = {
    "471": "FEFCO 471",
    "427": "FEFCO 427",
    "426": "FEFCO 426",
    "421": "FEFCO 421",
    "201": "FEFCO 201",
    "SWT": "Spody, wieka, tacki",
    "KR": "Krata",
    "NR": "Narożnik",
    "PDK": "Pozostałe do klejenia",
    "WK": "Wkład",
    "INNE": "Inne",
}


def get_punch_types():
    return [
        {
            "value": value,
            "label": label,
        }
        for value, label in PUNCH_TYPE_LABELS.items()
    ]


def get_punch_list(*, include_inactive=False):
    punches = (
        Punch.objects
        .all()
        .prefetch_related("customers")
        .order_by(
            "type",
            "type_letter",
            "type_num",
        )
    )

    if not include_inactive:
        punches = punches.filter(active=True)

    rows = []

    for punch in punches:
        if punch.wave_direction:
            format_width = punch.size_one
            format_height = punch.size_two
        else:
            format_width = punch.size_two
            format_height = punch.size_one

        format_label = None

        if (
            format_width is not None
            and format_height is not None
        ):
            format_label = (
                f"{format_width} × {format_height}"
            )

        rows.append({
            "punch": punch,

            "identifier": punch.punch_name,

            "dimensions": {
                "width": punch.dimension_one,
                "length": punch.dimension_two,
                "height": punch.dimension_three,
            },

            "format": {
                "width": format_width,
                "height": format_height,
                "label": format_label,
            },

            "customers": list(
                punch.customers.all()
            ),

            "type_label": PUNCH_TYPE_LABELS.get(
                punch.type,
                punch.type,
            ),
        })

    return rows