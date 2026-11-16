from django.core.exceptions import ValidationError

from orders.models import MaterialRequirementScore


def parse_scores(
    value,
    *,
    width=None,
):
    """
    Zamienia zapis kolejnych odcinków na pozycje bigów.

    300/600
        -> [300, 900]

    100/200/100
        -> [100, 300, 400]

    Jeśli podano width:
        suma odcinków musi być równa szerokości arkusza.
    """

    value = (value or "").strip()

    if not value:
        return []

    parts = value.split("/")

    segments = []

    for part in parts:
        part = part.strip()

        if not part:
            raise ValidationError(
                "Niepoprawny zapis bigów."
            )

        try:
            segment = int(part)

        except ValueError:
            raise ValidationError(
                "Bigi muszą być liczbami oddzielonymi znakiem '/'."
            )

        if segment <= 0:
            raise ValidationError(
                "Każdy odcinek musi być większy od 0."
            )

        segments.append(segment)

    # ========================================================
    # CHECK TOTAL WIDTH
    # ========================================================

    total = sum(segments)

    if width is not None and total != width:

        difference = width - total

        if difference > 0:
            message = (
                f"Suma bigów wynosi {total} mm, "
                f"a szerokość arkusza to {width} mm. "
                f"Brakuje {difference} mm."
            )

        else:
            message = (
                f"Suma bigów wynosi {total} mm, "
                f"a szerokość arkusza to {width} mm. "
                f"Przekroczono szerokość o {abs(difference)} mm."
            )

        raise ValidationError(
            message
        )

    # ========================================================
    # CONVERT SEGMENTS TO ABSOLUTE POSITIONS
    # ========================================================

    positions = []
    current_position = 0

    for segment in segments:
        current_position += segment

        positions.append(
            current_position
        )

    # ostatnia wartość oznacza krawędź arkusza,
    # więc nie jest fizycznym bigiem
    if width is not None and positions:
        if positions[-1] == width:
            positions.pop()

    return positions


def save_requirement_scores(
    *,
    requirement,
    value,
):
    positions = parse_scores(
        value,
        width=requirement.sheet_width,
    )

    requirement.scores.all().delete()

    MaterialRequirementScore.objects.bulk_create(
        [
            MaterialRequirementScore(
                requirement=requirement,
                position_mm=position,
            )
            for position in positions
        ]
    )


def scores_as_segments(requirement):
    """
    Zamienia zapisane pozycje bigów z powrotem
    na odcinki używane przez pracowników.

    Dla szerokości 600 i pozycji:
        100, 500

    zwróci:
        100/400/100
    """

    positions = list(
        requirement.scores
        .order_by("position_mm")
        .values_list(
            "position_mm",
            flat=True,
        )
    )

    width = requirement.sheet_width

    if not width:
        return ""

    segments = []

    previous_position = 0

    for position in positions:
        segments.append(
            position - previous_position
        )

        previous_position = position

    # ostatni odcinek od ostatniego bigu do krawędzi
    segments.append(
        width - previous_position
    )

    return "/".join(
        str(segment)
        for segment in segments
    )


def order_item_scores_as_segments(order_item):
    """
    Zamienia snapshot pozycji bigów zapisanych
    przy CardboardOrderItem z powrotem na odcinki.

    Dla:
        width = 600
        positions = [100, 500]

    zwróci:
        "100/400/100"
    """

    positions = list(
        order_item.scores
        .order_by("position_mm")
        .values_list(
            "position_mm",
            flat=True,
        )
    )

    width = order_item.sheet_width

    if not width:
        return ""

    segments = []

    previous_position = 0

    for position in positions:
        segments.append(
            position - previous_position
        )

        previous_position = position

    segments.append(
        width - previous_position
    )

    return "/".join(
        str(segment)
        for segment in segments
    )
