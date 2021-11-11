from django.shortcuts import render, HttpResponse, redirect
from django.views import View

from django.db.models import Q

from production.models import *
from production.forms import *

from django.template.loader import get_template

import os
from xhtml2pdf import pisa

from warehousemanager.functions import visit_counter

from warehousemanager.models import Absence, ExtraHour


class ProductionMenu(View):
    def get(self, request):
        return render(request, 'production/production-menu.html', locals())


class AllProductionOrders(View):
    def get(self, request):
        visit_counter(request.user, 'All Production Orders')
        title = 'Production Orders'
        production_orders = ProductionOrder.objects.all().order_by('id_number', 'dimensions')
        return render(request, 'production/production-all.html', locals())


class ProductionDetails(View):
    def get(self, request, production_order_id):
        production_order_statuses = PRODUCTION_ORDER_STATUSES
        production_order = ProductionOrder.objects.get(id=production_order_id)
        production_units = ProductionUnit.objects.filter(production_order=production_order).order_by('sequence')
        return render(request, 'production/production-details.html', locals())


class ChangeProductionStatus(View):
    def get(self, request):
        production_order_id = int(request.GET.get('production-order-id'))
        status = request.GET.get('status')
        production_order = ProductionOrder.objects.get(id=production_order_id)
        production_order.status = status
        production_order.save()

        return redirect('production-details', production_order_id=production_order.id)


class AddProductionOrder(View):
    def get(self, request):
        form = ProductionOrderForm()
        return render(request, 'production/production-order-add.html', locals())

    def post(self, request):
        form = ProductionOrderForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            id_number = data['id_number']
            cardboard = data['cardboard']
            cardboard_dimensions = data['cardboard_dimensions']
            customer = data['customer']
            dimensions = data['dimensions']
            quantity = data['quantity']
            status = data['status']
            completed = data['completed']
            priority = data['priority']
            notes = data['notes']

            if customer:
                customer = Buyer.objects.get(name=customer)

            try:
                ProductionOrder.objects.get(id_number=id_number)
            except ObjectDoesNotExist:
                ProductionOrder.objects.create(id_number=id_number, cardboard=cardboard,
                                               cardboard_dimensions=cardboard_dimensions, customer=customer,
                                               dimensions=dimensions, quantity=quantity, status=status,
                                               completed=completed, priority=priority, notes=notes)
        return redirect('all-production-orders')


class WorkStations(View):
    def get(self, request):
        visit_counter(request.user, 'Production Workstations')
        workers_data = []
        workers = Person.workers_at_work(datetime.date.today())
        for w in workers:
            if w.occupancy_type == 'PRODUCTION':
                workers_data.append((w, ProductionUnit.worker_occupancy(w)))
        stations = WorkStation.objects.all()
        return render(request, 'production/workstations.html', locals())


class WorkStationDetails(View):
    def get(self, request, workstation_id):
        def get_date_str(some_date):
            date = some_date
            date_str = f'{date.year}-'
            if date.month < 10:
                date_str += '0'
            date_str += f'{date.month}-'
            if date.day < 10:
                date_str += '0'
            date_str += f'{date.day}'
            return date_str

        date_string = get_date_str(datetime.date.today())

        station = WorkStation.objects.get(id=workstation_id)
        visit_counter(request.user, f'{station} - details')
        units = ProductionUnit.objects.filter(work_station=station)
        planned_units = units.filter(status='PLANNED').order_by('order')
        in_progress_units = units.filter(status='IN PROGRESS').order_by('order')
        other_units = units.filter(status='NOT STARTED').order_by('order')
        history_units = units.filter(status='FINISHED').order_by('-end')

        # counting machine set up
        '''def counting_machine_times(some_units):
            equations = []
            set_up_values = []
            for u in some_units:
                equation = (u.production_order.quantity, u.unit_duration_in_seconds())
                equations.append(equation)

            for num in range(len(equations)):
                equation_one = equations[num]
                for num_2 in range(len(equations)):
                    if num_2 != num:
                        equation_two = equations[num_2]

                        set_up_value = abs(equation_two[1] - equation_one[1])/abs(equation_two[0] - equation_one[0])

                        set_up_values.append(set_up_value)

            unit_sum_ups = (sum([x[1] for x in equations]), -sum([x[0] for x in equations]), len(equations))

            print(set_up_values)

            set_up_values = set(set_up_values)

            print(set_up_values)

            return sum(set_up_values)/len(set_up_values), unit_sum_ups

        result_1, result_2 = counting_machine_times(history_units)

        final_result = (result_2[0] + result_2[1] * result_1)/result_2[2]

        print(result_2[0], result_2[1], result_1, result_2[2])

        test_value = final_result // 60'''


        return render(request, 'production/workstation-details.html', locals())


