from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import permission_required
from django.core.paginator import Paginator
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views.generic.detail import DetailView
from django.views.generic.list import ListView
from django.urls import reverse_lazy
import calendar
import json
import qrcode
from io import BytesIO
import base64
from PIL import Image, ImageDraw, ImageFont
from warehousemanager.functions import *
from warehousemanager.forms import *
from django.template.loader import get_template
from xhtml2pdf import pisa


class StartPage(View):
    def get(self, request):
        user = request.user
        visit_counter(user, 'index')
        return render(request, 'start-page.html', locals())

    def post(self, request):
        name = request.POST.get('login')
        password = request.POST.get('password')

        user = authenticate(username=name, password=password)

        if user is not None:
            login(request, user)

        return redirect('start-page')


class LoginView(View):
    def get(self, request):
        print('here')
        user = request.user
        visit_counter(user, 'index')
        next_url = request.GET.get('next')
        print(next_url)
        return render(request, 'start-page.html', locals())

    def post(self, request):
        name = request.POST.get('login')
        password = request.POST.get('password')
        next_url = request.POST.get('next')

        user = authenticate(username=name, password=password)

        if user is not None:
            login(request, user)
        if next_url:
            return redirect(next_url)
        return redirect('start-page')


class LogoutView(View):
    def get(self, request):
        logout(request)

        return redirect('start-page')


class MainPageView(LoginRequiredMixin, View):
    login_url = reverse_lazy('login')

    def get(self, request):
        title = 'MAIN PAGE'
        orders = Order.objects.all()
        items = OrderItem.objects.all()
        workers = Person.objects.all()
        absences = Absence.objects.all()
        punches = Punch.objects.all()
        polymers = Photopolymer.objects.all()
        colors = Color.objects.all()
        deliveries = Delivery.objects.all()
        providers = CardboardProvider.objects.all()
        customers = Buyer.objects.all()

        return render(request, 'warehousemanager-main-page.html', locals())
        # return redirect('punches')


class AbsencesList(PermissionRequiredMixin, View):
    permission_required = 'warehousemanager.view_absence'

    def get(self, request):

        user = request.user
        visit_counter(user, 'absences')

        def month_days_function(month_and_year):
            if month_and_year.month in (1, 3, 5, 7, 8, 10, 12):
                days_num = 31
            elif month_and_year.month == 2:
                if month_and_year.year % 4 == 0:
                    days_num = 29
                else:
                    days_num = 28
            else:
                days_num = 30

            return days_num

        def weekday_of_month_days(some_date, day):
            weekday_ = datetime.datetime.strptime(f'{day}-{some_date.month}-{some_date.year}', '%d-%m-%Y')
            weekday_num = weekday_.weekday()

            return weekday_num

        def today_month():
            today = datetime.datetime.now()

            ab = datetime.datetime.strftime(today, '%d-%m-%Y')
            a_dt = datetime.datetime.strptime(ab, '%d-%m-%Y')

            am = months[int(a_dt.month - 1)]
            ay = a_dt.year

            aaa = am + ' ' + str(ay)

            return aaa

        def previous_and_next_month(some_date_str_yyyy_mm_dd):
            this_month = datetime.datetime.strptime(some_date_str_yyyy_mm_dd, '%Y-%m-%d').month
            this_year = datetime.datetime.strptime(some_date_str_yyyy_mm_dd, '%Y-%m-%d').year

            if int(this_month) == 12:
                next_month_num = 1
                prev_month_num = 11
                next_year = this_year + 1
                prev_year = this_year
            elif int(this_month) == 1:
                next_month_num = 2
                prev_month_num = 12
                next_year = this_year
                prev_year = this_year - 1
            else:
                next_month_num = int(this_month) + 1
                prev_month_num = int(this_month) - 1
                prev_year = this_year
                next_year = this_year
            return months[prev_month_num - 1] + f' {prev_year}', months[next_month_num - 1] + f' {next_year}'

        months = (
            'January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October',
            'November', 'December')

        month = request.GET.get('month')

        if not month:
            month = datetime.date.today()
            month_num = month.month
            year_num = month.year
            aa = today_month()
            month_date = datetime.datetime.today()
            day_num = month_date.day
            prev_month, next_month = previous_and_next_month(datetime.date.strftime(month, '%Y-%m-%d'))
        else:
            aa = month
            month_split = month.split()
            month_num = months.index(month_split[0]) + 1
            year_num = int(month_split[1])
            new_date = f'01-{months.index(month_split[0]) + 1}-{month_split[1]}'
            month_date = datetime.datetime.strptime(new_date, '%d-%m-%Y')
            if month_date.month == datetime.datetime.today().month and month_date.year == datetime.datetime.today().year:
                day_num = datetime.datetime.today().day
            else:
                day_num = 32
            prev_month, next_month = previous_and_next_month(f'{month_split[1]}-{months.index(month_split[0]) + 1}-01')

        month_year = aa.split()
        str_date = f'{month_year[1]}-{months.index(month_year[0]) + 1}-1'
        month_days = month_days_function(datetime.datetime.strptime(str_date, '%Y-%m-%d'))

        if request.user.is_superuser:
            workers = Person.objects.all().filter(
                job_start__lte=datetime.date(int(month_year[1]), months.index(month_year[0]) + 1, month_days))
            workers = workers.exclude(
                job_end__lt=datetime.date(int(month_year[1]), months.index(month_year[0]) + 1, 1))
            workers = list(workers)

            from .models import LocalSetting
            excluded_workers = LocalSetting.objects.filter(name='excluded_workers').first()
            ew_list = []
            if excluded_workers:
                for ew in excluded_workers.value.split(','):
                    worker = ew.split('_')
                    worker = Person.objects.filter(first_name=worker[0], last_name=worker[1]).first()
                    if worker:
                        if worker in workers:
                            workers.remove(worker)

            contracts = Contract.objects.filter(
                date_start__lte=datetime.date(int(month_year[1]), months.index(month_year[0]) + 1,
                                              calendar.monthrange(year_num, month_num)[1]))
            # contracts = contracts.exclude(date_end__lte=datetime.date(int(month_year[1]), months.index(month_year[0]) + 1, 1))
            workers_temp = []
            for c in contracts:
                if not c.date_end or c.date_end >= datetime.date(int(month_year[1]), months.index(month_year[0]) + 1,
                                                                 1):
                    if request.GET.get('uz') == 'yes':
                        if c.type == 'UZ':
                            workers_temp.append(c.worker)
                    elif request.GET.get('fz') == 'yes':
                        if c.type == 'FZ':
                            workers_temp.append(c.worker)
                    else:
                        if c.type == 'UOP':
                            workers_temp.append(c.worker)
            workers_ = []
            for w in workers_temp:
                if w in workers:
                    if w not in workers_:
                        workers_.append(w)
            workers = workers_
        else:
            try:
                workers = [Person.objects.get(user=request.user)]
            except ObjectDoesNotExist:
                workers = []

        mcp_month = months.index(month_year[0]) + 1
        mcp_year = month_year[1]

        absences = Absence.objects.all()

        a = datetime.datetime.strftime(month_date, '%d-%m-%Y')

        month_days = [(x, weekday_of_month_days(datetime.datetime.strptime(a, '%d-%m-%Y'), x)) for x in
                      range(1, month_days_function(month_date) + 1)]

        def month_list(start_date, end_date):
            start_date_str = datetime.datetime.strptime(start_date, '%d-%m-%Y')
            end_date_str = datetime.datetime.strptime(end_date, '%d-%m-%Y')

            month_year = str(start_date_str.month) + ' ' + str(start_date_str.year)
            month_year_end = str(end_date_str.month) + ' ' + str(end_date_str.year)

            months_list = []

            while month_year != month_year_end:
                month_num_arg = datetime.datetime.strftime(start_date_str, '%d-%m-%Y')
                month_num = datetime.datetime.strptime(month_num_arg, '%d-%m-%Y').month
                year = datetime.datetime.strptime(month_num_arg, '%d-%m-%Y').year
                month_name = months[int(month_num) - 1]
                months_list.append(month_name + ' ' + str(year))
                if start_date_str.month in (1, 3, 5, 7, 8, 10, 12):
                    days_num = 31
                elif start_date_str.month == 2:
                    if start_date_str.year % 4 == 0:
                        days_num = 29
                    else:
                        days_num = 28
                else:
                    days_num = 30
                start_date_str = start_date_str + datetime.timedelta(days=days_num)
                month_year = str(start_date_str.month) + ' ' + str(start_date_str.year)

            return months_list

        if datetime.date.today().month != 12:
            end_list_condition = next_month == f'{months[datetime.date.today().month]} {str(datetime.date.today().year)}'
        else:
            end_list_condition = next_month == f'{months[0]} {str(datetime.date.today().year + 1)}'
        end_plus_31 = datetime.datetime.today() + datetime.timedelta(days=31)
        z = month_list('01-01-2017', datetime.datetime.strftime(end_plus_31, '%d-%m-%Y'))

        return render(request, 'warehousemanager-absenceslist.html', locals())


