import xml.etree.ElementTree as ET

from dataclasses import dataclass, field
from typing import Optional

import requests


# ============================================================
# KONFIGURACJA VPK / AQUILA
# ============================================================

EDI_URL = (
    "http://edi.vpkgroup.com/sap/xi/adapter_plain"
    "?service=AQUILA"
    "&namespace=http://vpk.be/AQUILA/SalesOrder"
    "&interface=SalesOrder_oa"
    "&qos=EO"
)

EDI_USERNAME = "WPISZ_LOGIN"
EDI_PASSWORD = "WPISZ_HASLO"


CUSTOMER_NUMBER = "38465"
SHIP_TO = "83867"

NAMESPACE = "http://vpk.be/AQUILA/SalesOrder"


# ============================================================
# MODELE DANYCH
# ============================================================

@dataclass
class AquilaScores:
    """
    Dane dotyczące bigowania.

    score_values:
        długości poszczególnych odcinków w poprzek WidthX.

    Przykład:
        szerokość 367
        2 bigi regularne:
        [80, 207, 80]
    """

    score_values: list[int] = field(default_factory=list)

    scored: str = "809"
    score_type: str = "0"

    # M  = big jednopunktowy
    # MM = point-to-point
    ril_type: Optional[str] = None

    @classmethod
    def no_scores(cls, width: int):
        """
        Format bez bigów - wariant Scored=809.

        Dokumentacja:
            WidthX = 745
            Scores Scored=809 NumberOfScores=1
            Score = 745
        """
        return cls(
            score_values=[width],
            scored="809",
            score_type="0",
        )

    @classmethod
    def regular(cls, values: list[int]):
        """
        Bigi regularne.

        np.:
            width = 367
            values = [80, 207, 80]

        oznacza 2 linie bigujące.
        """
        return cls(
            score_values=values,
            scored="809",
            score_type="0",
        )

    @classmethod
    def point(cls, values: list[int], score_type: str = "3"):
        """
        Bigowanie punktowe.

        score_type pozostawiamy konfigurowalny,
        ponieważ dokumentacja pokazuje zarówno '3'
        jak i '3 pkt.'.
        """
        return cls(
            score_values=values,
            scored="809",
            score_type=score_type,
        )

    @classmethod
    def single_point(cls, values: list[int]):
        """
        Big jednopunktowy.

        ril_type = M
        """
        return cls(
            score_values=values,
            scored="809",
            score_type="0",
            ril_type="M",
        )

    @classmethod
    def point_to_point(cls, values: list[int]):
        """
        Biga point-to-point.

        ril_type = MM
        """
        return cls(
            score_values=values,
            scored="809",
            score_type="0",
            ril_type="MM",
        )


@dataclass
class AquilaOrder:
    board_grade: str
    order_number: str

    length: int
    width: int

    quantity: int
    delivery_date: str

    webshop_comment: str = "TEST"

    scores: Optional[AquilaScores] = None

    customer_number: str = CUSTOMER_NUMBER
    ship_to: str = SHIP_TO


# ============================================================
# WALIDACJA
# ============================================================

def validate_order(order: AquilaOrder):
    if not order.board_grade:
        raise ValueError("BoardGrade jest wymagany.")

    if not order.order_number:
        raise ValueError("Numer zamówienia jest wymagany.")

    if order.quantity <= 0:
        raise ValueError("Ilość musi być większa od zera.")

    if order.width < 250:
        raise ValueError(
            "Szerokość arkusza nie może być mniejsza niż 250 mm."
        )

    if order.length < 500:
        raise ValueError(
            "Długość arkusza nie może być mniejsza niż 500 mm."
        )

    # VPK:
    # max 5000 x 2400
    # LUB 2400 x 2760

    dimensions_ok = (
        (
            order.length <= 5000
            and order.width <= 2400
        )
        or
        (
            order.length <= 2400
            and order.width <= 2760
        )
    )

    if not dimensions_ok:
        raise ValueError(
            "Format przekracza maksymalny dopuszczalny wymiar VPK."
        )

    if len(order.webshop_comment) > 30:
        raise ValueError(
            "WebshopComment może mieć maksymalnie 30 znaków."
        )

    if order.scores:
        validate_scores(
            width=order.width,
            scores=order.scores,
        )


def validate_scores(
    *,
    width: int,
    scores: AquilaScores,
):
    if not scores.score_values:
        raise ValueError(
            "Dla Scored=809 musi być podany przynajmniej jeden Score."
        )

    if any(value <= 0 for value in scores.score_values):
        raise ValueError(
            "Wszystkie wartości Score muszą być większe od zera."
        )

    score_sum = sum(scores.score_values)

    if score_sum != width:
        raise ValueError(
            f"Suma Score ({score_sum}) "
            f"nie zgadza się z WidthX ({width})."
        )


