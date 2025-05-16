from django.views import View
import datetime
import os
from warehousemanager.models import Person, Holiday, Absence, ExtraHour
from production.models import ProductionUnit
from xhtml2pdf import pisa
from django.template.loader import get_template
from django.shortcuts import HttpResponse


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