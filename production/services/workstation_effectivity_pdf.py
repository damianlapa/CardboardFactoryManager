from io import BytesIO
from pathlib import Path

from django.conf import settings

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    KeepTogether,
)


class WorkstationEffectivityPDF:
    PAGE_SIZE = A4

    PAGE_MARGIN = 14 * mm

    FONT_REGULAR = "DejaVuSans"
    FONT_BOLD = "DejaVuSans-Bold"

    def __init__(
        self,
        statistics,
        date_from,
        date_to,
    ):
        self.statistics = statistics
        self.date_from = date_from
        self.date_to = date_to

        self._register_fonts()

        self.buffer = BytesIO()

    # ============================================================
    # BUILD
    # ============================================================

    def build(self):
        doc = SimpleDocTemplate(
            self.buffer,
            pagesize=self.PAGE_SIZE,
            leftMargin=self.PAGE_MARGIN,
            rightMargin=self.PAGE_MARGIN,
            topMargin=self.PAGE_MARGIN,
            bottomMargin=self.PAGE_MARGIN,
            title="Zajętość stanowisk",
            author="PAKER Sp. z o.o.",
        )

        story = []

        story.extend(
            self._build_header()
        )

        story.append(
            self._build_summary()
        )

        story.append(
            Spacer(1, 7 * mm)
        )

        for item in self.statistics["stations"]:
            story.append(
                KeepTogether(
                    self._build_station(item)
                )
            )

        doc.build(
            story,
            onFirstPage=self._draw_page_number,
            onLaterPages=self._draw_page_number,
        )

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
            for path in (
                regular_path,
                bold_path,
            )
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
    # HEADER
    # ============================================================

    def _build_header(self):
        return [
            self._paragraph(
                "Zajętość stanowisk",
                18,
                bold=True,
                alignment=TA_LEFT,
                leading=22,
            ),

            Spacer(1, 1.5 * mm),

            self._paragraph(
                "Wykorzystanie stanowisk produkcyjnych "
                "i roboczogodziny",
                9,
                alignment=TA_LEFT,
                text_color=colors.HexColor("#666666"),
            ),

            Spacer(1, 6 * mm),
        ]

    # ============================================================
    # PODSUMOWANIE
    # ============================================================

    def _build_summary(self):
        data = [
            [
                self._summary_cell(
                    "OKRES",
                    (
                        f"{self.date_from:%d.%m.%Y} - "
                        f"{self.date_to:%d.%m.%Y}"
                    ),
                ),
                self._summary_cell(
                    "DNI ROBOCZE",
                    str(
                        self.statistics["working_days"]
                    ),
                ),
                self._summary_cell(
                    "DOSTĘPNOŚĆ DZIENNA",
                    "7 h 25 min",
                ),
            ]
        ]

        table = Table(
            data,
            colWidths=[
                65 * mm,
                45 * mm,
                52 * mm,
            ],
        )

        table.setStyle(
            TableStyle(
                [
                    (
                        "BOX",
                        (0, 0),
                        (-1, -1),
                        0.4,
                        colors.HexColor("#d6d6d6"),
                    ),
                    (
                        "INNERGRID",
                        (0, 0),
                        (-1, -1),
                        0.4,
                        colors.HexColor("#e0e0e0"),
                    ),
                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "MIDDLE",
                    ),
                    (
                        "LEFTPADDING",
                        (0, 0),
                        (-1, -1),
                        3 * mm,
                    ),
                    (
                        "RIGHTPADDING",
                        (0, 0),
                        (-1, -1),
                        3 * mm,
                    ),
                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, -1),
                        2.5 * mm,
                    ),
                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, -1),
                        2.5 * mm,
                    ),
                ]
            )
        )

        return table

    def _summary_cell(
        self,
        label,
        value,
    ):
        return [
            self._paragraph(
                label,
                7.5,
                alignment=TA_LEFT,
                text_color=colors.HexColor("#777777"),
            ),
            Spacer(1, 1 * mm),
            self._paragraph(
                value,
                10,
                bold=True,
                alignment=TA_LEFT,
            ),
        ]

    # ============================================================
    # STANOWISKO
    # ============================================================

    def _build_station(self, item):
        result = []

        result.append(
            self._build_station_header(item)
        )

        result.append(
            Spacer(1, 2 * mm)
        )

        result.append(
            self._build_progress_bar(
                item["progress_percent"]
            )
        )

        result.append(
            Spacer(1, 3 * mm)
        )

        result.append(
            self._build_metrics(item)
        )

        if item["persons_distribution"]:
            result.append(
                Spacer(1, 3 * mm)
            )

            result.append(
                self._build_distribution(
                    item["persons_distribution"]
                )
            )

        result.append(
            Spacer(1, 7 * mm)
        )

        return result

    def _build_station_header(self, item):
        left = [
            self._paragraph(
                item["station"].name,
                12,
                bold=True,
                alignment=TA_LEFT,
            ),
            Spacer(1, 0.5 * mm),
            self._paragraph(
                f'{item["units_count"]} operacji',
                7.5,
                alignment=TA_LEFT,
                text_color=colors.HexColor("#777777"),
            ),
        ]

        right = self._paragraph(
            f'{item["occupancy_percent"]:.1f}%',
            12,
            bold=True,
            alignment=TA_RIGHT,
        )

        table = Table(
            [[left, right]],
            colWidths=[
                130 * mm,
                32 * mm,
            ],
        )

        table.setStyle(
            TableStyle(
                [
                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "MIDDLE",
                    ),
                    (
                        "LEFTPADDING",
                        (0, 0),
                        (-1, -1),
                        0,
                    ),
                    (
                        "RIGHTPADDING",
                        (0, 0),
                        (-1, -1),
                        0,
                    ),
                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, -1),
                        0,
                    ),
                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, -1),
                        0,
                    ),
                ]
            )
        )

        return table

    # ============================================================
    # PROGRESS
    # ============================================================

    def _build_progress_bar(self, percent):
        percent = max(
            0,
            min(
                float(percent),
                100,
            ),
        )

        total_width = 162 * mm

        filled = (
            total_width
            * percent
            / 100
        )

        empty = total_width - filled

        # zabezpieczenie ReportLab przed zerową kolumną
        if filled <= 0:
            filled = 0.1 * mm

        if empty <= 0:
            empty = 0.1 * mm

        table = Table(
            [["", ""]],
            colWidths=[
                filled,
                empty,
            ],
            rowHeights=[
                3.5 * mm,
            ],
        )

        table.setStyle(
            TableStyle(
                [
                    (
                        "BACKGROUND",
                        (0, 0),
                        (0, 0),
                        colors.HexColor("#4f6475"),
                    ),
                    (
                        "BACKGROUND",
                        (1, 0),
                        (1, 0),
                        colors.HexColor("#e8ecef"),
                    ),
                    (
                        "BOX",
                        (0, 0),
                        (-1, -1),
                        0.2,
                        colors.HexColor("#d0d0d0"),
                    ),
                    (
                        "LEFTPADDING",
                        (0, 0),
                        (-1, -1),
                        0,
                    ),
                    (
                        "RIGHTPADDING",
                        (0, 0),
                        (-1, -1),
                        0,
                    ),
                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, -1),
                        0,
                    ),
                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, -1),
                        0,
                    ),
                ]
            )
        )

        return table

    # ============================================================
    # METRYKI
    # ============================================================

    def _build_metrics(self, item):
        data = [
            [
                self._metric_cell(
                    "ZAJĘTE",
                    f'{item["occupied_hours"]:.2f} h',
                ),

                self._metric_cell(
                    "ROBOCZOGODZINY",
                    f'{item["worker_hours"]:.2f} h',
                ),

                self._metric_cell(
                    "DOSTĘPNE",
                    f'{item["available_hours"]:.2f} h',
                ),
            ]
        ]

        table = Table(
            data,
            colWidths=[
                54 * mm,
                54 * mm,
                54 * mm,
            ],
        )

        table.setStyle(
            TableStyle(
                [
                    (
                        "BOX",
                        (0, 0),
                        (-1, -1),
                        0.3,
                        colors.HexColor("#dedede"),
                    ),
                    (
                        "INNERGRID",
                        (0, 0),
                        (-1, -1),
                        0.3,
                        colors.HexColor("#e5e5e5"),
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
                        "TOPPADDING",
                        (0, 0),
                        (-1, -1),
                        2 * mm,
                    ),
                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, -1),
                        2 * mm,
                    ),
                ]
            )
        )

        return table

    def _metric_cell(
        self,
        label,
        value,
    ):
        return [
            self._paragraph(
                label,
                7,
                text_color=colors.HexColor("#777777"),
            ),
            Spacer(1, 0.8 * mm),
            self._paragraph(
                value,
                9.5,
                bold=True,
            ),
        ]

    # ============================================================
    # OBSADA
    # ============================================================

    def _build_distribution(
        self,
        distribution,
    ):
        rows = [
            [
                self._paragraph(
                    "OBSADA",
                    7,
                    bold=True,
                    alignment=TA_LEFT,
                ),
                self._paragraph(
                    "CZAS",
                    7,
                    bold=True,
                    alignment=TA_RIGHT,
                ),
                self._paragraph(
                    "ROBOCZOGODZINY",
                    7,
                    bold=True,
                    alignment=TA_RIGHT,
                ),
            ]
        ]

        for row in distribution:
            persons = row["persons"]

            if persons == 0:
                persons_label = "Bez osób"
            elif persons == 1:
                persons_label = "1 osoba"
            else:
                persons_label = (
                    f"{persons} osoby/osób"
                )

            rows.append(
                [
                    self._paragraph(
                        persons_label,
                        7.5,
                        alignment=TA_LEFT,
                    ),
                    self._paragraph(
                        f'{row["hours"]:.2f} h',
                        7.5,
                        alignment=TA_RIGHT,
                    ),
                    self._paragraph(
                        f'{row["worker_hours"]:.2f} rbh',
                        7.5,
                        alignment=TA_RIGHT,
                    ),
                ]
            )

        table = Table(
            rows,
            colWidths=[
                82 * mm,
                40 * mm,
                40 * mm,
            ],
        )

        table.setStyle(
            TableStyle(
                [
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, 0),
                        colors.HexColor("#f4f5f6"),
                    ),
                    (
                        "LINEBELOW",
                        (0, 0),
                        (-1, 0),
                        0.4,
                        colors.HexColor("#cccccc"),
                    ),
                    (
                        "LINEBELOW",
                        (0, 1),
                        (-1, -1),
                        0.2,
                        colors.HexColor("#ededed"),
                    ),
                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "MIDDLE",
                    ),
                    (
                        "LEFTPADDING",
                        (0, 0),
                        (-1, -1),
                        2 * mm,
                    ),
                    (
                        "RIGHTPADDING",
                        (0, 0),
                        (-1, -1),
                        2 * mm,
                    ),
                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, -1),
                        1.4 * mm,
                    ),
                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, -1),
                        1.4 * mm,
                    ),
                ]
            )
        )

        return table

    # ============================================================
    # PARAGRAPH
    # ============================================================

    def _paragraph(
        self,
        value,
        font_size,
        bold=False,
        alignment=TA_LEFT,
        leading=None,
        text_color=colors.black,
    ):
        if leading is None:
            leading = font_size * 1.18

        style = ParagraphStyle(
            name=(
                f"workstation-effectivity-"
                f"{id(value)}-"
                f"{font_size}"
            ),
            fontName=(
                self.FONT_BOLD
                if bold
                else self.FONT_REGULAR
            ),
            fontSize=font_size,
            leading=leading,
            alignment=alignment,
            textColor=text_color,
            spaceBefore=0,
            spaceAfter=0,
        )

        return Paragraph(
            str(value or ""),
            style,
        )

    # ============================================================
    # NUMER STRONY
    # ============================================================

    def _draw_page_number(
        self,
        canvas,
        doc,
    ):
        canvas.saveState()

        canvas.setFont(
            self.FONT_REGULAR,
            7,
        )

        canvas.setFillColor(
            colors.HexColor("#777777")
        )

        canvas.drawRightString(
            self.PAGE_SIZE[0]
            - self.PAGE_MARGIN,
            7 * mm,
            f"Strona {canvas.getPageNumber()}",
        )

        canvas.restoreState()