class AbsencesAndHolidays(LoginRequiredMixin, View):
    login_url = reverse_lazy('login')


    def get(self, request):
        def days_without_work(worker, mm_yyyy_str):
            start = worker.job_start
            end = worker.job_end
            month__ = datetime.datetime.strptime(mm_yyyy_str, '%m-%Y')

            if month__.month in (1, 3, 5, 7, 8, 10, 12):
                days = 31
            elif month__.month == 2:
                days = 28
                if month__.year % 4 == 0:
                    days = 29
            else:
                days = 30

            result_days = []

            if start.month == month__.month and start.year == month__.year:
                result_days = [x for x in range(1, start.day)]
            if end:
                if end.month == month__.month and end.year == month__.year:
                    for y in range(end.day + 1, days + 1):
                        result_days.append(y)

            return worker.id, result_days

        months = (
            'January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October',
            'November',
            'December')
        month = request.GET.get('month')
        div_date = month.split()
        year = div_date[1]
        month_ = months.index(div_date[0]) + 1
        if month_ != 12:
            absences_objects = Absence.objects.all().filter(absence_date__gte=datetime.date(int(year), month_, 1),
                                                            absence_date__lt=datetime.date(int(year), month_ + 1, 1))
            holiday_objects = Holiday.objects.all().filter(holiday_date__gte=datetime.date(int(year), month_, 1),
                                                           holiday_date__lt=datetime.date(int(year), month_ + 1, 1))
        else:
            absences_objects = Absence.objects.all().filter(absence_date__gte=datetime.date(int(year), month_, 1),
                                                            absence_date__lt=datetime.date(int(year) + 1, 1, 1))
            holiday_objects = Holiday.objects.all().filter(holiday_date__gte=datetime.date(int(year), month_, 1),
                                                           holiday_date__lt=datetime.date(int(year) + 1, 1, 1))

        # deleting vacations on holidays
        '''for h in holiday_objects:
            absences = Absence.objects.all().filter(absence_date=h.holiday_date)
            if len(absences) > 0:
                for a in absences:
                    a.delete()'''

        workers = Person.objects.all()
        non_work_days = []

        for w in workers:
            r = days_without_work(w, f'{month_}-{year}')
            if len(r[1]) > 0:
                non_work_days.append(r)

        extra_hours = []
        non_full_days = []
        acquaintances = []
        unusual_absences = []
        month_start_date = datetime.date(int(year), month_, 1)
        month_days = 30 if month_ in (4, 6, 9, 11) else 31
        month_end_date = datetime.date(int(year), month_, 28 if month_ == 2 else month_days)
        e_h = ExtraHour.objects.all().filter(extras_date__gte=month_start_date).filter(extras_date__lte=month_end_date)

        for e in e_h:
            if e.full_day:
                extra_hours.append((e.worker.id, e.extras_date.day, float(e.quantity)))
            else:
                non_full_days.append((e.worker.id, e.extras_date.day, float(e.quantity)))

        absences_and_holidays = []
        for a in absences_objects:
            if a.absence_type != 'SP' and a.absence_type != 'IN':
                absences_and_holidays.append((a.worker.id, a.absence_date.day, a.absence_type, a.id))
            elif a.absence_type == 'IN':
                unusual_absences.append((a.worker.id, a.absence_date.day, a.absence_type, a.additional_info))
            else:
                value = change_minutes_to_hours(a.value) if a.value else 'no value'
                acquaintances.append((a.worker.id, a.absence_date.day, a.absence_type, value))
        for h in holiday_objects:
            absences_and_holidays.append((-1, h.holiday_date.day, h.name))
        return HttpResponse(
            json.dumps(
                (absences_and_holidays, non_work_days, extra_hours, non_full_days, acquaintances, unusual_absences)))


class GetLocalVar(View):
    def get(self, request, variable_name):
        if os.environ[variable_name]:
            return HttpResponse(json.dumps(os.environ[variable_name]))
        else:
            return redirect('manage')


class AbsenceEdit(PermissionRequiredMixin, View):
    permission_required = 'warehousemanager.change_absence'

    def get(self, request, absence_id):
        absence = Absence.object.get(id=int(absence_id))


# absence-view
class AbsenceAdd(PermissionRequiredMixin, View):
    permission_required = 'warehousemanager.add_absence'

    def get(self, request):
        worker = None
        day = None
        monthyear = None
        default_date = ''

        if request.GET.get('worker'):
            worker = Person.objects.get(id=int(request.GET.get('worker')))

        if request.GET.get('day'):
            day = request.GET.get('day') if int(request.GET.get('day')) > 9 else '0' + request.GET.get('day')

        if request.GET.get('monthyear'):
            monthyear = request.GET.get('monthyear')
            default_date = ' '.join((day, monthyear))
            default_date = default_date.split(' ')
            default_date = '-'.join(default_date[::-1])
            default_date = datetime.datetime.strptime(default_date, '%Y-%B-%d')
            default_date = datetime.date.strftime(default_date, '%Y-%m-%d')

        reason = 'UW'

        title = f'{default_date} absence'
        workers = Person.objects.all()
        reasons = ABSENCE_TYPES

        if all((worker, day, monthyear)):
            title = f'{worker.get_initials()} {default_date} absence'

            if len(Absence.objects.filter(worker=worker, absence_date=default_date)) > 0:
                reason = Absence.objects.filter(worker=worker, absence_date=default_date)[0].absence_type
                absence_edited = Absence.objects.filter(worker=worker, absence_date=default_date)[0]

            short_absence_form = AbsenceForm(initial={
                'worker': worker,
                'absence_date': default_date,
                'absence_type': reason
            })

            extra_hours_form = ExtraHoursForm(initial={
                'worker': worker,
                'extras_date': default_date
            }, auto_id='eh_%s')

        else:
            short_absence_form = AbsenceForm()
            extra_hours_form = ExtraHoursForm(auto_id='eh_%s')

        return render(request, 'warehousemanager-add-absence.html', locals())

    def post(self, request):
        short_absence_form = AbsenceForm(request.POST)
        extra_hours_form = ExtraHoursForm(request.POST)

        print(request.POST)

        if extra_hours_form.is_valid():
            worker = extra_hours_form.cleaned_data['worker']
            extras_date = extra_hours_form.cleaned_data['extras_date']
            extras_quantity = float(extra_hours_form.cleaned_data['quantity'])
            extras_day = extra_hours_form.cleaned_data['full_day']

            condition_one = extras_date <= worker.job_end if worker.job_end else True
            condition_two = extras_date >= worker.job_start

            if all((condition_one, condition_two)):

                if len(ExtraHour.objects.filter(worker=worker, extras_date=extras_date)) > 0:
                    new_extras = ExtraHour.objects.filter(worker=worker, extras_date=extras_date)[0]
                    old_data = f'{new_extras}'
                    new_extras.quantity = extras_quantity
                    new_extras.full_day = extras_day
                    new_extras.save()
                    new_data = f'{new_extras}'
                    visit_counter(request.user, f'{old_data}//{new_data}')
                else:

                    new_extras = ExtraHour.objects.create(worker=worker, extras_date=extras_date,
                                                          quantity=extras_quantity, full_day=extras_day)

                    new_extras.save()

            response = redirect('absence-list')
            response['Location'] += f'?month={change_month_num_to_name(extras_date.month)} {extras_date.year}'

            return response

        if short_absence_form.is_valid():
            worker = short_absence_form.cleaned_data['worker']
            absence_date = short_absence_form.cleaned_data['absence_date']
            absence_type = short_absence_form.cleaned_data['absence_type']

            condition_one = absence_date <= worker.job_end if worker.job_end else True
            condition_two = absence_date >= worker.job_start

            if all((condition_one, condition_two)):

                if len(Absence.objects.filter(worker=worker, absence_date=absence_date)) > 0:
                    new_absence = Absence.objects.filter(worker=worker, absence_date=absence_date)[0]
                    old_data = f'{new_absence}'
                    new_absence.absence_type = absence_type
                    new_absence.save()
                    new_data = f'{new_absence}'
                    visit_counter(request.user, f'{old_data}//{new_data}')
                else:

                    new_absence = Absence.objects.create(worker=worker, absence_date=absence_date,
                                                         absence_type=absence_type)

                    new_absence.save()

                if absence_type == 'SP':
                    new_absence.create_acquaintance(value=int(short_absence_form.cleaned_data['value']))
                elif absence_type == 'IN':
                    new_absence.create_unusual(additional_info=short_absence_form.cleaned_data['additional_info'])

            response = redirect('absence-list')
            response['Location'] += f'?month={change_month_num_to_name(absence_date.month)} {absence_date.year}'

            return response

        else:
            worker = request.POST.get('worker')
            first_day = request.POST.get('first_day')
            last_day = request.POST.get('last_day')
            absence_type = request.POST.get('type')
            additional_info = request.POST.get('additional_info')
            print(additional_info)

            worker_s = worker.split()
            worker_object = Person.objects.filter(first_name=worker_s[0], last_name=worker_s[1])[0]
            first_day_date = datetime.datetime.strptime(first_day, '%Y-%m-%d')
            last_day_date = datetime.datetime.strptime(last_day, '%Y-%m-%d')

            safety_counter = 0
            while first_day_date != last_day_date:
                if safety_counter < 15:
                    safety_counter += 1
                    if absence_type == 'IN':
                        if additional_info:
                            new_absence = Absence(worker=worker_object, absence_date=first_day_date,
                                                  absence_type=absence_type, additional_info=additional_info)
                        else:
                            new_absence = Absence(worker=worker_object, absence_date=first_day_date,
                                                  absence_type=absence_type)
                        new_absence.save()
                    else:
                        if first_day_date.weekday() < 5:
                            new_absence = Absence(worker=worker_object, absence_date=first_day_date,
                                                  absence_type=absence_type)
                            new_absence.save()
                        else:
                            if absence_type == 'CH':
                                new_absence = Absence(worker=worker_object, absence_date=first_day_date,
                                                      absence_type=absence_type)
                                new_absence.save()
                            else:
                                pass
                    first_day_date = first_day_date + datetime.timedelta(days=1)
                    if first_day_date == last_day_date:
                        new_absence = Absence(worker=worker_object, absence_date=first_day_date,
                                              absence_type=absence_type, additional_info=additional_info)
                        new_absence.save()
                else:
                    break

            return redirect('absence-list')