class ProductionUnitDetails(View):
    def get(self, request, unit_id):
        unit = ProductionUnit.objects.get(id=unit_id)
        return render(request, 'production/production-unit-details.html', locals())


class EditProductionUnit(View):
    def get(self, request, unit_id):
        source = request.GET.get('source')
        edit = True
        form = ProductionUnitForm(instance=ProductionUnit.objects.get(id=unit_id))
        return render(request, 'production/production-unit-add.html', locals())

    def post(self, request, unit_id):
        form = ProductionUnitForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            sequence = data['sequence']
            production_order = data['production_order']
            work_station = data['work_station']
            order = data['order']
            status = data['status']
            estimated_time = data['estimated_time']
            start = data['start']
            end = data['end']
            quantity_start = data['quantity_start']
            quantity_end = data['quantity_end']
            notes = data['notes']
            persons = data['persons']
            source = None
            try:
                source = form.data.get('source')
            except KeyError:
                pass

            unit = ProductionUnit.objects.get(id=unit_id)

            unit.production_order = production_order
            unit.work_station = work_station
            unit.status = status
            unit.sequence = sequence
            unit.order = order
            unit.estimated_time = estimated_time
            unit.start = start
            unit.end = end
            unit.quantity_end = quantity_end
            unit.quantity_start = quantity_start
            unit.notes = notes

            if persons:
                unit.persons.clear()
                for p in persons:
                    unit.persons.add(p)

            unit.save()

            all_production_order_units = ProductionUnit.objects.filter(production_order=unit.production_order)

            all_finished = True
            all_planned = True
            for u in all_production_order_units:
                if u.status not in ('FINISHED', 'PLANNED'):
                    all_planned = False
                if u.status != 'FINISHED':
                    all_finished = False

            if all_finished:
                unit.production_order.status = 'FINISHED'
                unit.production_order.save()

            if all_planned:
                unit.production_order.status = 'PLANNED'
                unit.production_order.save()

            try:
                return redirect('workstation-details', workstation_id=int(source))
            except ValueError:
                return redirect('unit-details', unit_id=unit.id)


class AddProductionUnit(View):
    def get(self, request, order_id):
        production_order = ProductionOrder.objects.get(id=order_id)
        order_units = ProductionUnit.objects.filter(production_order=production_order)
        form = ProductionUnitForm(initial={'production_order': production_order, 'sequence': order_units.count() + 1})
        return render(request, 'production/production-unit-add.html', locals())

    def post(self, request, order_id):
        form = ProductionUnitForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            sequence = data['sequence']
            production_order = data['production_order']
            work_station = data['work_station']
            order = data['order']
            status = data['status']
            estimated_time = data['estimated_time']
            start = data['start']
            end = data['end']
            quantity_start = data['quantity_start']
            quantity_end = data['quantity_end']
            notes = data['notes']
            persons = data['persons']

            new_unit = ProductionUnit.objects.create(production_order=production_order, work_station=work_station,
                                                     status=status,
                                                     sequence=sequence, order=order, estimated_time=estimated_time,
                                                     start=start,
                                                     end=end, quantity_end=quantity_end, quantity_start=quantity_start,
                                                     notes=notes)

            for p in persons:
                new_unit.persons.add(p)

            return redirect('production-details', production_order_id=production_order.id)


class DeleteProductionUnit(View):
    def get(self, request, unit_id):
        unit = ProductionUnit.objects.get(id=unit_id)
        order_id = unit.production_order.id
        unit.delete()
        return redirect('production-details', production_order_id=order_id)