# ============================================================
# XML
# ============================================================

def build_xml(order: AquilaOrder) -> bytes:
    validate_order(order)

    if order.scores is None:
        order.scores = AquilaScores.no_scores(
            width=order.width,
        )

    quantity_m2 = (
        order.length
        * order.width
        * order.quantity
        / 1_000_000
    )

    root = ET.Element(
        f"{{{NAMESPACE}}}SalesOrder_aquila"
    )

    # ========================================================
    # HEADER
    # ========================================================

    header = ET.SubElement(
        root,
        "Header",
    )

    ET.SubElement(
        header,
        "DeliveryDate",
    ).text = order.delivery_date

    ET.SubElement(
        header,
        "CustomerPurchaseOrder",
    ).text = order.order_number

    ET.SubElement(
        header,
        "ShipTo",
    ).text = order.ship_to

    ET.SubElement(
        header,
        "CumulativeQuantity",
        UnitOfMeasure="",
    )

    ET.SubElement(
        header,
        "CustomerNumber",
    ).text = order.customer_number

    ET.SubElement(
        header,
        "LabelType",
    )

    ET.SubElement(
        header,
        "Rate",
        UnitOfMeasure="",
    )

    # ========================================================
    # ITEMS
    # ========================================================

    items = ET.SubElement(
        root,
        "Items",
    )

    item = ET.SubElement(
        items,
        "Item",
    )

    ET.SubElement(
        item,
        "CustomerReferenceLineNumber",
    ).text = "1"

    ET.SubElement(
        item,
        "MaterialNumber",
    ).text = "sheets"

    ET.SubElement(
        item,
        "BoardGrade",
    ).text = order.board_grade

    ET.SubElement(
        item,
        "MaterialDescription",
    ).text = (
        f"({order.length}x{order.width})"
    )

    # brak Price - świadomie

    ET.SubElement(
        item,
        "Remark",
    )

    ET.SubElement(
        item,
        "LabelType",
    )

    ET.SubElement(
        item,
        "MaxOverDeliveryTotal",
    )

    ET.SubElement(
        item,
        "MaxUnderDeliveryTotal",
    )

    ET.SubElement(
        item,
        "MaterialDescription",
    ).text = (
        f"{order.board_grade},"
        f"{order.length}x{order.width}"
    )

    # ========================================================
    # FORMAT
    # ========================================================

    sheet = ET.SubElement(
        item,
        "Sheet",
    )

    ET.SubElement(
        sheet,
        "WidthX",
    ).text = str(order.width)

    ET.SubElement(
        item,
        "WidthY",
    ).text = "0"

    ET.SubElement(
        item,
        "Length",
    ).text = str(order.length)

    # ========================================================
    # ILOŚĆ
    # ========================================================

    ET.SubElement(
        item,
        "QuantityPce",
    ).text = str(order.quantity)

    ET.SubElement(
        item,
        "QuantityM2",
    ).text = f"{quantity_m2:.3f}"

    # ========================================================
    # BIGOWANIE
    # ========================================================

    add_scores_xml(
        item=item,
        scores=order.scores,
    )

    # ========================================================
    # KOMENTARZ
    # ========================================================

    ET.SubElement(
        item,
        "WebshopComment",
    ).text = order.webshop_comment

    # ========================================================
    # DATY
    # ========================================================

    ET.SubElement(
        item,
        "RequestedDelDate",
    ).text = order.delivery_date

    ET.SubElement(
        item,
        "ProposedDelDate",
    ).text = order.delivery_date

    return ET.tostring(
        root,
        encoding="utf-8",
        xml_declaration=True,
    )


def add_scores_xml(
    *,
    item,
    scores: AquilaScores,
):
    scores_element = ET.SubElement(
        item,
        "Scores",
        Scored=str(scores.scored),
        NumberOfScores=str(
            len(scores.score_values)
        ),
    )

    for value in scores.score_values:
        ET.SubElement(
            scores_element,
            "Score",
        ).text = str(value)

    if scores.ril_type:
        ET.SubElement(
            item,
            "ril_type",
        ).text = scores.ril_type

    ET.SubElement(
        item,
        "score_type",
    ).text = str(scores.score_type)


# ============================================================
# WYSYŁKA
# ============================================================

def send_order(order: AquilaOrder):
    xml_body = build_xml(order)

    response = requests.post(
        EDI_URL,
        data=xml_body,
        auth=(
            EDI_USERNAME,
            EDI_PASSWORD,
        ),
        headers={
            "Content-Type": "application/xml; charset=utf-8",
            "Accept": "*/*",
        },
        timeout=30,
    )

    return {
        "status_code": response.status_code,
        "reason": response.reason,
        "response_text": response.text,
        "xml": xml_body.decode("utf-8"),
    }