# absence-delete
class AbsenceDelete(PermissionRequiredMixin, View):
    permission_required = 'warehousemanager.delete_absence'

    def post(self, request):
        absence = Absence.objects.get(id=int(request.POST.get('absence_id')))
        absence_info = f'{absence.worker}-{absence.absence_type}-{absence.absence_date}-by: {request.user}'
        absence.delete()

        visit_counter(request.user, 'absence-delete ' + absence_info)

        return HttpResponse(request.POST.get('absence_id'))


class PunchesList(PermissionRequiredMixin, View):
    permission_required = 'warehousemanager.view_punch'

    def get(self, request):
        if request.GET.get('all') == 'yes':
            only_active = False
        else:
            only_active = True
        PUNCH_TYPES_COLORS = (
            ('471', 'FEFCO 471', '#D49AE9'),
            ('427', 'FEFCO 427', 'white'),
            ('426', 'FEFCO 426', '#43E2C8'),
            ('421', 'FEFCO 421', '#FFD8FF'),
            ('201', 'FEFCO 201', 'orange'),
            ('SWT', 'Spody, wieka, tacki', '#FF6CA7'),
            ('KR', 'Krata', 'blue'),
            ('NR', 'Narożnik', 'green'),
            ('PDK', 'Pozostałe do klejenia', 'yellow'),
            ('WK', 'Wkład', 'red'),
            ('INNE', 'Inne', 'lightblue')
        )
        user = request.user
        visit_counter(user, 'punches')

        punches = Punch.objects.all().order_by('type', 'type_letter', 'type_num')
        if only_active:
            punches = punches.filter(active=True)
        punch_types = PUNCH_TYPES_COLORS
        title = 'PUNCHES'

        return render(request, 'warehousemanager-punches-list.html', locals())


class PunchAdd(PermissionRequiredMixin, View):
    permission_required = 'warehousemanager.add_punch'

    def get(self, request):
        user = request.user
        visit_counter(user, 'punch_add')

        punch_form = PunchForm()

        return render(request, 'warehousemanager-punch-add.html', locals())

    def post(self, request):
        punch_form = PunchForm(request.POST)

        if punch_form.is_valid():
            punch_type = punch_form.cleaned_data['type']
            type_letter = type_num = punch_form.cleaned_data['type_letter']
            type_num = punch_form.cleaned_data['type_num']
            name = punch_form.cleaned_data['name']
            dimension_one = punch_form.cleaned_data['dimension_one']
            dimension_two = punch_form.cleaned_data['dimension_two']
            dimension_three = punch_form.cleaned_data['dimension_three']
            quantity = punch_form.cleaned_data['quantity']
            size_one = punch_form.cleaned_data['size_one']
            size_two = punch_form.cleaned_data['size_two']
            cardboard = punch_form.cleaned_data['cardboard']
            pressure_large = punch_form.cleaned_data['pressure_large']
            pressure_small = punch_form.cleaned_data['pressure_small']
            wave_direction = punch_form.cleaned_data['wave_direction']
            customers = punch_form.cleaned_data['customers']

            new_punch = Punch.objects.create(type=punch_type, type_num=type_num, dimension_one=dimension_one,
                                             dimension_two=dimension_two, dimension_three=dimension_three,
                                             quantity=quantity, size_one=size_one, size_two=size_two,
                                             cardboard=cardboard, pressure_large=pressure_large,
                                             pressure_small=pressure_small, wave_direction=wave_direction, name=name,
                                             type_letter=type_letter)

            for c in customers:
                new_punch.customers.add(c)

            new_punch.save()

            return redirect('punches')


class PunchDetails(PermissionRequiredMixin, View):
    permission_required = 'warehousemanager.view_punch'

    def get(self, request, punch_id):
        p = get_object_or_404(Punch, id=punch_id)
        production = PunchProduction.objects.filter(punch=p)

        wear = 0
        for pr in production:
            wear += pr.quantity

        return render(request, 'warehousemanager-punch-details.html', locals())


class PunchEdit(PermissionRequiredMixin, View):
    permission_required = 'warehousemanager.change_punch'

    def get(self, request, punch_id):
        p = get_object_or_404(Punch, id=punch_id)
        punch_form = PunchForm(instance=p)
        edit = True

        return render(request, 'warehousemanager-punch-add.html', locals())

    def post(self, request, punch_id):
        punch_form = PunchForm(request.POST)

        if punch_form.is_valid():
            punch_type = punch_form.cleaned_data['type']
            type_letter = punch_form.cleaned_data['type_letter']
            type_num = punch_form.cleaned_data['type_num']
            name = punch_form.cleaned_data['name']
            dimension_one = punch_form.cleaned_data['dimension_one']
            dimension_two = punch_form.cleaned_data['dimension_two']
            dimension_three = punch_form.cleaned_data['dimension_three']
            quantity = punch_form.cleaned_data['quantity']
            size_one = punch_form.cleaned_data['size_one']
            size_two = punch_form.cleaned_data['size_two']
            cardboard = punch_form.cleaned_data['cardboard']
            pressure_large = punch_form.cleaned_data['pressure_large']
            pressure_small = punch_form.cleaned_data['pressure_small']
            wave_direction = punch_form.cleaned_data['wave_direction']
            customers = punch_form.cleaned_data['customers']
            active = punch_form.cleaned_data['active']

            edited_punch = Punch.objects.get(id=punch_id)

            edited_punch.type = punch_type
            edited_punch.type_num = type_num
            edited_punch.dimension_one = dimension_one
            edited_punch.dimension_two = dimension_two
            edited_punch.dimension_three = dimension_three
            edited_punch.quantity = quantity
            edited_punch.size_one = size_one
            edited_punch.size_two = size_two
            edited_punch.cardboard = cardboard
            edited_punch.pressure_small = pressure_small
            edited_punch.pressure_large = pressure_large
            edited_punch.wave_direction = wave_direction
            edited_punch.name = name
            edited_punch.type_letter = type_letter
            edited_punch.active = active

            edited_punch.customers.clear()

            for c in customers:
                edited_punch.customers.add(c)

            edited_punch.save()

            return redirect('punches')


class PunchDelete(PermissionRequiredMixin, View):
    permission_required = 'warehousemanager.delete_punch'

    def get(self, request, punch_id):
        p = get_object_or_404(Punch, id=punch_id)
        production = PunchProduction.objects.filter(punch=p)
        if production:
            return redirect('announcement')
        p.delete()

        return redirect('punches')


class AddBuyer(PermissionRequiredMixin, View):
    permission_required = 'warehousemanager.add_buyer'

    def get(self, request):
        buyer_form = BuyerForm()

        return render(request, 'warehousemanager-add-buyer.html', locals())

    def post(self, request):
        buyer_form = BuyerForm(request.POST)

        if buyer_form.is_valid():
            name = buyer_form.cleaned_data['name']
            new_buyer = Buyer.objects.create(name=name)
            new_buyer.save()

            return redirect('manage')


class BuyersList(PermissionRequiredMixin, View):
    permission_required = 'warehousemanager.view_buyer'

    def get(self, request):
        buyers = Buyer.objects.all()

        return render(request, 'warehousemanager-buyers-list.html', locals())


class PhotoPolymers(PermissionRequiredMixin, View):
    permission_required = 'warehousemanager.view_photopolymer'

    def get(self, request):

        user = request.user
        visit_counter(user, 'polymer_list')

        polymers = Photopolymer.objects.all()
        services = PhotopolymerService.objects.all()
        current_services = []
        history_services = []

        for s in services:
            if s.status():
                current_services.append(s)
            else:
                history_services.append(s)
        return render(request, 'warehousemanager-photopolymers.html', locals())


class PhotoPolymerDetail(PermissionRequiredMixin, View):
    permission_required = 'warehousemanager.view_photopolymer'

    def get(self, request, polymer_id):
        polymer = Photopolymer.objects.get(id=polymer_id)
        services = PhotopolymerService.objects.filter(photopolymer=polymer)
        colors = polymer.colors.all()

        return render(request, 'warehousemanager-polymer-detail.html', locals())


class PolymerCreate(PermissionRequiredMixin, CreateView):
    permission_required = 'warehousemanager.change_photopolymer'
    model = Photopolymer
    fields = ['producer', 'identification_number', 'customer', 'name', 'delivery_date', 'project']


class PolymerUpdate(PermissionRequiredMixin, UpdateView):
    permission_required = 'warehousemanager.change_photopolymer'

    model = Photopolymer
    fields = ['producer', 'identification_number', 'customer', 'name', 'delivery_date', 'project']
    template_name_suffix = '_update_form'