class StartProductionUnit(View):
    def get(self, request, unit_id):
        unit = ProductionUnit.objects.get(id=unit_id)
        unit.status = 'IN PROGRESS'
        unit.start = datetime.datetime.now()
        unit.save()

        return redirect('workstation-details', workstation_id=unit.work_station.id)


class FinishProductionUnit(View):
    def get(self, request, unit_id):
        unit = ProductionUnit.objects.get(id=unit_id)
        unit.status = 'FINISHED'
        unit.end = datetime.datetime.now()
        unit.save()

        all_production_order_units = ProductionUnit.objects.filter(production_order=unit.production_order)

        all_finished = True
        all_planned = True

        for u in all_production_order_units:
            if u.status not in ('FINISHED', 'PLANNED'):
                all_planned = False
            if u.status != 'FINISHED':
                all_finished = False

        if all_finished:
            unit.production_order.status = 'FINISHED'
            unit.production_order.save()
        elif all_planned:
            unit.production_order.status = 'PLANNED'
            unit.production_order.save()

        return redirect('workstation-details', workstation_id=unit.work_station.id)


class PlanProductionUnit(View):
    def get(self, request, unit_id):
        unit = ProductionUnit.objects.get(id=unit_id)
        unit.status = 'PLANNED'
        unit.order = ProductionUnit.last_in_line(unit.work_station) + 1
        unit.save()

        return redirect('workstation-details', workstation_id=unit.work_station.id)


class RemoveProductionUnit(View):
    def get(self, request, unit_id):
        unit = ProductionUnit.objects.get(id=unit_id)
        unit.status = 'NOT STARTED'
        unit.order = None
        unit.start = None
        unit.end = None
        unit.save()

        return redirect('workstation-details', workstation_id=unit.work_station.id)


class UpProductionUnit(View):
    def get(self, request, unit_id):
        unit = ProductionUnit.objects.get(id=unit_id)
        unit.move_up_unit()
        unit.save()

        return redirect('workstation-details', workstation_id=unit.work_station.id)


class DownProductionUnit(View):
    def get(self, request, unit_id):
        unit = ProductionUnit.objects.get(id=unit_id)
        unit.move_down_unit()
        unit.save()

        return redirect('workstation-details', workstation_id=unit.work_station.id)


class WorkersByMonth(View):
    def get(self, request, year, month):
        month_date = datetime.datetime.strptime(f'{year}-{month}', '%Y-%m').strftime("%B")
        month_date = f'{month_date} {year}'
        active_workers = Person.active_workers_at_month(year, month)
        return render(request, 'production/workers-by-month.html', locals())


