from django.conf import settings
from django.core.exceptions import ValidationError

from orders.services.edi.jassboard import (
    JassBoardClient,
)

from orders.services.scores import (
    scores_as_segments,
)


# ============================================================
# PROVIDER
# ============================================================

def is_jassboard_provider(provider):
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
        name in ("JASS", "JASSBOARD")
        or shortcut in ("JASS", "JASSBOARD")
    )


# ============================================================
# BOARD TYPE
# ============================================================

def resolve_jassboard_board_type(board_grade_code):
    """
    JassBoard:

    2... -> TF2
    3... -> TF35
    5... -> TF35
    """

    code = (
        str(board_grade_code or "")
        .strip()
        .upper()
    )

    if not code:
        raise ValidationError(
            "Brak kodu składu JassBoard."
        )

    if code.startswith("2"):
        return "TF2"

    if code.startswith(("3", "5")):
        return "TF35"

    raise ValidationError(
        f"Nieznany typ składu JassBoard: {code}"
    )


# ============================================================
# BIGOWANIE
# ============================================================

def build_jassboard_scores(requirement):
    """
    JassBoard oczekuje bigów jako odcinki rozdzielone /.

    np.
        pozycje absolutne:
            111, 333

        szerokość:
            444

        wynik:
            111/222/111
    """

    scores = scores_as_segments(
        requirement
    )

    return scores or ""


# ============================================================
# PAYLOAD
# ============================================================

def build_jassboard_order(
    *,
    requirement,
    offer,
    order_number,
    delivery_date,
):
    if not delivery_date:
        raise ValidationError(
            "Podaj oczekiwaną datę wysyłki."
        )

    grade = offer.get("grade")

    if not grade:
        raise ValidationError(
            "Oferta nie zawiera składu tektury."
        )

    board_grade_code = (
            getattr(grade, "index", None)
            or getattr(grade, "code", None)
            or str(grade)
    )

    if not board_grade_code:
        raise ValidationError(
            "Nie udało się ustalić kodu składu JassBoard."
        )

    board_type = resolve_jassboard_board_type(
        board_grade_code
    )

    bigi = build_jassboard_scores(
        requirement
    )

    payload = {
        "AdresDostawyErpId":
            settings.JASSBOARD_ADDRESS_ERP_ID,

        "TypPozycji":
            board_type,

        "NrZamKlienta":
            str(order_number)[:19],

        "NrPozZamKlienta":
            "1",

        "IndeksKlienta":
            "",

        "Gramatura":
            0,

        "MarkaTektury":
            "",

        "Szerokosc":
            int(requirement.sheet_width),

        "Dlugosc":
            int(requirement.sheet_length),

        "Sklad":
            str(board_grade_code),

        "Bigi":
            bigi,

        "IloscKg":
            0,

        "IloscMetrow":
            0,

        "IloscArkuszy":
            int(
                requirement.required_sheet_quantity
            ),

        "CertyfikatFsc":
            "",

        "Expres":
            False,

        "NumerOfertySpecjalnej":
            "",

        "Uwagi":
            str(
                requirement
                .customer_order
                .order_number
            )[:200],

        "UtworzonoZaPomoca":
            "PAKER",

        "OczekiwanaDataWysylki":
            delivery_date.isoformat(),
    }

    return payload


# ============================================================
# PREVIEW
# ============================================================

def build_jassboard_preview(
    *,
    requirement,
    offer,
    order_number,
    delivery_date,
):
    return build_jassboard_order(
        requirement=requirement,
        offer=offer,
        order_number=order_number,
        delivery_date=delivery_date,
    )


# ============================================================
# SEND
# ============================================================

def send_jassboard_purchase(
    *,
    requirement,
    offer,
    order_number,
    delivery_date,
):
    payload = build_jassboard_order(
        requirement=requirement,
        offer=offer,
        order_number=order_number,
        delivery_date=delivery_date,
    )

    client = JassBoardClient()

    result = client.add_order(
        payload
    )

    return result