class PolymerDelete(PermissionRequiredMixin, DeleteView):
    permission_required = 'warehousemanager.delete_photopolymer'
    model = Photopolymer
    success_url = reverse_lazy('photopolymers')


class ServiceDetailView(PermissionRequiredMixin, DetailView):
    permission_required = 'warehousemanager.view_photopolymer_service'
    model = PhotopolymerService


class ServiceListView(PermissionRequiredMixin, ListView):
    permission_required = 'warehousemanager.view_photopolymer_service'
    model = PhotopolymerService


class ServiceCreate(PermissionRequiredMixin, CreateView):
    permission_required = 'warehousemanager.add_photopolymer_service'
    model = PhotopolymerService
    fields = ['photopolymer', 'send_date', 'company', 'service_description', 'return_date']


class ServiceUpdate(PermissionRequiredMixin, UpdateView):
    permission_required = 'warehousemanager.change_photopolymer_service'
    model = PhotopolymerService
    fields = ['photopolymer', 'send_date', 'company', 'service_description', 'return_date']
    template_name_suffix = '_update_form'


class ServiceDelete(PermissionRequiredMixin, DeleteView):
    permission_required = 'warehousemanager.delete_photopolymer_service'
    model = PhotopolymerService
    success_url = reverse_lazy('photopolymers')


class ColorListView(PermissionRequiredMixin, ListView):
    permission_required = 'warehousemanager.view_color'
    model = Color


class ColorRefresh(PermissionRequiredMixin, View):
    permission_required = 'warehousemanager.view_color'
    def get(self, request):
        for color in Color.objects.all():
            weight = 0
            for bucket in ColorBucket.objects.filter(color=color):
                weight += bucket.weight
            color.availability = weight
            color.save()

        return redirect('colors')


class ColorDetail(PermissionRequiredMixin, View):
    permission_required = 'warehousemanager.view_color'

    def get(self, request, color_id):
        c = Color.objects.get(id=color_id)

        polymers = Photopolymer.objects.filter(colors=c)
        buckets = ColorBucket.objects.filter(color=c)

        return render(request, 'warehousemanager-color-detail.html', locals())


class BucketDetail(View):
    def get(self, request, bucket_id):
        bucket = ColorBucket.objects.get(id=bucket_id)

        bucket_url = request.build_absolute_uri(reverse('bucket-details', args=[bucket_id]))

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )

        qr.add_data(bucket_url)
        qr.make(fit=True)

        # Generowanie obrazu QR
        img = qr.make_image(fill="black", back_color="white")

        # Konwersja do base64, aby można było osadzić w HTML
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        qr_code_base64 = base64.b64encode(buffer.getvalue()).decode()

        color = bucket.color
        color_hex = color.hex()

        today = datetime.date.today()

        data_str = bucket.usage

        history = data_str.split('/')
        data = []

        for h in history:
            data.append(h.split(';'))

        context = {
            'bucket': bucket,
            'qr_code': qr_code_base64,
            'color_hex': color_hex,
            'today': f'{today}',
            'start_value': bucket.weight,
            'data': data,
            'color': color
        }

        return render(request, 'warehousemanager-bucket-details.html', context)

    def post(self, request, bucket_id):
        bucket = ColorBucket.objects.get(id=bucket_id)
        date = request.POST.get("value0")
        value1 = request.POST.get("value1")
        value2 = request.POST.get("value2")

        # Aktualizacja historii użytkowania
        new_entry = f"{date};{value1};{value2}"
        bucket.usage = f"{bucket.usage}/{new_entry}" if bucket.usage else new_entry
        bucket.weight = value2
        bucket.save()

        return redirect('bucket-details', bucket_id=bucket.id)


class BucketQRCode(View):
    def get(self, request, bucket_id):
        bucket = get_object_or_404(ColorBucket, id=bucket_id)

        # Generowanie poprawnego URL do szczegółów wiadra
        bucket_url = request.build_absolute_uri(reverse('bucket-details', args=[bucket_id]))

        # Tworzymy kod QR z większym rozmiarem
        qr = qrcode.QRCode(
            version=1,  # Wersja większa (większa wersja - większy kod)
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=30,  # Zwiększenie rozmiaru pudełek
            border=4,
        )
        qr.add_data(bucket_url)
        qr.make(fit=True)

        qr_img = qr.make_image(fill="black", back_color="white")

        # Wymiary strony A4 w pikselach przy 300 DPI
        a4_width = 2480  # 210mm * 300 DPI
        a4_height = 3508  # 297mm * 300 DPI
        half_a4_height = a4_height // 2

        # Tworzymy nowy obrazek, na którym będą dwa zestawy kodu QR
        img = Image.new("RGB", (a4_width, half_a4_height * 2), "white")

        # Obliczanie pozycji wyśrodkowania QR
        qr_x = (a4_width - qr_img.width) // 2  # Pozycja X do wyśrodkowania
        qr_y = (half_a4_height - qr_img.height) // 2  # Pozycja Y do wyśrodkowania

        # Pierwszy obrazek QR - wyśrodkowany
        img.paste(qr_img, (qr_x, qr_y))

        # Dodanie kwadracika w kolorze wiadra obok kodu QR
        color_square_size = 500  # Rozmiar kwadracika
        color_square_position = (qr_x - color_square_size - 10, qr_y + 20)  # Pozycja kwadracika obok QR
        color_square_position2 = (qr_x - color_square_size - 10, qr_y + half_a4_height)

        color = bucket.color.hex()  # Zakładając, że color to np. #FF5733 lub 'red'
        color_square = Image.new("RGB", (color_square_size, color_square_size), color)
        img.paste(color_square, color_square_position)
        img.paste(color_square, color_square_position2)

        # Rysowanie tekstu pod pierwszym QR
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("DejaVuSans.ttf", 60)  # Czcionka systemowa, rozmiar 40
        except IOError:
            font = ImageFont.load_default()

        # Więcej informacji o wiadrze
        text = f"ID: {bucket.id}\nKolor: {bucket.color}\n"
        text += (f"Dostawca: {bucket.provider}\nData produkcji: {bucket.production_date}\n"
                 f"Data ważności: {bucket.expiration_date}")

        # Rysowanie tekstu pod pierwszym kodem QR
        text_position = (10, qr_img.size[1] + 10)
        draw.text(text_position, text, fill="black", font=font)

        # Drugi obrazek QR poniżej pierwszego
        img.paste(qr_img, (qr_x, half_a4_height + qr_y))  # Drugi obrazek poniżej pierwszego

        # Rysowanie tekstu pod drugim QR
        text_position = (10, qr_img.size[1] + half_a4_height + 10)
        draw.text(text_position, text, fill="black", font=font)

        # Konwersja do pliku
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)

        # Zwracamy plik do pobrania
        response = HttpResponse(buffer.getvalue(), content_type="image/png")
        response["Content-Disposition"] = f'attachment; filename="bucket_{bucket_id}_qr_double.png"'
        return response


class AvailableVacation(PermissionRequiredMixin, View):
    permission_required = 'warehousemanager.view_absence'

    def get(self, request):
        title = 'Available Vacations'
        year = datetime.datetime.now().year if not request.GET.get('year-choice') else int(
            request.GET.get('year-choice'))
        years = [x for x in range(2020, datetime.datetime.now().year + 2)]
        persons_data = []
        if request.user.username == 'damian':
            persons = Person.objects.filter(job_end=None)
        else:
            try:
                persons = [Person.objects.get(user=request.user)]
            except ObjectDoesNotExist:
                persons = []
        for p in persons:
            vacation_in_year = p.worker_vacation_in_year(year)
            person_vacations = p.worker_vacations(year)
            vacation = person_vacations['UW'] if 'UW' in person_vacations.keys() else 0
            vacation_on_demand = person_vacations['UŻ'] if 'UŻ' in person_vacations.keys() else 0
            vacations_summary = vacation + vacation_on_demand
            persons_data.append((p, vacation_in_year, p.vacation_left(year), vacations_summary, vacation_in_year + p.vacation_left(year) - vacations_summary))

        return render(request, 'warehousemanager-vacation-list.html', locals())


class PersonsVacations(PermissionRequiredMixin, View):
    permission_required = 'warehousemanager.view_absence'

    def get(self, request, person_id):
        person = Person.objects.get(id=person_id)
        title = f'{person} Vacations'
        absences = Absence.objects.filter(worker=person)
        return render(request, 'warehousemanager-vacation-person.html', locals())


# absence-view
class PersonAbsences(PermissionRequiredMixin, View):
    permission_required = 'warehousemanager.view_absence'

    def get(self, request, person_id):
        person = Person.objects.get(id=person_id)

        title = f'{person.get_initials()} Absences'

        visit_counter(request.user, f'personal-abs({person.get_initials()})')
        person_absences = Absence.objects.filter(worker=person)
        person_additional_events = ExtraHour.objects.filter(worker=person)

        all_events = []
        for a in person_absences:
            all_events.append((0, a.absence_date, a.absence_type, change_minutes_to_hours(a.value) if a.value else ''))
        for e in person_additional_events:
            all_events.append((1, e.extras_date, 'EX H' if e.full_day else 'NOT FULL', e.quantity))

        all_events = sorted(all_events, key=lambda x: x[1])

        return render(request, 'warehousemanager-person-absences.html', locals())


