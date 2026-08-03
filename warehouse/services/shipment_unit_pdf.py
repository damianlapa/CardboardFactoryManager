from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

import qrcode

from django.conf import settings
from django.core import signing
from django.urls import reverse

from reportlab.graphics.barcode import code128
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import (
    Image as ReportLabImage,
    Paragraph,
    Table,
    TableStyle,
)


class ShipmentUnitPDF:
    PAGE_SIZE = landscape(A4)

    PAGE_MARGIN = 8 * mm

    LABEL_WIDTH = PAGE_SIZE[0] - (2 * PAGE_MARGIN)
    LABEL_HEIGHT = PAGE_SIZE[1] - (2 * PAGE_MARGIN)

    LEFT_COLUMN_WIDTH = 56 * mm
    RIGHT_COLUMN_WIDTH = LABEL_WIDTH - LEFT_COLUMN_WIDTH

    BORDER_WIDTH = 0.35 * mm

    FONT_REGULAR = "DejaVuSans"
    FONT_BOLD = "DejaVuSans-Bold"

    def __init__(self, request, shipment_unit):
        self.request = request
        self.shipment_unit = shipment_unit
        self.order = shipment_unit.order

        self._register_fonts()

        self.buffer = BytesIO()
        self.canvas = Canvas(
            self.buffer,
            pagesize=self.PAGE_SIZE,
            pageCompression=1,
        )

        self.canvas.setTitle(
            f"Paletowka {self.shipment_unit.id}"
        )
        self.canvas.setAuthor("PAKER Sp. z o.o.")

    def build(self):
        self._draw_label()

        self.canvas.showPage()
        self.canvas.save()

        self.buffer.seek(0)
        return self.buffer

    # ============================================================
    # FONTY
    # ============================================================

    def _register_fonts(self):
        regular_path = (
                Path(settings.BASE_DIR)
                / "warehousemanager"
                / "static"
                / "fonts"
                / "DejaVuSans.ttf"
        )

        bold_path = (
                Path(settings.BASE_DIR)
                / "warehousemanager"
                / "static"
                / "fonts"
                / "DejaVuSans-Bold.ttf"
        )

        missing = [
            str(path)
            for path in (regular_path, bold_path)
            if not path.exists()
        ]

        if missing:
            raise FileNotFoundError(
                "Brakuje fontów wymaganych do wygenerowania PDF:\n"
                + "\n".join(missing)
            )

        registered = pdfmetrics.getRegisteredFontNames()

        if self.FONT_REGULAR not in registered:
            pdfmetrics.registerFont(
                TTFont(
                    self.FONT_REGULAR,
                    str(regular_path),
                )
            )

        if self.FONT_BOLD not in registered:
            pdfmetrics.registerFont(
                TTFont(
                    self.FONT_BOLD,
                    str(bold_path),
                )
            )

    # ============================================================
    # GŁÓWNY UKŁAD
    # ============================================================

    def _draw_label(self):
        x = self.PAGE_MARGIN
        y = self.PAGE_MARGIN

        left_table = self._build_left_table()
        right_table = self._build_right_table()

        main_table = Table(
            [[left_table, right_table]],
            colWidths=[
                self.LEFT_COLUMN_WIDTH,
                self.RIGHT_COLUMN_WIDTH,
            ],
            rowHeights=[self.LABEL_HEIGHT],
        )

        main_table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ]
            )
        )

        main_table.wrapOn(
            self.canvas,
            self.LABEL_WIDTH,
            self.LABEL_HEIGHT,
        )

        main_table.drawOn(
            self.canvas,
            x,
            y,
        )

    # ============================================================
    # LEWA KOLUMNA
    # ============================================================

    def _build_left_table(self):
        print(
            self.order.production_date_result())
        production_date = (
            self.order.production_date_result()
            or self.shipment_unit.created
        )

        rows = [
            [self._paragraph("DATA PRODUKCJI", 9)],
            [
                self._paragraph(
                    self._format_date(production_date),
                    11,
                    bold=True,
                )
            ],
            [self._paragraph("DATA WYSYŁKI", 9)],
            [self._paragraph("", 11, bold=True)],
            [self._paragraph("WAGA", 9)],
            [
                self._paragraph(
                    (
                        # f"{self.shipment_unit.weight} kg"
                        # if self.shipment_unit.weight
                        # else "-"
                        "-"
                    ),
                    11,
                    bold=True,
                )
            ],
            [self._paragraph("WYSOKOŚĆ", 9)],
            [
                self._paragraph(
                    (
                        # f"{self.shipment_unit.height} mm"
                        # if self.shipment_unit.height
                        # else "-"
                        "-"
                    ),
                    11,
                    bold=True,
                )
            ],
            [self._paragraph("SPAKOWAŁ", 9)],
            [
                self._paragraph(
                    self._packer_name(),
                    11,
                    bold=True,
                )
            ],
            [self._paragraph("PALETA", 9)],
            [
                self._paragraph(
                    self._safe_text(
                        self.shipment_unit.palette
                    ),
                    11,
                    bold=True,
                )
            ],
            [
                self._paragraph(
                    "INFORMACJE O<br/>PRZECHOWYWANIU",
                    8,
                )
            ],
            [
                self._storage_information()
            ],
        ]

        fixed_height = 12 * mm
        fixed_rows_count = 13

        storage_height = (
            self.LABEL_HEIGHT
            - (fixed_height * fixed_rows_count)
        )

        row_heights = (
            [fixed_height] * fixed_rows_count
            + [storage_height]
        )

        table = Table(
            rows,
            colWidths=[self.LEFT_COLUMN_WIDTH],
            rowHeights=row_heights,
        )

        table.setStyle(
            self._base_table_style(
                font_size=9,
                padding=1.5 * mm,
            )
        )

        table.setStyle(
            TableStyle(
                [
                    (
                        "VALIGN",
                        (0, 13),
                        (0, 13),
                        "TOP",
                    ),
                    (
                        "ALIGN",
                        (0, 13),
                        (0, 13),
                        "LEFT",
                    ),
                    (
                        "TOPPADDING",
                        (0, 13),
                        (0, 13),
                        3 * mm,
                    ),
                    (
                        "LEFTPADDING",
                        (0, 13),
                        (0, 13),
                        2.5 * mm,
                    ),
                    (
                        "RIGHTPADDING",
                        (0, 13),
                        (0, 13),
                        2.5 * mm,
                    ),
                ]
            )
        )

        return table

    def _storage_information(self):
        text = (
            "<b>Zalecenia i warunki przechowywania wyrobów "
            "z tektury falistej:</b>"
            "<br/><br/>"
            "1) Temperatura 5-30°C. Wilgotność względna 30-70%."
            "<br/>"
            "2) Chronić przed zamoczeniem i bezpośrednim "
            "promieniowaniem słonecznym."
            "<br/>"
            "3) Nie dopuszczać do gwałtownych zmian temperatury "
            "i wilgotności."
            "<br/>"
            "4) Uwaga! Wyrób podatny na uszkodzenia - zachować "
            "ostrożność podczas magazynowania i przemieszczania."
        )

        return self._paragraph(
            text,
            font_size=5.2,
            alignment=TA_LEFT,
            leading=6.7,
        )

    # ============================================================
    # PRAWA KOLUMNA
    # ============================================================

    def _build_right_table(self):
        header = self._build_company_header()
        product_row = self._build_field_row(
            "PRODUKT",
            self._product_name(),
            value_font_size=self._product_font_size(),
        )

        quantity_row = self._build_field_row(
            "ILOŚĆ SZTUK",
            self.shipment_unit.quantity,
            value_font_size=18,
        )

        series_row = self._build_field_row(
            "NUMER SERII",
            self._series_number(),
            value_font_size=18,
        )

        codes = self._build_codes_area()

        rows = [
            [header],
            [
                self._paragraph(
                    self._customer_name(),
                    self._customer_font_size(),
                    bold=True,
                )
            ],
            [product_row],
            [quantity_row],
            [series_row],
            [codes],
            [""],
        ]

        row_heights = [
            29 * mm,
            35 * mm,
            18 * mm,
            18 * mm,
            14 * mm,
            self.LABEL_HEIGHT
            - (
                29 * mm
                + 35 * mm
                + 18 * mm
                + 18 * mm
                + 14 * mm
                + 29 * mm
            ),
            29 * mm,
        ]

        table = Table(
            rows,
            colWidths=[self.RIGHT_COLUMN_WIDTH],
            rowHeights=row_heights,
        )

        table.setStyle(
            self._base_table_style(
                font_size=10,
                padding=0,
            )
        )

        table.setStyle(
            TableStyle(
                [
                    (
                        "LEFTPADDING",
                        (0, 1),
                        (0, 1),
                        3 * mm,
                    ),
                    (
                        "RIGHTPADDING",
                        (0, 1),
                        (0, 1),
                        3 * mm,
                    ),
                    (
                        "TOPPADDING",
                        (0, 1),
                        (0, 1),
                        2 * mm,
                    ),
                    (
                        "BOTTOMPADDING",
                        (0, 1),
                        (0, 1),
                        2 * mm,
                    ),
                ]
            )
        )

        return table

    def _build_company_header(self):
        company_name_width = self.RIGHT_COLUMN_WIDTH * 0.50
        company_address_width = self.RIGHT_COLUMN_WIDTH * 0.25
        company_extra_width = (
            self.RIGHT_COLUMN_WIDTH
            - company_name_width
            - company_address_width
        )

        address = (
            "UL. LOTNICZA 1<br/>"
            "55-200 STANOWICE<br/>"
            "NIP: 8961533894<br/>"
        )

        table = Table(
            [
                [
                    self._paragraph(
                        "PAKER SP. Z O. O.",
                        22,
                    ),
                    self._paragraph(
                        address,
                        10.5,
                        alignment=TA_LEFT,
                        leading=9,
                    ),
                    "",
                ]
            ],
            colWidths=[
                company_name_width,
                company_address_width,
                company_extra_width,
            ],
            rowHeights=[29 * mm],
        )

        table.setStyle(
            self._base_table_style(
                font_size=8,
                padding=2 * mm,
            )
        )

        return table

    def _build_field_row(
        self,
        label,
        value,
        value_font_size=14,
    ):
        label_width = 50 * mm
        value_width = self.RIGHT_COLUMN_WIDTH - label_width

        table = Table(
            [
                [
                    self._paragraph(label, 10),
                    self._paragraph(
                        self._safe_text(value),
                        value_font_size,
                        bold=True,
                    ),
                ]
            ],
            colWidths=[
                label_width,
                value_width,
            ],
        )

        table.setStyle(
            self._base_table_style(
                font_size=10,
                padding=2 * mm,
            )
        )

        return table

    # ============================================================
    # KODY
    # ============================================================

    def _build_codes_area(self):
        barcode_flowable = self._barcode_flowable()
        qr_flowable = self._qr_flowable()

        table = Table(
            [[barcode_flowable, qr_flowable]],
            colWidths=[
                self.RIGHT_COLUMN_WIDTH - 48 * mm,
                48 * mm,
            ],
        )

        table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("ALIGN", (0, 0), (0, 0), "CENTER"),
                    ("ALIGN", (1, 0), (1, 0), "CENTER"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 2 * mm),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 2 * mm),
                    ("TOPPADDING", (0, 0), (-1, -1), 2 * mm),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2 * mm),
                ]
            )
        )

        return table

    def _barcode_flowable(self):
        barcode_value = self._barcode_value()

        return code128.Code128(
            barcode_value,
            barHeight=18 * mm,
            barWidth=0.35 * mm,
            humanReadable=True,
        )

    def _qr_flowable(self):
        scan_url = self._build_scan_url()

        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=8,
            border=2,
        )

        qr.add_data(scan_url)
        qr.make(fit=True)

        image = qr.make_image(
            fill_color="black",
            back_color="white",
        )

        image_buffer = BytesIO()
        image.save(
            image_buffer,
            format="PNG",
        )
        image_buffer.seek(0)

        return ReportLabImage(
            image_buffer,
            width=35 * mm,
            height=35 * mm,
        )

    def _barcode_value(self):
        if self.order.id:
            return (
                f"{self.order.provider_id}-"
                f"{self.order.id}-"
                f"{self.shipment_unit.id}"
            )

        return str(self.shipment_unit.id)

    def _build_scan_url(self):
        token = signing.dumps(
            {
                "shipment_unit_id": self.shipment_unit.id,
            },
            salt="shipment-unit-loading",
        )

        scan_path = reverse(
            "warehouse:shipment-unit-loading-scan",
            kwargs={
                "token": token,
            },
        )

        return self.request.build_absolute_uri(
            scan_path
        )

    # ============================================================
    # STYLE I PARAGRAFY
    # ============================================================

    def _paragraph(
        self,
        value,
        font_size,
        bold=False,
        alignment=TA_CENTER,
        leading=None,
    ):
        if leading is None:
            leading = font_size * 1.15

        style = ParagraphStyle(
            name=f"shipment-unit-{id(value)}-{font_size}",
            fontName=(
                self.FONT_BOLD
                if bold
                else self.FONT_REGULAR
            ),
            fontSize=font_size,
            leading=leading,
            alignment=alignment,
            textColor=colors.black,
            spaceBefore=0,
            spaceAfter=0,
        )

        return Paragraph(
            str(value or ""),
            style,
        )

    def _base_table_style(
        self,
        font_size=10,
        padding=2 * mm,
    ):
        return TableStyle(
            [
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    self.BORDER_WIDTH,
                    colors.black,
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "ALIGN",
                    (0, 0),
                    (-1, -1),
                    "CENTER",
                ),
                (
                    "FONTNAME",
                    (0, 0),
                    (-1, -1),
                    self.FONT_REGULAR,
                ),
                (
                    "FONTSIZE",
                    (0, 0),
                    (-1, -1),
                    font_size,
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    padding,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    padding,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    padding,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    padding,
                ),
            ]
        )

    # ============================================================
    # DANE
    # ============================================================

    def _customer_name(self):
        return self._safe_text(
            self.order.customer
        ).upper()

    def _product_name(self):
        product = (
            self.shipment_unit.product
            or self.order.product
        )

        return self._safe_text(product)

    def _series_number(self):
        year = self.order.order_year or ""

        return f"{self.order.id}/{year}"

    def _packer_name(self):
        user = self.shipment_unit.created_by

        if not user:
            return "-"

        return user.id

    def _customer_font_size(self):
        length = len(self._customer_name())

        if length > 45:
            return 16

        if length > 30:
            return 19

        if length > 20:
            return 22

        return 25

    def _product_font_size(self):
        length = len(self._product_name())

        if length > 75:
            return 8

        if length > 55:
            return 9.5

        if length > 40:
            return 11

        if length > 25:
            return 12.5

        return 14

    @staticmethod
    def _safe_text(value, default="-"):
        if value is None:
            return default

        text = str(value).strip()

        if not text:
            return default

        return escape(text)

    @staticmethod
    def _format_date(value):
        if not value:
            return "-"

        if hasattr(value, "date") and not hasattr(
            value,
            "strftime",
        ):
            value = value.date()

        return value.strftime("%d.%m.%Y")