class WorkerEfficiency(View):
    def get(self, request, year, month, worker_id):
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

        if month_end > datetime.datetime.today().date():
            month_end = datetime.datetime.today().date()

        working_days = 0
        absences = 0
        extra_hours = 0

        end_day = None
        start_day = month_start
        while start_day != month_end + datetime.timedelta(days=1):
            if worker.job_start <= start_day:
                if worker.job_end:
                    if worker.job_end >= start_day:
                        if start_day.isoweekday() < 6:
                            absence = Absence.objects.filter(worker=worker, absence_date=start_day)
                            absence = absence.exclude(absence_type='SP')
                            extra_h = ExtraHour.objects.filter(worker=worker, extras_date=start_day)
                            if extra_h:
                                extra_ho = extra_h[0]
                                if extra_ho.full_day:
                                    extra_hours += extra_ho.quantity
                                else:
                                    extra_hours += extra_ho.quantity - 8
                            if absence:
                                absences += 1
                            working_days += 1
                else:
                    if start_day.isoweekday() < 6:
                        absence = Absence.objects.filter(worker=worker, absence_date=start_day)
                        absence = absence.exclude(absence_type='SP')
                        extra_h = ExtraHour.objects.filter(worker=worker, extras_date=start_day)
                        if extra_h:
                            extra_ho = extra_h[0]
                            if extra_ho.full_day:
                                extra_hours += extra_ho.quantity
                            else:
                                extra_hours += extra_ho.quantity - 8
                        if absence:
                            absences += 1
                        working_days += 1
            start_day += datetime.timedelta(days=1)

        work_seconds = 36 * 800 * (working_days - absences) + extra_hours * 3600

        def working_hours(value_in_seconds):
            hours = value_in_seconds // 3600
            return hours

        work_hours = working_hours(work_seconds)
        days_at_work = working_days - absences
        days_at_work_to_count = days_at_work

        if work_hours != days_at_work_to_count * 8:
            days_at_work_to_count = round(work_hours // 8 + (work_hours % 8)/8, 2)

        month_end += datetime.timedelta(days=1)

        units = ProductionUnit.objects.filter(start__gte=month_start, end__lte=month_end, persons__id=worker_id).order_by('start')

        data = []

        efficiency = [0, 0]

        for unit in units:
            data.append([unit, ])
            if unit.estimated_duration_in_seconds() and unit.unit_duration_in_seconds():
                unit_fractal = unit.estimated_duration_in_seconds()/unit.unit_duration_in_seconds()
                unit_efficiency = round(100*unit_fractal, 2)
                data[-1].append(unit_efficiency)
                efficiency[0] += unit.estimated_duration_in_seconds()
                efficiency[1] += unit.unit_duration_in_seconds()

        efficiency = round(100*efficiency[0]/efficiency[1], 2) if efficiency[1] else 100

        pot = round(600 * (days_at_work_to_count/working_days), 2)

        return render(request, 'production/worker-efficiency.html', locals())


class WorkerEfficiencyPrintPDF(View):
    def get(self, request, year, month, worker_id):
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

        if month_end > datetime.datetime.today().date():
            month_end = datetime.datetime.today().date()

        working_days = 0
        absences = 0
        extra_hours = 0
        holidays = 0
        late = 0

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
                                    events_data.append((absence[0].absence_date, absence[0].absence_type, late_in_minutes))
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
            if unit.estimated_duration_in_seconds() and unit.unit_duration_in_seconds():

                unit_fractal = unit.estimated_duration_in_seconds() / unit.unit_duration_in_seconds()
                unit_efficiency = round(100 * unit_fractal, 2)
                data[-1].append(unit_efficiency)
                efficiency[0] += unit.estimated_duration_in_seconds()
                efficiency[1] += unit.unit_duration_in_seconds()

                # work stations
                if unit.work_station not in worker_stations:
                    worker_stations.append(unit.work_station)
                    units_stations.append([unit.work_station, 1, unit.unit_duration_in_seconds(), [unit.estimated_duration_in_seconds(), unit.unit_duration_in_seconds()]])
                else:
                    for us in units_stations:
                        if us[0] == unit.work_station:
                            us[1] += 1
                            us[2] += unit.unit_duration_in_seconds()
                            us[3][0] += unit.estimated_duration_in_seconds()
                            us[3][1] += unit.unit_duration_in_seconds()

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
                            works_with[0][2] += unit.unit_duration_in_seconds()
                            works_with[0][3][0] += unit.estimated_duration_in_seconds()
                            works_with[0][3][1] += unit.unit_duration_in_seconds()
                        else:
                            works_with.insert(0, ['-', 1, unit.unit_duration_in_seconds(), [unit.estimated_duration_in_seconds(), unit.unit_duration_in_seconds()]])
                    else:
                        works_with.append(['-', 1, unit.unit_duration_in_seconds(), [unit.estimated_duration_in_seconds(), unit.unit_duration_in_seconds()]])
                for coop in works_with:
                    for coworker_person in unit.persons.all():
                        if coworker_person == coop[0]:
                            coop[1] += 1
                            coop[2] += unit.unit_duration_in_seconds()
                            coop[3][0] += unit.estimated_duration_in_seconds()
                            coop[3][1] += unit.unit_duration_in_seconds()

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

        # work stations
        for us in units_stations:
            hours = us[2] // 3600
            minutes = (us[2] - hours * 3600) // 60
            seconds = us[2] % 60
            hours = hours if hours > 9 else f'0{hours}'
            minutes = minutes if minutes > 9 else f'0{minutes}'
            seconds = seconds if seconds > 9 else f'0{seconds}'
            us[2] = f'{hours}:{minutes}:{seconds}'
            us[3] = round(100 * us[3][0] / us[3][1], 2) if us[3][1] else 100

        units_stations = sorted(units_stations, key=lambda x:x[1], reverse=True)

        efficiency = round(100 * efficiency[0] / efficiency[1], 2) if efficiency[1] else 100

        pot = round(full_pot * float((days_at_work_to_count / working_days)), 2)

        suggested_bonus = 0

        if efficiency >= 100:
            suggested_bonus = 0.5 * pot * (1 + (efficiency - 100)/50)
            if suggested_bonus > pot:
                suggested_bonus = pot
        else:
            suggested_bonus = 0.5 * pot * (100-((100 - efficiency)*4))/100
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


class WorkStationEfficiency(View):
    def get(self, request, year, month, station_id):
        station = WorkStation.objects.get(id=station_id)

        date_start = datetime.datetime.strptime('2021-10-01', '%Y-%m-%d').date()
        date_end = datetime.datetime.strptime('2021-10-31', '%Y-%m-%d').date()

        units = ProductionUnit.objects.filter(start__gte=date_start, end__lte=date_end + datetime.timedelta(days=1), work_station=station).order_by('start')

        data = []

        efficiency = [0, 0]

        for unit in units:
            data.append([unit, ])
            if unit.estimated_duration_in_seconds() and unit.unit_duration_in_seconds():
                unit_fractal = unit.estimated_duration_in_seconds()/unit.unit_duration_in_seconds()
                unit_efficiency = round(100*unit_fractal, 2)
                data[-1].append(unit_efficiency)
                efficiency[0] += unit.estimated_duration_in_seconds()
                efficiency[1] += unit.unit_duration_in_seconds()

        efficiency = round(100*efficiency[0]/efficiency[1], 2) if efficiency[1] else 100

        return render(request, 'production/station-efficiency.html', locals())


class StationEfficiencyPrintPDF(View):
    def get(self, request, year, month, station_id):
        station = WorkStation.objects.get(id=station_id)

        if month == 2:
            days = 28 if year % 4 != 0 else 29
        elif month in (4, 6, 9, 11):
            days = 30
        else:
            days = 31

        date_start = datetime.datetime.strptime(f'{year}-{month}-01', '%Y-%m-%d').date()
        date_end = datetime.datetime.strptime(f'{year}-{month}-{days}', '%Y-%m-%d').date()

        units = ProductionUnit.objects.filter(start__gte=date_start, end__lte=date_end + datetime.timedelta(days=1),
                                              work_station=station).order_by('start')

        data = []

        coworkers = []
        works_with = []

        efficiency = [0, 0]

        for unit in units:
            data.append([unit, ])
            if unit.estimated_duration_in_seconds() and unit.unit_duration_in_seconds():

                unit_fractal = unit.estimated_duration_in_seconds() / unit.unit_duration_in_seconds()
                unit_efficiency = round(100 * unit_fractal, 2)
                data[-1].append(unit_efficiency)
                efficiency[0] += unit.estimated_duration_in_seconds()
                efficiency[1] += unit.unit_duration_in_seconds()

                # works with
                for coworker in unit.persons.all():
                    if coworker not in coworkers:
                        coworkers.append(coworker)
                        works_with.append([coworker, 0, 0, [0, 0]])
                for coop in works_with:
                    for coworker_person in unit.persons.all():
                        if coworker_person == coop[0]:
                            coop[1] += 1
                            coop[2] += unit.unit_duration_in_seconds()
                            coop[3][0] += unit.estimated_duration_in_seconds()
                            coop[3][1] += unit.unit_duration_in_seconds()

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

        efficiency = round(100 * efficiency[0] / efficiency[1], 2) if efficiency[1] else 100

        logo_url = os.environ['PAKER_MAIN'] + 'static/images/paker-logo.png'
        font_url = os.environ['PAKER_MAIN'] + 'static/fonts/roboto/'

        template_path = 'production/station-efficiency-pdf.html'
        context = locals()
        # Create a Django response object, and specify content_type as pdf
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'filename="report.pdf"'
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