# person view
class PersonListView(PermissionRequiredMixin, View):
    permission_required = 'warehousemanager.view_person'

    def get(self, request):
        title = 'WORKERS'
        visit_counter(request.user, 'Person List View')
        former_workers = Person.objects.filter(job_end__isnull=False).order_by('last_name')
        today_workers = Person.objects.filter(job_end=None)
        for t in today_workers:
            create_or_send_reminder(t, check_contract_expiration_date(t), 'contract')
            create_or_send_reminder(t, check_medical_examination_expiration_date(t), 'medical examination')
        return render(request, 'warehousemanager-person-list.html', locals())


# person view
class PersonDetailView(PermissionRequiredMixin, View):
    permission_required = 'warehousemanager.view_person'

    def get(self, request, person_id):
        person = Person.objects.get(id=person_id)
        visit_counter(request.user, f'Person details - {person.get_initials()}')
        contracts = Contract.objects.filter(worker=person).order_by('date_start')
        return render(request, 'warehousemanager-person-details.html', locals())


# contract view
class ContractCreate(PermissionRequiredMixin, CreateView):
    permission_required = 'warehousemanager.add_contract'
    model = Contract
    fields = ['worker', 'type', 'date_start', 'date_end', 'salary', 'extra_info']


# reminder view
class ReminderListView(PermissionRequiredMixin, View):
    permission_required = 'warehousemanager.view_reminder'

    def get(self, request):
        reminders = Reminder.objects.all().order_by('create_date')
        return render(request, 'warehousemanager-reminders-list.html', locals())


class ReminderDetailsView(PermissionRequiredMixin, View):
    permission_required = 'warehousemanager.view_reminder'

    def get(self, request, reminder_id):
        reminder = Reminder.objects.get(id=int(reminder_id))
        reminder_content = compose_mail(reminder)
        if not reminder.sent_date:
            reminder.sent_date = datetime.date.today()
            reminder.save()

        return render(request, 'warehousemanager-reminder-details.html', locals())


class ReminderDeleteView(PermissionRequiredMixin, View):
    permission_required = 'warehousemanager.delete_reminder'

    def get(self, request, reminder_id):
        reminder = Reminder.objects.get(id=int(reminder_id))
        reminder.delete()

        return redirect('reminders')


class PaletteQuantitiesView(PermissionRequiredMixin, View):
    permission_required = 'warehousemanager.view_palette'

    def get(self, request):
        providers = CardboardProvider.objects.all()
        provider = request.GET.get('provider')
        date_from = request.GET.get('date-from')
        date_to = request.GET.get('date-to')

        date_from_text = date_from if date_from else '2017-01-01'
        date_to_text = date_to if date_to else datetime.date.strftime(datetime.date.today(), '%Y-%m-%d')

        provider_object = CardboardProvider.objects.get(
            shortcut=provider) if provider else CardboardProvider.objects.get(shortcut='AQ')

        all_deliveries = []

        palettes = Palette.objects.all().order_by('type', 'width')

        palettes_list = []
        for p in palettes:
            palettes_list.append(p)

        deliveries_query = Delivery.objects.filter(provider=provider_object,
                                                   date_of_delivery__gte=datetime.datetime.strptime(date_from_text,
                                                                                                    '%Y-%m-%d'),
                                                   date_of_delivery__lte=datetime.datetime.strptime(date_to_text,
                                                                                                    '%Y-%m-%d'))

        for delivery in deliveries_query:
            result = [(delivery.date_of_delivery, delivery.id)] + ['-' for _ in palettes_list] + ['-' for _ in
                                                                                                  palettes_list]
            for p in PaletteQuantity.objects.filter(delivery=delivery):
                if p.status == 'DEL':
                    result[palettes_list.index(p.palette) + 1] = p.quantity
                else:
                    result[palettes_list.index(p.palette) + 1 + len(palettes)] = p.quantity
            all_deliveries.append(result)

        current_quantity_table_data = [['-' for _ in palettes_list], ['-' for _ in palettes_list],
                                       ['-' for _ in palettes_list]]
        for p in palettes_list:
            provider = provider if provider else 'AQ'

            palette_type = p.type
            palette_dimensions = f'{p.width}x{p.height}'

            del_palettes = PaletteQuantity.all_quantities_between_dates(provider=provider, palette_type=palette_type,
                                                                        palette_dimensions=palette_dimensions,
                                                                        date_from=date_from_text, date_to=date_to_text)
            ret_palettes = PaletteQuantity.all_quantities_between_dates(provider=provider, palette_type=palette_type,
                                                                        palette_dimensions=palette_dimensions,
                                                                        date_from=date_from_text, date_to=date_to_text,
                                                                        status='RET')
            difference = del_palettes - ret_palettes

            current_quantity_table_data[0][palettes_list.index(p)] = del_palettes
            current_quantity_table_data[1][palettes_list.index(p)] = ret_palettes
            current_quantity_table_data[2][palettes_list.index(p)] = difference

        return render(request, 'warehousemanager-palettes-quantities.html', locals())


# profile-view
class ProfileView(LoginRequiredMixin, View):
    login_url = reverse_lazy('login')

    def get(self, request):
        user = request.user
        form = PasswordForm()
        return render(request, 'warehousemanager-profile.html', locals())

    def post(self, request):

        form = PasswordForm(request.POST)
        user = request.user

        if form.is_valid():
            username = user.username

            if user.check_password(form.cleaned_data['old_password']) and form.cleaned_data['new_password'] == \
                    form.cleaned_data['repeated_password']:
                user.set_password(form.cleaned_data['new_password'])
                user.save()

                username = user.username

                user = authenticate(username=username, password=form.cleaned_data['new_password'])

                if user is not None:
                    login(request, user)

                statement = 'Password changed'

            else:

                statement = 'Password change unsuccessful'

            return render(request, 'warehousemanager-profile.html', locals())


