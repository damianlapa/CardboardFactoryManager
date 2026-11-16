from django.views import View
import datetime
import os
from warehousemanager.models import Person, Holiday, Absence, ExtraHour
from production.models import ProductionUnit
from xhtml2pdf import pisa
from django.template.loader import get_template
from django.shortcuts import HttpResponse, render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy


class WorkerEfficiencyPrintPDF2(View):
    def get(self, request, year, month, worker_id):
        date_from = datetime.datetime.strptime(f"{request.GET.get('from')} 00:00:00",
                                               '%Y-%m-%d %H:%M:%S') if request.GET.get('from') else None
        date_to = datetime.datetime.strptime(f"{request.GET.get('to')} 23:59:59",
                                             '%Y-%m-%d %H:%M:%S') if request.GET.get('to') else None
        bonus = True if request.GET.get('bonus') else False
        full_pot = float(600.00)
        now = datetime.datetime.now()
        worker = Person.objects.get(id=worker_id)
        if month == 2:
            if year % 4 == 0:
                days = 29
            else:
                days = 28
        elif month in (1, 3, 5, 7, 8, 10, 12):
            days = 31
        else:
            days = 30

        month_start = datetime.datetime.strptime(f'{year}-{month}-01', '%Y-%m-%d').date()
        month_end = datetime.datetime.strptime(f'{year}-{month}-{days}', '%Y-%m-%d').date()

        if date_from:
            month_start = date_from.date()
        if date_to:
            month_end = date_to.date()

        if month_end > datetime.datetime.today().date():
            month_end = datetime.datetime.today().date()

        working_days = 0
        absences = 0
        extra_hours = 0
        holidays = 0
        late = 0
        fridays = 0

        events_data = []

        end_day = None
        start_day = month_start
        while start_day != month_end + datetime.timedelta(days=1):
            if worker.job_start <= start_day:
                if worker.job_end:
                    if worker.job_end >= start_day:
                        holiday = Holiday.objects.filter(holiday_date=start_day)
                        if start_day.isoweekday() < 6:
                            if not holiday:
                                absence = Absence.objects.filter(worker=worker, absence_date=start_day)
                                if absence:
                                    late_in_minutes = f'{absence[0].value} minut' if absence[0].value else ''
                                    events_data.append(
                                        (absence[0].absence_date, absence[0].absence_type, late_in_minutes))
                                    if absence[0].absence_type == 'SP':
                                        late += 1

                                absence = absence.exclude(absence_type='SP')
                                extra_h = ExtraHour.objects.filter(worker=worker, extras_date=start_day)
                                if extra_h:
                                    extra_ho = extra_h[0]
                                    if extra_ho.full_day:
                                        extra_hours += extra_ho.quantity
                                        events_data.append(
                                            (extra_ho.extras_date, 'Nadgodziny', extra_ho.quantity))
                                    else:
                                        extra_hours += extra_ho.quantity - 8
                                        events_data.append(
                                            (extra_ho.extras_date, 'Niepełny dzień', 8 - extra_ho.quantity))
                                if absence:
                                    absences += 1
                                working_days += 1
                            else:
                                holidays += 1
                else:
                    holiday = Holiday.objects.filter(holiday_date=start_day)
                    if not holiday:
                        if start_day.isoweekday() < 6:
                            absence = Absence.objects.filter(worker=worker, absence_date=start_day)
                            if absence:
                                late_in_minutes = f'{absence[0].value} minut' if absence[0].value else ''
                                events_data.append((absence[0].absence_date, absence[0].absence_type, late_in_minutes))
                                if absence[0].absence_type == 'SP':
                                    late += 1
                                    if start_day.isoweekday() == 5:
                                        fridays += 1
                            else:
                                if start_day.isoweekday() == 5:
                                    fridays += 1
                            absence = absence.exclude(absence_type='SP')
                            extra_h = ExtraHour.objects.filter(worker=worker, extras_date=start_day)
                            if extra_h:
                                extra_ho = extra_h[0]
                                if extra_ho.full_day:
                                    extra_hours += extra_ho.quantity
                                    events_data.append(
                                        (extra_ho.extras_date, 'Nadgodziny', extra_ho.quantity))
                                else:
                                    extra_hours += extra_ho.quantity - 8
                                    events_data.append(
                                        (extra_ho.extras_date, 'Niepełny dzień', extra_ho.quantity))
                            if absence:
                                absences += 1
                            working_days += 1
                    else:
                        holidays += 1
            start_day += datetime.timedelta(days=1)

        work_seconds = 36 * 800 * (working_days - absences) + extra_hours * 3600

        def working_hours(value_in_seconds):
            hours = value_in_seconds // 3600
            return hours

        work_hours = working_hours(work_seconds)
        all_hours = working_days * 8
        days_at_work = working_days - absences
        days_at_work_to_count = days_at_work

        if work_hours != days_at_work_to_count * 8:
            days_at_work_to_count = round(work_hours // 8 + (work_hours % 8) / 8, 2)

        month_end += datetime.timedelta(days=1)

        units = ProductionUnit.objects.filter(start__gte=month_start, end__lte=month_end,
                                              persons__id=worker_id).order_by('start')

        data = []

        worker_stations = []
        units_stations = []
        coworkers = []
        works_with = []

        efficiency = [0, 0]

        for unit in units:
            data.append([unit, ])
            # if unit.estimated_duration_in_seconds() and unit.unit_duration_in_seconds():
            if unit.estimated_duration_in_seconds() and unit.unit_duration2():

                # unit_fractal = unit.estimated_duration_in_seconds() / unit.unit_duration_in_seconds()
                unit_fractal = unit.estimated_duration_in_seconds() / unit.unit_duration2()
                unit_efficiency = round(100 * unit_fractal, 2)
                data[-1].append(unit_efficiency)
                efficiency[0] += unit.estimated_duration_in_seconds()
                # efficiency[1] += unit.unit_duration_in_seconds()
                efficiency[1] += unit.unit_duration2()

                # work stations
                if unit.work_station not in worker_stations:
                    worker_stations.append(unit.work_station)
                    # units_stations.append([unit.work_station, 1, unit.unit_duration_in_seconds(),
                    #                        [unit.estimated_duration_in_seconds(), unit.unit_duration_in_seconds()]])
                    units_stations.append([unit.work_station, 1, unit.unit_duration2(),
                                           [unit.estimated_duration_in_seconds(), unit.unit_duration2()]])
                else:
                    for us in units_stations:
                        if us[0] == unit.work_station:
                            us[1] += 1
                            # us[2] += unit.unit_duration_in_seconds()
                            us[2] += unit.unit_duration2()
                            us[3][0] += unit.estimated_duration_in_seconds()
                            # us[3][1] += unit.unit_duration_in_seconds()
                            us[3][1] += unit.unit_duration2()

                # works with
                for coworker in unit.persons.all():
                    if coworker != worker:
                        if coworker not in coworkers:
                            coworkers.append(coworker)
                            works_with.append([coworker, 0, 0, [0, 0]])
                if unit.persons.all().count() == 1:
                    if works_with:
                        if works_with[0][0] == '-':
                            works_with[0][1] += 1
                            # works_with[0][2] += unit.unit_duration_in_seconds()
                            works_with[0][2] += unit.unit_duration2()
                            works_with[0][3][0] += unit.estimated_duration_in_seconds()
                            # works_with[0][3][1] += unit.unit_duration_in_seconds()
                            works_with[0][3][1] += unit.unit_duration2()
                        else:
                            # works_with.insert(0, ['-', 1, unit.unit_duration_in_seconds(),
                            #                       [unit.estimated_duration_in_seconds(),
                            #                        unit.unit_duration_in_seconds()]])
                            works_with.insert(0, ['-', 1, unit.unit_duration2(),
                                                  [unit.estimated_duration_in_seconds(),
                                                   unit.unit_duration2()]])
                    else:
                        # works_with.append(['-', 1, unit.unit_duration_in_seconds(),
                        #                    [unit.estimated_duration_in_seconds(), unit.unit_duration_in_seconds()]])
                        works_with.append(['-', 1, unit.unit_duration2(),
                                           [unit.estimated_duration_in_seconds(), unit.unit_duration2()]])
                for coop in works_with:
                    for coworker_person in unit.persons.all():
                        if coworker_person == coop[0]:
                            coop[1] += 1
                            # coop[2] += unit.unit_duration_in_seconds()
                            coop[2] += unit.unit_duration2()
                            coop[3][0] += unit.estimated_duration_in_seconds()
                            # coop[3][1] += unit.unit_duration_in_seconds()
                            coop[3][1] += unit.unit_duration2()

        for coworker_data in works_with:
            hours = coworker_data[2] // 3600
            minutes = (coworker_data[2] - hours * 3600) // 60
            seconds = coworker_data[2] % 60
            hours = hours if hours > 9 else f'0{hours}'
            minutes = minutes if minutes > 9 else f'0{minutes}'
            seconds = seconds if seconds > 9 else f'0{seconds}'
            coworker_data[2] = f'{hours}:{minutes}:{seconds}'
            coworker_data[3] = round(100 * coworker_data[3][0] / coworker_data[3][1], 2) if coworker_data[3][1] else 100

        works_with = sorted(works_with, key=lambda x: x[1], reverse=True)

        month_work_time = 0

        # work stations
        for us in units_stations:
            month_work_time += us[2]
            hours = us[2] // 3600
            minutes = (us[2] - hours * 3600) // 60
            seconds = us[2] % 60
            hours = hours if hours > 9 else f'0{hours}'
            minutes = minutes if minutes > 9 else f'0{minutes}'
            seconds = seconds if seconds > 9 else f'0{seconds}'
            us[2] = f'{hours}:{minutes}:{seconds}'
            us[3] = round(100 * us[3][0] / us[3][1], 2) if us[3][1] else 100

        month_work_time_units = [month_work_time // 3600, (month_work_time - (month_work_time // 3600) * 3600) // 60, month_work_time % 60]
        month_work_time_units = [int(x // 1) for x in month_work_time_units]
        month_work_time_str = ':'.join([f'{x}' if x > 9 else f'0{x}' for x in month_work_time_units])

        month_work_base = work_hours - ((work_hours // 8) / 3)
        month_work_base = month_work_base * 60 * 60 - fridays * 3600

        month_work_base_units = [month_work_base // 3600, (month_work_base - (month_work_base // 3600) * 3600) // 60, month_work_base % 60]
        month_work_base_units = [int(x // 1) for x in month_work_base_units]
        month_work_base_str = ':'.join([f'{x}' if x > 9 else f'0{x}' for x in month_work_base_units])

        result = round(month_work_time/month_work_base, 2) * 100


        units_stations = sorted(units_stations, key=lambda x: x[1], reverse=True)

        efficiency = round(100 * efficiency[0] / efficiency[1], 2) if efficiency[1] else 100

        pot = round(full_pot * float((days_at_work_to_count / working_days)), 2)

        suggested_bonus = 0

        if efficiency >= 100:
            suggested_bonus = 0.5 * pot * (1 + (efficiency - 100) / 50)
            if suggested_bonus > pot:
                suggested_bonus = pot
        else:
            suggested_bonus = 0.5 * pot * (100 - ((100 - efficiency) * 4)) / 100
            if suggested_bonus < 0:
                suggested_bonus = 0

        suggested_bonus = round(suggested_bonus, 2)

        month_end_pdf = month_end - datetime.timedelta(days=1)

        logo_url = os.environ['PAKER_MAIN'] + 'static/images/paker-logo.png'
        font_url = os.environ['PAKER_MAIN'] + 'static/fonts/roboto/'

        template_path = 'production/worker-efficiency-pdf.html'
        context = locals()
        # Create a Django response object, and specify content_type as pdf
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'filename="{worker} {year}-{month} report.pdf"'
        # find the template and render it.
        template = get_template(template_path)
        html = template.render(context)

        # create a pdf
        pisa_status = pisa.CreatePDF(
            html, dest=response, encoding='UTF-8')
        # if errorw
        if pisa_status.err:
            return HttpResponse('We had some errors <pre>' + html + '</pre>')
        return response


class MonthReport(LoginRequiredMixin, View):
    login_url = reverse_lazy('login')

    def get(self, request):
        dates = (datetime.date(2025, 11, 1), datetime.date(2025, 11, 30))
        units = ProductionUnit.objects.filter(start__lte=dates[1], end__gte=dates[0])
        context = {
            'units': units
        }

        return render(request, 'production/month_report.html', context=context)


import io
import re

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
    PageBreak,
)
from warehouse.models import *
from production.models import ProductionUnit, ProductionOrder

import os

from django.conf import settings

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

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


class DieCutProductionPdfView(LoginRequiredMixin, View):
    login_url = reverse_lazy("login")

    FONT_REGULAR = "DejaVuSans"
    FONT_BOLD = "DejaVuSans-Bold"

    WORKSTATIONS = (
        "TYGIEL MAŁY",
        "TYGIEL DUŻY",
    )

    MIN_SHORT = 350
    MAX_SHORT = 800

    MIN_LONG = 500
    MAX_LONG = 1500

    EXCLUDED_PRODUCTS = (
        "MERIDA | BC | KÓŁKA",
    )

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

    @staticmethod
    def _parse_dimensions(value):
        if not value:
            return None

        value = str(value).lower().replace("×", "x")

        match = re.search(
            r"(\d+)\s*x\s*(\d+)",
            value,
        )

        if not match:
            return None

        a = int(match.group(1))
        b = int(match.group(2))

        return min(a, b), max(a, b)

    def _dimension_is_allowed(self, value):
        dimensions = self._parse_dimensions(value)

        if not dimensions:
            return False

        short_side, long_side = dimensions

        return (
            self.MIN_SHORT <= short_side <= self.MAX_SHORT
            and
            self.MIN_LONG <= long_side <= self.MAX_LONG
        )

    @staticmethod
    def _normalize_name(value):
        if not value:
            return ""

        return " ".join(
            str(value).upper().split()
        )

    def get(self, request):
        self._register_fonts()

        today = datetime.date.today()

        date_from = datetime.date(
            today.year,
            1,
            1,
        )

        date_to = datetime.date(
            today.year + 1,
            1,
            1,
        )

        # ============================================================
        # JEDNOSTKI PRODUKCYJNE
        # ============================================================

        units_qs = (
            ProductionUnit.objects
            .filter(
                work_station__name__in=self.WORKSTATIONS,
                start__date__gte=date_from,
                start__date__lt=date_to,
                quantity_start__isnull=False,
            )
            .select_related(
                "work_station",
                "production_order",
                "production_order__customer",
            )
            .order_by(
                "start",
                "production_order__customer__name",
            )
        )

        # ============================================================
        # MAPA ZLECEŃ MAGAZYNOWYCH
        #
        # ProductionOrder.id_number:
        #   np. "TFP 123/26"
        #
        # Order:
        #   provider + order_id
        # ============================================================

        warehouse_orders = (
            Order.objects
            .select_related(
                "provider",
                "product",
            )
            .all()
        )

        order_map = {
            f"{order.provider} {order.order_id}": order
            for order in warehouse_orders
        }

        # ============================================================
        # WYKLUCZONE PRODUKTY
        # ============================================================

        excluded_products = {
            self._normalize_name(name)
            for name in self.EXCLUDED_PRODUCTS
        }

        # ============================================================
        # DANE RAPORTU
        # ============================================================

        rows = []

        total_quantity = 0

        product_summary = {}

        for unit in units_qs:
            production_order = unit.production_order

            # --------------------------------------------------------
            # WYMIARY
            # --------------------------------------------------------

            dimensions = production_order.cardboard_dimensions

            if not self._dimension_is_allowed(dimensions):
                continue

            # --------------------------------------------------------
            # PRODUKT
            # --------------------------------------------------------

            warehouse_order = order_map.get(
                production_order.id_number
            )

            product = (
                warehouse_order.product
                if warehouse_order
                else None
            )

            product_name = (
                product.name
                if product
                else "BRAK PRODUKTU"
            )

            normalized_product_name = self._normalize_name(
                product_name
            )

            # dokładne wykluczenie
            if normalized_product_name in excluded_products:
                continue

            # dodatkowe zabezpieczenie:
            # jeśli np. istnieje:
            # MERIDA | BC | KÓŁKA | INNY OPIS
            if normalized_product_name.startswith(
                "MERIDA | BC | KÓŁKA"
            ):
                continue

            # --------------------------------------------------------
            # ILOŚĆ
            # --------------------------------------------------------

            quantity = unit.quantity_start or 0

            total_quantity += quantity

            # --------------------------------------------------------
            # WIERSZ RAPORTU
            # --------------------------------------------------------

            rows.append({
                "customer": production_order.customer.name,
                "dimensions": dimensions,
                "quantity": quantity,
                "date": unit.start.date(),
                "workstation": unit.work_station.name,
                "product": product_name,
            })

            # --------------------------------------------------------
            # PODSUMOWANIE WG PRODUCT
            # --------------------------------------------------------

            if product_name not in product_summary:
                product_summary[product_name] = {
                    "quantity": 0,
                    "units": 0,
                }

            product_summary[product_name]["quantity"] += quantity
            product_summary[product_name]["units"] += 1

        # ============================================================
        # SORTOWANIE PODSUMOWANIA WG ILOŚCI
        # ============================================================

        product_summary = sorted(
            product_summary.items(),
            key=lambda x: x[1]["quantity"],
            reverse=True,
        )

        # ============================================================
        # RESPONSE
        # ============================================================

        response = HttpResponse(
            content_type="application/pdf"
        )

        filename = (
            f"tygle_{today.year}_"
            f"350x500-800x1500.pdf"
        )

        response["Content-Disposition"] = (
            f'inline; filename="{filename}"'
        )

        buffer = io.BytesIO()

        # ============================================================
        # DOKUMENT
        # ============================================================

        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(A4),
            rightMargin=12 * mm,
            leftMargin=12 * mm,
            topMargin=14 * mm,
            bottomMargin=14 * mm,
            title="Raport produkcji - tygle",
        )

        styles = getSampleStyleSheet()

        # ============================================================
        # STYLE
        # ============================================================

        title_style = ParagraphStyle(
            "ReportTitle",
            parent=styles["Title"],
            fontName=self.FONT_BOLD,
            fontSize=18,
            leading=22,
            spaceAfter=8,
        )

        subtitle_style = ParagraphStyle(
            "ReportSubtitle",
            parent=styles["Normal"],
            fontName=self.FONT_REGULAR,
            fontSize=9,
            leading=12,
            spaceAfter=10,
        )

        normal_style = ParagraphStyle(
            "TableNormal",
            parent=styles["Normal"],
            fontName=self.FONT_REGULAR,
            fontSize=8,
            leading=10,
        )

        right_style = ParagraphStyle(
            "Right",
            parent=styles["Normal"],
            fontName=self.FONT_REGULAR,
            fontSize=8,
            leading=10,
            alignment=TA_RIGHT,
        )

        body_style = ParagraphStyle(
            "Body",
            parent=styles["Normal"],
            fontName=self.FONT_REGULAR,
            fontSize=9,
            leading=12,
        )

        story = []

        # ============================================================
        # TYTUŁ
        # ============================================================

        story.append(
            Paragraph(
                (
                    f"Produkcja - TYGIEL MAŁY / "
                    f"TYGIEL DUŻY - {today.year}"
                ),
                title_style,
            )
        )

        story.append(
            Paragraph(
                (
                    f"Zakres dat: "
                    f"{date_from:%d.%m.%Y} - "
                    f"{today:%d.%m.%Y}<br/>"
                    f"Format arkusza: "
                    f"350x500 - 800x1500 mm"
                ),
                subtitle_style,
            )
        )

        story.append(
            Spacer(
                1,
                4 * mm,
            )
        )

        # ============================================================
        # TABELA SZCZEGÓŁOWA
        # ============================================================

        table_data = [
            [
                "Klient",
                "Format",
                "Ilość start",
                "Data",
                "Stanowisko",
                "Produkt",
            ]
        ]

        for row in rows:
            table_data.append([
                Paragraph(
                    str(row["customer"]),
                    normal_style,
                ),
                Paragraph(
                    str(row["dimensions"]),
                    normal_style,
                ),
                Paragraph(
                    f'{row["quantity"]:,}'.replace(",", " "),
                    right_style,
                ),
                Paragraph(
                    row["date"].strftime("%d.%m.%Y"),
                    normal_style,
                ),
                Paragraph(
                    row["workstation"],
                    normal_style,
                ),
                Paragraph(
                    row["product"],
                    normal_style,
                ),
            ])

        # ============================================================
        # SUMA
        # ============================================================

        table_data.append([
            Paragraph(
                "<b>SUMA</b>",
                normal_style,
            ),
            "",
            Paragraph(
                f'<b>{total_quantity:,}</b>'.replace(",", " "),
                right_style,
            ),
            "",
            "",
            "",
        ])

        table = Table(
            table_data,
            repeatRows=1,
            colWidths=[
                43 * mm,
                25 * mm,
                28 * mm,
                26 * mm,
                32 * mm,
                103 * mm,
            ],
        )

        table.setStyle(
            TableStyle([
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#263238"),
                ),
                (
                    "TEXTCOLOR",
                    (0, 0),
                    (-1, 0),
                    colors.white,
                ),
                (
                    "FONTNAME",
                    (0, 0),
                    (-1, 0),
                    self.FONT_BOLD,
                ),
                (
                    "FONTNAME",
                    (0, 1),
                    (-1, -1),
                    self.FONT_REGULAR,
                ),
                (
                    "FONTSIZE",
                    (0, 0),
                    (-1, -1),
                    8,
                ),
                (
                    "ALIGN",
                    (1, 0),
                    (4, -1),
                    "CENTER",
                ),
                (
                    "ALIGN",
                    (2, 1),
                    (2, -1),
                    "RIGHT",
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -2),
                    0.25,
                    colors.HexColor("#CFD8DC"),
                ),
                (
                    "LINEABOVE",
                    (0, -1),
                    (-1, -1),
                    1,
                    colors.black,
                ),
                (
                    "BACKGROUND",
                    (0, -1),
                    (-1, -1),
                    colors.HexColor("#ECEFF1"),
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),
            ])
        )

        story.append(table)

        # ============================================================
        # PODSUMOWANIE OGÓLNE
        # ============================================================

        story.append(
            Spacer(
                1,
                8 * mm,
            )
        )

        story.append(
            Paragraph(
                (
                    "<b>Łączna liczba jednostek produkcyjnych:</b> "
                    f"{len(rows)}"
                ),
                body_style,
            )
        )

        story.append(
            Spacer(
                1,
                2 * mm,
            )
        )

        story.append(
            Paragraph(
                (
                    "<b>Łączna ilość:</b> "
                    f'{total_quantity:,}'.replace(",", " ")
                ),
                body_style,
            )
        )

        # ============================================================
        # DRUGA STRONA
        # PODSUMOWANIE WG PRODUCT
        # ============================================================

        story.append(
            PageBreak()
        )

        story.append(
            Paragraph(
                "Podsumowanie według produktu",
                title_style,
            )
        )

        story.append(
            Paragraph(
                (
                    f"Produkcja od "
                    f"{date_from:%d.%m.%Y} "
                    f"do {today:%d.%m.%Y}"
                ),
                subtitle_style,
            )
        )

        story.append(
            Spacer(
                1,
                4 * mm,
            )
        )

        product_table_data = [
            [
                "Produkt",
                "Liczba jednostek",
                "Ilość",
                "% całości",
            ]
        ]

        for product_name, values in product_summary:
            quantity = values["quantity"]

            percent = (
                quantity / total_quantity * 100
                if total_quantity
                else 0
            )

            product_table_data.append([
                Paragraph(
                    product_name,
                    normal_style,
                ),
                Paragraph(
                    f'{values["units"]:,}'.replace(",", " "),
                    right_style,
                ),
                Paragraph(
                    f'{quantity:,}'.replace(",", " "),
                    right_style,
                ),
                Paragraph(
                    f"{percent:.1f}%",
                    right_style,
                ),
            ])

        product_table_data.append([
            Paragraph(
                "<b>SUMA</b>",
                normal_style,
            ),
            Paragraph(
                f"<b>{len(rows)}</b>",
                right_style,
            ),
            Paragraph(
                f'<b>{total_quantity:,}</b>'.replace(",", " "),
                right_style,
            ),
            Paragraph(
                "<b>100.0%</b>" if total_quantity else "<b>0.0%</b>",
                right_style,
            ),
        ])

        product_table = Table(
            product_table_data,
            repeatRows=1,
            colWidths=[
                156 * mm,
                38 * mm,
                38 * mm,
                30 * mm,
            ],
        )

        product_table.setStyle(
            TableStyle([
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#263238"),
                ),
                (
                    "TEXTCOLOR",
                    (0, 0),
                    (-1, 0),
                    colors.white,
                ),
                (
                    "FONTNAME",
                    (0, 0),
                    (-1, 0),
                    self.FONT_BOLD,
                ),
                (
                    "FONTNAME",
                    (0, 1),
                    (-1, -1),
                    self.FONT_REGULAR,
                ),
                (
                    "FONTSIZE",
                    (0, 0),
                    (-1, -1),
                    8,
                ),
                (
                    "ALIGN",
                    (1, 0),
                    (-1, -1),
                    "RIGHT",
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -2),
                    0.25,
                    colors.HexColor("#CFD8DC"),
                ),
                (
                    "LINEABOVE",
                    (0, -1),
                    (-1, -1),
                    1,
                    colors.black,
                ),
                (
                    "BACKGROUND",
                    (0, -1),
                    (-1, -1),
                    colors.HexColor("#ECEFF1"),
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),
            ])
        )

        story.append(product_table)

        # ============================================================
        # GENEROWANIE PDF
        # ============================================================

        doc.build(story)

        pdf = buffer.getvalue()
        buffer.close()

        response.write(pdf)

        return response