class MonthlyCardPresence(LoginRequiredMixin, View):
    login_url = reverse_lazy('login')

    def get(self, request, year, month, worker_id):

        def get_weekday_name(day_num):
            names = ('Pn', 'Wt', 'Śr', 'Cz', 'Pt', 'So', 'Nd')
            return names[day_num]

        def clear_some_data(some_list, list_of_indexes):
            for num in list_of_indexes:
                some_list[num] = ''

        worker = Person.objects.get(id=worker_id)
        date_from = datetime.datetime.strptime(f"{request.GET.get('from')} 00:00:00",
                                               '%Y-%m-%d %H:%M:%S') if request.GET.get('from') else None
        date_to = datetime.datetime.strptime(f"{request.GET.get('to')} 23:59:59",
                                             '%Y-%m-%d %H:%M:%S') if request.GET.get('to') else None

        now = datetime.datetime.now()

        summary = [0 for _ in range(19)]

        if month == 2:
            days = 28 if year % 4 != 0 else 29
        elif month in (4, 6, 9, 11):
            days = 30
        else:
            days = 31

        date_start = datetime.datetime.strptime(f'{year}-{month}-01', '%Y-%m-%d').date()
        date_end = datetime.datetime.strptime(f'{year}-{month}-{days}', '%Y-%m-%d').date()
        data = []

        days_data = [d for d in range(1, days + 1)]

        days_data_expanded = []

        for d in days_data:
            day = datetime.datetime.strptime(f'{year}-{month}-{d}', '%Y-%m-%d')
            day_info = []

            absence_type = None
            delay = None

            extra_hours = None
            extra_hours_value_h = None
            extra_hours_value_m = None
            extra_hours_sign = None

            vacation_day = None
            vacation_day_on_demand = None
            vacation_day_quarantine = None
            vacation_special = None
            vacation_free = None
            vacation_care = None
            vacation_illness = None
            vacation_other = None

            isolation = None
            unexcused_absence = None

            work_during_sunday_and_holidays = 0
            work_during_saturdays_and_free_days = 0
            extra_hours_value_to_add = 0

            try:
                holiday = Holiday.objects.get(holiday_date=day)
            except ObjectDoesNotExist:
                holiday = None

            try:
                absences = Absence.objects.get(worker=worker, absence_date=day)
            except ObjectDoesNotExist:
                absences = None

            try:
                extra_hours = ExtraHour.objects.get(worker=worker, extras_date=day)
            except ObjectDoesNotExist:
                extra_hours = None

            if absences:
                absence_type = absences.absence_type
                if absence_type == 'SP':
                    delay = absences.value
                elif absence_type == 'UW':
                    vacation_day = 1
                    summary[9] += 1
                elif absence_type == 'UŻ':
                    vacation_day_on_demand = 1
                    summary[10] += 1
                elif absence_type == 'KW':
                    vacation_day_quarantine = 1
                    summary[11] += 1
                elif absence_type == 'UO':
                    vacation_special = 1
                    summary[12] += 1
                elif absence_type == 'UB':
                    vacation_free = 1
                    summary[13] += 1
                elif absence_type == 'OP':
                    vacation_care = 1
                    summary[14] += 1
                elif absence_type == 'CH':
                    vacation_illness = 1
                    summary[15] += 1
                elif absence_type == 'IZ':
                    isolation = 1
                    summary[16] += 1
                elif absence_type == 'NN':
                    unexcused_absence = 1
                    summary[17] += 1
                elif absence_type == 'IN':
                    vacation_other = absences.additional_info
                    summary[18] += 1

            if extra_hours:
                extra_hours_value_h = int(extra_hours.quantity)
                extra_hours_value_m = int((extra_hours.quantity % 1) * 60)
                extra_hours_sign = True if extra_hours.full_day else False

                if day.isoweekday() == 7:
                    work_during_sunday_and_holidays += extra_hours.quantity
                    summary[4] += round(float(work_during_sunday_and_holidays), 2)
                    summary[5] += work_during_sunday_and_holidays
                elif day.isoweekday() == 6:
                    work_during_saturdays_and_free_days += extra_hours.quantity
                    summary[4] += round(float(work_during_saturdays_and_free_days), 2)
                    summary[6] += work_during_saturdays_and_free_days
                else:
                    extra_hours_value_to_add += extra_hours.quantity if extra_hours_sign else 0

            day_info.append(d)
            day_info.append(get_weekday_name(day.weekday()))
            # work start hour
            day_start = day + datetime.timedelta(hours=7)
            if delay:
                day_start += datetime.timedelta(minutes=delay)
            start_hour = f'{day_start.hour}' if day_start.hour >= 10 else f'0{day_start.hour}'
            start_minute = f'{day_start.minute}' if day_start.minute >= 10 else f'0{day_start.minute}'
            day_start_str = f'{start_hour}:{start_minute}'
            # day_info.append(day_start_str) if day.date() >= worker.job_start else day_info.append('')
            if day.date() >= worker.job_start:
                if worker.job_end:
                    if day.date() <= worker.job_end:
                        day_info.append(day_start_str)
                    else:
                        day_info.append('')
                else:
                    day_info.append(day_start_str)
            else:
                day_info.append('')

            # work end hour
            day_end = day + datetime.timedelta(hours=15)
            if extra_hours:
                if day_info[1] not in ('So', 'Nd'):
                    if extra_hours_sign:
                        day_end += datetime.timedelta(hours=extra_hours_value_h)
                        day_end += datetime.timedelta(minutes=extra_hours_value_m)
                    else:
                        day_end -= datetime.timedelta(hours=8 - extra_hours_value_h)
                        day_end -= datetime.timedelta(minutes=extra_hours_value_m)
                else:
                    day_end = day_start + datetime.timedelta(hours=extra_hours_value_h)
                    day_end += datetime.timedelta(minutes=extra_hours_value_m)

            end_hour = f'{day_end.hour}' if day_end.hour >= 10 else f'0{day_end.hour}'
            end_minute = f'{day_end.minute}' if day_end.minute >= 10 else f'0{day_end.minute}'
            day_end_str = f'{end_hour}:{end_minute}'
            # day_info.append(day_end_str) if day.date() >= worker.job_start else day_info.append('')
            if day.date() >= worker.job_start:
                if worker.job_end:
                    if day.date() <= worker.job_end:
                        day_info.append(day_end_str)
                    else:
                        day_info.append('')
                else:
                    day_info.append(day_end_str)
            else:
                day_info.append('')

            if day.date() >= worker.job_start:

                job_end = False

                if worker.job_end:
                    if day.date() > worker.job_end:
                        job_end = True

                if not job_end:
                    # hours at work
                    hours_at_work = f'{day_end - day_start}'
                    divided_time = hours_at_work.split(':')
                    hours_at_work = round(float(divided_time[0]) + float(divided_time[1]) / 60, 2)
                    day_info.append(hours_at_work)
                    if not holiday:
                        if day_info[1] not in ('So', 'Nd'):
                            if not absences:
                                summary[4] += hours_at_work
                            else:
                                if absence_type == 'SP' or absence_type == 'D':
                                    summary[4] += hours_at_work
                else:
                    day_info.append('')

            else:
                day_info.append('')

            # sundays and holidays
            day_info.append('') if not work_during_sunday_and_holidays else day_info.append(
                work_during_sunday_and_holidays)

            # extra free days
            day_info.append('') if not work_during_saturdays_and_free_days else day_info.append(
                work_during_saturdays_and_free_days)

            # night time work
            day_info.append('')

            # extra_time_work
            day_info.append('') if not extra_hours_value_to_add else day_info.append(extra_hours_value_to_add)
            summary[8] += extra_hours_value_to_add

            # vacation_day
            day_info.append(vacation_day) if vacation_day else day_info.append('')
            if vacation_day:
                clear_some_data(day_info, [2, 3, 4])

            # vacation_day_on_demand
            day_info.append(vacation_day_on_demand) if vacation_day_on_demand else day_info.append('')
            if vacation_day_on_demand:
                clear_some_data(day_info, [2, 3, 4])

            # vacation quarantine
            day_info.append(vacation_day_quarantine) if vacation_day_quarantine else day_info.append('')
            if vacation_day_quarantine:
                clear_some_data(day_info, [2, 3, 4])

            # vacation special
            day_info.append(vacation_special) if vacation_special else day_info.append('')
            if vacation_special:
                clear_some_data(day_info, [2, 3, 4])

            # free vacation
            day_info.append(vacation_free) if vacation_free else day_info.append('')
            if vacation_free:
                clear_some_data(day_info, [2, 3, 4])

            # home care
            day_info.append(vacation_care) if vacation_care else day_info.append('')
            if vacation_care:
                clear_some_data(day_info, [2, 3, 4])

            # illness
            day_info.append(vacation_illness) if vacation_illness else day_info.append('')
            if vacation_illness:
                clear_some_data(day_info, [2, 3, 4])

            # isolation
            day_info.append(isolation) if isolation else day_info.append('')
            if isolation:
                clear_some_data(day_info, [2, 3, 4])

            # unexcused absence
            day_info.append(unexcused_absence) if unexcused_absence else day_info.append('')
            if unexcused_absence:
                clear_some_data(day_info, [2, 3, 4])

            # other
            day_info.append(vacation_other) if vacation_other else day_info.append('')
            if vacation_other:
                clear_some_data(day_info, [2, 3, 4])

            # any absence
            day_info.append('white')
            if any((vacation_day, vacation_special, vacation_free, vacation_care, vacation_illness, vacation_other,
                    vacation_day_quarantine, unexcused_absence, isolation, vacation_day_on_demand)):
                clear_some_data(day_info, [2, 3, 4])
                day_info[19] = '#E9967A'

            if day_info[1] in ('So', 'Nd') or holiday:
                if not extra_hours:
                    clear_some_data(day_info, [2, 3, 4])
                else:
                    pass
                if any((vacation_day, vacation_special, vacation_free, vacation_care, vacation_illness, vacation_other,
                        vacation_day_quarantine, unexcused_absence, isolation, vacation_day_on_demand)):
                    clear_some_data(day_info, [2, 3, 4])
                    day_info[19] = '#E9967A'
                else:
                    day_info[19] = '#FFEB97'

            days_data_expanded.append(day_info)

        summary[4] = round(summary[4], 2)

        logo_url = os.environ['PAKER_MAIN'] + 'static/images/paker-logo.png'
        font_url = os.environ['PAKER_MAIN'] + 'static/fonts/roboto/'

        template_path = 'whm/worker-timetable.html'
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
        # if error
        if pisa_status.err:
            return HttpResponse('We had some errors <pre>' + html + '</pre>')
        return response


class MonthlyCardPresenceAll(LoginRequiredMixin, View):
    login_url = reverse_lazy('login')

    def get(self, request, year, month):

        def get_weekday_name(day_num):
            names = ('Pn', 'Wt', 'Śr', 'Cz', 'Pt', 'So', 'Nd')
            return names[day_num]

        def clear_some_data(some_list, list_of_indexes):
            for num in list_of_indexes:
                some_list[num] = ''

        workers = Person.active_workers_at_month(int(year), int(month))

        if request.GET.get('uop') == 'yes':
            contracts = Contract.contracts_during_the_month(month, year, 'UOP')
            workers = []
            for c in contracts:
                if c.worker not in workers:
                    workers.append(c.worker)
        if request.GET.get('uz') == 'yes':
            contracts = Contract.contracts_during_the_month(month, year, 'UZ')
            workers = []
            for c in contracts:
                if c.worker not in workers:
                    workers.append(c.worker)
        if request.GET.get('fz') == 'yes':
            contracts = Contract.contracts_during_the_month(month, year, 'FZ')
            workers = []
            for c in contracts:
                if c.worker not in workers:
                    workers.append(c.worker)

        # Create a Django response object, and specify content_type as pdf
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'filename="{year}-{month} timetable.pdf"'
        logo_url = os.environ['PAKER_MAIN'] + 'static/images/paker-logo.png'
        font_url = os.environ['PAKER_MAIN'] + 'static/fonts/roboto/'

        html = None

        date_from = datetime.datetime.strptime(f"{request.GET.get('from')} 00:00:00",
                                               '%Y-%m-%d %H:%M:%S') if request.GET.get('from') else None
        date_to = datetime.datetime.strptime(f"{request.GET.get('to')} 23:59:59",
                                             '%Y-%m-%d %H:%M:%S') if request.GET.get('to') else None

        now = datetime.datetime.now()

        month = int(month)

        if month == 2:
            days = 28 if year % 4 != 0 else 29
        elif month in (4, 6, 9, 11):
            days = 30
        else:
            days = 31

        date_start = datetime.datetime.strptime(f'{year}-{month}-01', '%Y-%m-%d').date()
        date_end = datetime.datetime.strptime(f'{year}-{month}-{days}', '%Y-%m-%d').date()

        for worker in workers:
            summary = [0 for _ in range(19)]

            summary = [0 for _ in range(19)]

            data = []

            days_data = [d for d in range(1, days + 1)]

            days_data_expanded = []

            for d in days_data:
                day = datetime.datetime.strptime(f'{year}-{month}-{d}', '%Y-%m-%d')
                day_info = []

                absence_type = None
                delay = None

                extra_hours = None
                extra_hours_value_h = None
                extra_hours_value_m = None
                extra_hours_sign = None

                vacation_day = None
                vacation_day_on_demand = None
                vacation_day_quarantine = None
                vacation_special = None
                vacation_free = None
                vacation_care = None
                vacation_illness = None
                vacation_other = None

                isolation = None
                unexcused_absence = None

                work_during_sunday_and_holidays = 0
                work_during_saturdays_and_free_days = 0
                extra_hours_value_to_add = 0

                try:
                    holiday = Holiday.objects.get(holiday_date=day)
                except ObjectDoesNotExist:
                    holiday = None

                try:
                    absences = Absence.objects.get(worker=worker, absence_date=day)
                except ObjectDoesNotExist:
                    absences = None

                try:
                    extra_hours = ExtraHour.objects.get(worker=worker, extras_date=day)
                except ObjectDoesNotExist:
                    extra_hours = None

                if absences:
                    absence_type = absences.absence_type
                    if absence_type == 'SP':
                        delay = absences.value
                    elif absence_type == 'UW':
                        vacation_day = 1
                        summary[9] += 1
                    elif absence_type == 'UŻ':
                        vacation_day_on_demand = 1
                        summary[10] += 1
                    elif absence_type == 'KW':
                        vacation_day_quarantine = 1
                        summary[11] += 1
                    elif absence_type == 'UO':
                        vacation_special = 1
                        summary[12] += 1
                    elif absence_type == 'UB':
                        vacation_free = 1
                        summary[13] += 1
                    elif absence_type == 'OP':
                        vacation_care = 1
                        summary[14] += 1
                    elif absence_type == 'CH':
                        vacation_illness = 1
                        summary[15] += 1
                    elif absence_type == 'IZ':
                        isolation = 1
                        summary[16] += 1
                    elif absence_type == 'NN':
                        unexcused_absence = 1
                        summary[17] += 1
                    elif absence_type == 'IN':
                        vacation_other = absences.additional_info
                        summary[18] += 1

                if extra_hours:
                    extra_hours_value_h = int(extra_hours.quantity)
                    extra_hours_value_m = int((extra_hours.quantity % 1) * 60)
                    extra_hours_sign = True if extra_hours.full_day else False

                    if day.isoweekday() == 7:
                        work_during_sunday_and_holidays += extra_hours.quantity
                        summary[4] += round(float(work_during_sunday_and_holidays), 2)
                        summary[5] += work_during_sunday_and_holidays
                    elif day.isoweekday() == 6:
                        work_during_saturdays_and_free_days += extra_hours.quantity
                        summary[4] += round(float(work_during_saturdays_and_free_days), 2)
                        summary[6] += work_during_saturdays_and_free_days
                    else:
                        extra_hours_value_to_add += extra_hours.quantity if extra_hours_sign else 0

                day_info.append(d)
                day_info.append(get_weekday_name(day.weekday()))
                # work start hour
                day_start = day + datetime.timedelta(hours=7)
                if delay:
                    day_start += datetime.timedelta(minutes=delay)
                start_hour = f'{day_start.hour}' if day_start.hour >= 10 else f'0{day_start.hour}'
                start_minute = f'{day_start.minute}' if day_start.minute >= 10 else f'0{day_start.minute}'
                day_start_str = f'{start_hour}:{start_minute}'
                # day_info.append(day_start_str) if day.date() >= worker.job_start else day_info.append('')
                if day.date() >= worker.job_start:
                    if worker.job_end:
                        if day.date() <= worker.job_end:
                            day_info.append(day_start_str)
                        else:
                            day_info.append('')
                    else:
                        day_info.append(day_start_str)
                else:
                    day_info.append('')

                # work end hour
                day_end = day + datetime.timedelta(hours=15)
                if extra_hours:
                    print(extra_hours_value_h, extra_hours_value_m)
                    if day_info[1] not in ('So', 'Nd'):
                        if extra_hours_sign:
                            day_end += datetime.timedelta(hours=extra_hours_value_h)
                            day_end += datetime.timedelta(minutes=extra_hours_value_m)
                        else:
                            day_end -= datetime.timedelta(hours=8 - extra_hours_value_h)
                            day_end += datetime.timedelta(minutes=extra_hours_value_m)
                    else:
                        day_end = day_start + datetime.timedelta(hours=extra_hours_value_h)
                        day_end += datetime.timedelta(minutes=extra_hours_value_m)

                end_hour = f'{day_end.hour}' if day_end.hour >= 10 else f'0{day_end.hour}'
                end_minute = f'{day_end.minute}' if day_end.minute >= 10 else f'0{day_end.minute}'
                day_end_str = f'{end_hour}:{end_minute}'
                # day_info.append(day_end_str) if day.date() >= worker.job_start else day_info.append('')
                if day.date() >= worker.job_start:
                    if worker.job_end:
                        if day.date() <= worker.job_end:
                            day_info.append(day_end_str)
                        else:
                            day_info.append('')
                    else:
                        day_info.append(day_end_str)
                else:
                    day_info.append('')

                if day.date() >= worker.job_start:

                    job_end = False

                    if worker.job_end:
                        if day.date() > worker.job_end:
                            job_end = True

                    if not job_end:
                        # hours at work
                        hours_at_work = f'{day_end - day_start}'
                        divided_time = hours_at_work.split(':')
                        hours_at_work = round(float(divided_time[0]) + float(divided_time[1]) / 60, 2)
                        day_info.append(hours_at_work)
                        if not holiday:
                            if day_info[1] not in ('So', 'Nd'):
                                if not absences:
                                    summary[4] += hours_at_work
                                else:
                                    if absence_type == 'SP' or absence_type == 'D':
                                        summary[4] += hours_at_work
                    else:
                        day_info.append('')

                else:
                    day_info.append('')

                # sundays and holidays
                day_info.append('') if not work_during_sunday_and_holidays else day_info.append(
                    work_during_sunday_and_holidays)

                # extra free days
                day_info.append('') if not work_during_saturdays_and_free_days else day_info.append(
                    work_during_saturdays_and_free_days)

                # night time work
                day_info.append('')

                # extra_time_work
                day_info.append('') if not extra_hours_value_to_add else day_info.append(extra_hours_value_to_add)
                summary[8] += extra_hours_value_to_add

                # vacation_day
                day_info.append(vacation_day) if vacation_day else day_info.append('')
                if vacation_day:
                    clear_some_data(day_info, [2, 3, 4])

                # vacation_day_on_demand
                day_info.append(vacation_day_on_demand) if vacation_day_on_demand else day_info.append('')
                if vacation_day_on_demand:
                    clear_some_data(day_info, [2, 3, 4])

                # vacation quarantine
                day_info.append(vacation_day_quarantine) if vacation_day_quarantine else day_info.append('')
                if vacation_day_quarantine:
                    clear_some_data(day_info, [2, 3, 4])

                # vacation special
                day_info.append(vacation_special) if vacation_special else day_info.append('')
                if vacation_special:
                    clear_some_data(day_info, [2, 3, 4])

                # free vacation
                day_info.append(vacation_free) if vacation_free else day_info.append('')
                if vacation_free:
                    clear_some_data(day_info, [2, 3, 4])

                # home care
                day_info.append(vacation_care) if vacation_care else day_info.append('')
                if vacation_care:
                    clear_some_data(day_info, [2, 3, 4])

                # illness
                day_info.append(vacation_illness) if vacation_illness else day_info.append('')
                if vacation_illness:
                    clear_some_data(day_info, [2, 3, 4])

                # isolation
                day_info.append(isolation) if isolation else day_info.append('')
                if isolation:
                    clear_some_data(day_info, [2, 3, 4])

                # unexcused absence
                day_info.append(unexcused_absence) if unexcused_absence else day_info.append('')
                if unexcused_absence:
                    clear_some_data(day_info, [2, 3, 4])

                # other
                day_info.append(vacation_other) if vacation_other else day_info.append('')
                if vacation_other:
                    clear_some_data(day_info, [2, 3, 4])

                # any absence
                day_info.append('white')
                if any((vacation_day, vacation_special, vacation_free, vacation_care, vacation_illness, vacation_other,
                        vacation_day_quarantine, unexcused_absence, isolation, vacation_day_on_demand)):
                    clear_some_data(day_info, [2, 3, 4])
                    day_info[19] = '#E9967A'

                if day_info[1] in ('So', 'Nd') or holiday:
                    if not extra_hours:
                        clear_some_data(day_info, [2, 3, 4])
                    else:
                        pass
                    if any((vacation_day, vacation_special, vacation_free, vacation_care, vacation_illness,
                            vacation_other,
                            vacation_day_quarantine, unexcused_absence, isolation, vacation_day_on_demand)):
                        clear_some_data(day_info, [2, 3, 4])
                        day_info[19] = '#E9967A'
                    else:
                        day_info[19] = '#FFEB97'

                days_data_expanded.append(day_info)

            summary[4] = round(summary[4], 2)

            template_path = 'whm/workers-timetable.html'
            context = locals()
            # find the template and render it.
            template = get_template(template_path)
            if not html:
                html = template.render(context)
            else:
                html = html + template.render(context)

        # create a pdf
        pisa_status = pisa.CreatePDF(
            html, dest=response, encoding='UTF-8')
        # if error
        if pisa_status.err:
            return HttpResponse('We had some errors <pre>' + html + '</pre>')
        return response


class WorkRemindersView(LoginRequiredMixin, View):
    login_url = reverse_lazy('login')

    def get(self, request):
        if request.GET.get('all') == '+':
            reminders = WorkReminder.objects.all()
        else:
            reminders = WorkReminder.objects.filter(active=True)

        return render(request, 'whm/workreminders.html', locals())


class WorkReminderAdd(LoginRequiredMixin, View):
    login_url = reverse_lazy('login')

    def get(self, request):
        form = WorkReminderForm()
        return render(request, 'whm/workreminder-add.html', locals())

    def post(self, request):
        form = WorkReminderForm(request.POST)

        if form.is_valid():
            new_reminder = WorkReminder(**form.cleaned_data)
            new_reminder.save()
            return redirect('workreminders')

        else:
            pass


class GluerNumberView(LoginRequiredMixin, View):
    login_url = reverse_lazy('login')

    def get(self, request):
        gluer_numbers = GluerNumber.objects.all().order_by('number')
        return render(request, 'whm/gluernumbers.html', locals())


class GluerNumberGet(View):
    def get(self, request):
        dimensions = request.GET.get('dimensions')
        customer = request.GET.get('customer')
        try:
            gluer_number = GluerNumber.objects.get(dimensions=dimensions, customer=Buyer.objects.get(name=customer))
            data = {
                'number': gluer_number.number,
                'comments': gluer_number.comments
            }
            return JsonResponse(data)
        except Exception as e:
            pass


class PolymerNumberGet(View):
    def get(self, request):
        name = request.GET.get('name')
        dimensions = request.GET.get('dimensions')
        customer = request.GET.get('customer')
        try:
            if customer:
                try:
                    customer = Buyer.objects.get(name=customer)
                except Exception:
                    customer = None
            if name and dimensions and customer:
                polymers = Photopolymer.objects.filter(name=name, dimensions=dimensions, customer=customer)
            elif name and dimensions:
                polymers = Photopolymer.objects.filter(name=name, dimensions=dimensions)
            elif name and customer:
                polymers = Photopolymer.objects.filter(name=name, customer=customer)
            elif customer and dimensions:
                polymers = Photopolymer.objects.filter(dimensions=dimensions, customer=customer)
            elif name:
                polymers = Photopolymer.objects.filter(name=name)
            elif dimensions:
                polymers = Photopolymer.objects.filter(dimensions=dimensions)
            elif customer:
                polymers = Photopolymer.objects.filter(customer=customer)
            else:
                polymers = None
            if polymers:
                colors = ''
                numbers = ''
                for p in polymers:
                    letter = '' if not p.identification_letter else p.identification_letter
                    numbers += f'{p.identification_number}{letter}' + ', '
                    for c in p.colors.all():
                        colors += c.number + ', '
                numbers = numbers[:-2]
                colors = colors[:-2]
                data = {
                    'number': numbers,
                    'colors': colors
                }
                data = {
                    'number': numbers,
                    'colors': colors
                }
            else:
                data = {}
            return JsonResponse(data)
        except Exception as e:
            pass


class PunchNumberGet(View):
    def get(self, request):
        name = request.GET.get('name')
        dimensions = request.GET.get('dimensions')

        punches = Punch.objects.filter(name=name)
        punch_data = None

        if punches:
            punch = punches[0]
            punch_data = str(punch.type) + '||'
            if punch.type_letter:
                punch_data += punch.type_letter
            if punch.type_num:
                if float(punch.type_num) % int(punch.type_num) != 0:
                    punch_data += str(punch.type_num)
                else:
                    punch_data += str(int(punch.type_num))

        data = {
            'dimensions': dimensions,
            'name': name,
            'count': len(punches),
            'punch': punch_data
        }
        return JsonResponse(data)


class PrintPolymers(LoginRequiredMixin, View):
    login_url = reverse_lazy('login')

    def get(self, request):
        polymers = Photopolymer.objects.filter(active=True)

        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'filename="polymers.pdf"'
        logo_url = os.environ['PAKER_MAIN'] + 'static/images/paker-logo.png'
        font_url = os.environ['PAKER_MAIN'] + 'static/fonts/roboto/'

        html = None

        now = datetime.datetime.now()

        template_path = 'whm/polymers-all-list.html'
        context = locals()
        template = get_template(template_path)
        if not html:
            html = template.render(context)
        else:
            html = html + template.render(context)

        # create a pdf
        pisa_status = pisa.CreatePDF(
            html, dest=response, encoding='UTF-8')
        # if error
        if pisa_status.err:
            return HttpResponse('We had some errors <pre>' + html + '</pre>')
        return response


class ActiveHours(LoginRequiredMixin, View):
    login_url = reverse_lazy('login')

    def get(self, request):
        d = request.GET.get('d')
        m = request.GET.get('m')
        y = request.GET.get('y')

        first_day = datetime.date(2024, 1, 1)
        if all((y, m, d)):
            d = int(d)
            m = int(m)
            y = int(y)
            first_day = datetime.date(y, m, d)
        day = first_day
        last_day = datetime.date.today() + datetime.timedelta(days=1)

        ld = request.GET.get('ld')
        lm = request.GET.get('lm')
        ly = request.GET.get('ly')

        if all((ly, lm, ld)):
            ld = int(ld)
            lm = int(lm)
            ly = int(ly)
            last_day = datetime.date(ly, lm, ld)

        weeks = []
        months = []
        week = []
        month = []
        months_results = []
        weeks_results = []

        while day != last_day:
            holiday = Holiday.objects.filter(holiday_date=day)
            if not holiday:
                day_data = Person.active_hours_per_day(day)
                if day.isoweekday() <= 5:
                    week.append(day_data)

                else:
                    if week:
                        weeks.append(week)
                        week = []
                if calendar.monthrange(day.year, day.month)[1] != day.day:
                    if day.isoweekday() <= 5:
                        month.append(day_data)
                else:
                    months.append([f'{day.year}.{day.month}'] + [month])
                    month = []
            day += datetime.timedelta(days=1)

        for m in months:
            result = [0 for _ in range(6)]
            for day in m[1]:
                result = [x + y for x, y in zip(result, day)]
            result.append(sum(result))
            result = list(map(int, result))
            months_results.append([m[0]] + result)

        for w in weeks:
            result = [0 for _ in range(6)]
            for day in w:
                result = [x + y for x, y in zip(result, day)]
            result.append(sum(result))
            weeks_results.append(result)

        return render(request, 'whm/active_hours.html', locals())


class WorkersVacationsTest(View):
    def get(self, request):
        result = ''
        workers = Person.objects.all()
        workers_cumulative = {}
        for y in range(2017, datetime.date.today().year + 1):
            result += f'<h1>{y}</h1>'
            for w in workers:
                if w.worker_vacation_in_year(y):
                    if not w.job_end:
                        vacations = 0 if not 'UW' in w.worker_vacations(y).keys() else w.worker_vacations(y)['UW']
                        vacations_on_demand = 0 if not 'UŻ' in w.worker_vacations(y).keys() else w.worker_vacations(y)['UŻ']
                        vacations += vacations_on_demand
                        result += f'<h3>{w} - [{w.worker_vacation_in_year(y) - vacations}] {w.worker_vacation_in_year(y)} - {w.worker_vacations(y)}</h3>'
                        if w in workers_cumulative.keys():
                            workers_cumulative[w] += w.worker_vacation_in_year(y) - vacations
                        else:
                            workers_cumulative[w] = w.worker_vacation_in_year(y) - vacations
            result += '<hr>'

        result += '<hr>'
        workers_data = [(worker, workers_cumulative[worker]) for worker in workers_cumulative.keys()]
        workers_data.sort(key=lambda x:x[0].last_name)

        for data in workers_data:
            result += f'<h2>{data[0]} :: {data[1]}<h2>'


        return HttpResponse(result)


class NoteAdd(PermissionRequiredMixin, View):
    permission_required = 'warehousemanager.add_note'

    def get(self, request):
        note_form = NoteForm()

        return render(request, 'warehousemanager-add-note.html', locals())

    def post(self, request):
        note_form = NoteForm(request.POST)
        if note_form.is_valid():
            genre = note_form.cleaned_data['genre']
            title = note_form.cleaned_data['title']
            content = note_form.cleaned_data['content']
            new_note = Note.objects.create(genre=genre, title=title, content=content)

            new_note.save()

            return redirect('deliveries-calendar')


# wszystkie notatki
class AllNotes(PermissionRequiredMixin, View):
    permission_required = 'warehousemanager.view_note'

    def get(self, request):
        all_notes = Note.objects.all()
        return render(request, 'warehousemanager-all-notes.html', locals())


class NoteDetailsView(PermissionRequiredMixin, View):
    permission_required = 'warehousemanager.view_note'

    def get(self, request, note_id):
        note = Note.objects.get(id=note_id)
        return render(request, 'note-details.html', locals())


class NoteDeleteView(PermissionRequiredMixin, View):
    permission_required = 'warehousemanager.view_note'

    def get(self, request, note_id):
        note = Note.objects.get(id=note_id)
        note.delete()
        return redirect('deliveries-calendar')