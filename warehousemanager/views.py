from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.http import HttpResponse
from django.views import View
from django.contrib import messages
from django.http import FileResponse
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import permission_required
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import Q
from django.core.exceptions import ObjectDoesNotExist
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views.generic.detail import DetailView
from django.views.generic.list import ListView
from django.urls import reverse_lazy
from django.core.mail import send_mail
import io
import os
import sys
import shutil
from django.conf import settings
# import docx
import json
import datetime

from warehousemanager.functions import *

import subprocess
# import models from warehousemanager app
from warehousemanager.models import *
from warehousemanager.forms import *

# exporting content to pdf
from django.template.loader import get_template
from xhtml2pdf import pisa

# coworking with google sheets
from django.contrib.staticfiles import finders
import gspread
from oauth2client.service_account import ServiceAccountCredentials


def index(request):
    return HttpResponse('first view')


def render_pdf_view(request):
    template_path = 'user_printer.html'
    context = {'myvar': 'this is your template context'}
    # Create a Django response object, and specify content_type as pdf
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="report.pdf"'
    # find the template and render it.
    template = get_template(template_path)
    html = template.render(context)

    # create a pdf
    pisa_status = pisa.CreatePDF(
        html, dest=response)
    # if error then show some funy view
    if pisa_status.err:
        return HttpResponse('We had some errors <pre>' + html + '</pre>')
    return response


class NewOrder(PermissionRequiredMixin, View):
    permission_required = 'warehousemanager.view_order'

    def get(self, request):
        providers = CardboardProvider.objects.all()
        form = NewOrderForm()

        # deleting orders without items
        orders = Order.objects.all()
        for order in orders:
            if not OrderItem.objects.all().filter(order=order):
                order.delete()

        not_completed_orders = Order.objects.all()

        for n_c_order in not_completed_orders:
            if not n_c_order.is_completed:
                messages.info(request, 'Masz niezakończone zamówienia')

        return render(request, 'warehousemanager-new-order.html', locals())

    def post(self, request):
        form = NewOrderForm(request.POST)
        if form.is_valid():
            provider = form.cleaned_data['provider']
            order_provider_number = form.cleaned_data['order_provider_number']
            date_of_order = form.cleaned_data['date_of_order']

            provider_object = CardboardProvider.objects.get(name=provider)

            new_order = Order.objects.create(provider=provider_object, order_provider_number=int(order_provider_number),
                                             date_of_order=date_of_order)

            new_order.save()

            orders = Order.objects.all()
            if orders:
                order_id = orders.order_by('id').reverse()[0].id
            else:
                order_id = 1
            return redirect('/add-items/{}'.format(order_id))


class DeleteOrder(PermissionRequiredMixin, View):
    permission_required = 'warehousemanager.delete_order'

    def get(self, request):
        order_id = int(request.GET.get('order_id'))
        Order.objects.get(id=order_id).delete()

        return redirect('uncompleted-orders')


class NewItemAdd(PermissionRequiredMixin, View):
    permission_required = 'warehousemanager.view_orderitem'

    def get(self, request, order_id):
        form = NewOrderItemForm()
        order = Order.objects.get(id=order_id)
        items = OrderItem.objects.all().filter(order=order)
        last_items = OrderItem.objects.all().reverse()[:5]
        all_items = OrderItem.objects.all()

        if order.is_completed:
            return HttpResponse('Zamówienie zostało już skompletowane')

        return render(request, 'add-item.html', locals())

    def post(self, request, order_id):
        form = NewOrderItemForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('/add-items/{}'.format(order_id))
        else:
            return HttpResponse(form.errors)


class OrderItemDelete(PermissionRequiredMixin, View):
    permission_required = 'warehousemanager.view_orderitem'

    def get(self, request, order_id, item_id):
        item_object = OrderItem.objects.get(id=int(item_id))
        item_object.delete()

        return redirect('/add-items/{}'.format(order_id))


class NextOrderNumber(View):
    def get(self, request):
        provider_num = request.GET.get('provider_num')
        provider = CardboardProvider.objects.get(id=int(provider_num))
        all_orders = Order.objects.all().filter(provider=provider).order_by('order_provider_number').reverse()
        if all_orders:
            num = all_orders[0].order_provider_number + 1
        else:
            num = 1

        z = json.dumps(num)

        return HttpResponse(z)


class ProviderForm(PermissionRequiredMixin, View):
    permission_required = 'warehousemanager.view_cardboardprovider'

    def get(self, request):
        form = CardboardProviderForm()
        return render(request, 'new_provider.html', locals())

    def post(self, request):
        form = CardboardProviderForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['name']
            CardboardProvider.objects.create(name=name)

            return redirect('main-page')


class NextItemNumber(View):
    def get(self, request):
        order_num = request.GET.get('order_num')
        order = Order.objects.get(id=int(order_num))
        all_items = OrderItem.objects.all().filter(order=order)

        num = len(all_items)

        return HttpResponse(json.dumps(num + 1))


class CompleteOrder(View):
    def get(self, request):
        order_id = int(request.GET.get('order_id'))
        state = request.GET.get('state')
        order = Order.objects.get(id=order_id)
        order.is_completed = True if state == 'c' else False
        order.save()

        return redirect('all-orders-details')


class GetItemDetails(PermissionRequiredMixin, View):
    permission_required = 'warehousemanager.view_orderitem'

    def get(self, request):
        item_id = int(request.GET.get('item_id'))
        item = OrderItem.objects.get(id=item_id)

        if item.buyer.all():
            buyer = item.buyer.all()[0].name
        else:
            buyer = ''

        data = {
            'height': item.format_height,
            'width': item.format_width,
            'dimension_one': item.dimension_one,
            'dimension_two': item.dimension_two,
            'dimension_three': item.dimension_three,
            'sort': item.sort,
            'buyer': buyer,
            'weight': item.cardboard_weight,
            'cardboard_type': item.cardboard_type,
            'name': item.name,
            'scores': item.scores
        }

        return HttpResponse(json.dumps(data))


class PrintTest(View):
    def get(self, request):
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer)
        p.drawString(100, 100, 'Hello World.')
        p.showPage()
        p.save()
        lpr = subprocess.Popen("/usr/bin/lpr", stdin=subprocess.PIPE)
        lpr.stdin.write(b'ok')
        buffer.seek(0)

        return FileResponse(buffer, as_attachment=True, filename='hello.pdf')


class OpenFile(View):
    def get(self, request, order_item_id):
        order_item = OrderItem.objects.get(id=order_item_id)

        os.chdir('/home/damian/PycharmProjects/PakerProject/media/paker')

        src = 'zp.docx'
        dst = 'zp{}'.format(order_item.id)

        os.rename(src, 'oko.docx')

        '''document = docx.Document('zp{}'.format(order_item.id))
        print(len(document.sections))

        text = ''

        for p in document.paragraphs:
            if p.text == 'TERMIN REALIZACJI':
                p.text = 'nowy termin'
            text += ' $'
            text += '<br />'
            text += p.text

        text += '<br />'
        text += 'Tabele <br />'

        for t in document.tables:
            text2 = ''
            for i, row in enumerate(t.rows):
                for c in row.cells:
                    if c.text == 'TYP MASZYNY':
                        if order_item.sort in ('201', '202', '203'):
                            c.text = 'f. ' + order_item.sort

                    text2 += c.text

            text += text2

        document.save('zp.docx')'''

        return HttpResponse('')


class NewAllOrders(PermissionRequiredMixin, View):
    permission_required = 'warehousemanager.view_order'

    def get(self, request):
        customer = request.GET.get('customer')
        all_customers = Buyer.objects.all()
        orders = Order.objects.all()
        items = OrderItem.objects.all()
        only_uncompleted = False if not request.GET.get('only_u') else True
        provider = request.GET.get('provider')
        if provider:
            orders = orders.filter(provider=CardboardProvider.objects.get(name=provider))
        if customer:
            orders = []
            orders_ = OrderItem.objects.filter(buyer__name=customer)
            for o in orders_:
                if o.order not in orders:
                    orders.append(o.order)
        orders_num = len(orders) if request.GET.get('all-orders') else 10

        paginator = Paginator(orders, orders_num)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        providers = CardboardProvider.objects.all()
        quantities = OrderItemQuantity.objects.all()
        return render(request, 'new-all-orders.html', locals())


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


class LogoutView(View):
    def get(self, request):
        logout(request)

        return redirect('start-page')


class MainPageView(LoginRequiredMixin, View):
    login_url = '/'

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

        return render(request, 'warehousemanager-main-page.html', locals())
        # return redirect('punches')


# wszyscy dostawcy
class AllProvidersView(LoginRequiredMixin, View):
    login_url = '/'

    def get(self, request):
        providers = CardboardProvider.objects.all()
        return render(request, 'warehousemanager-all-providers.html', locals())


# przelicznik formatów
class FormatConverter(LoginRequiredMixin, View):
    login_url = '/'

    def get(self, request):
        return render(request, 'warehousemanager-format-converter.html', locals())


# zarządzanie dostawami
class DeliveriesManagement(LoginRequiredMixin, View):
    login_url = '/'

    def get(self, request):
        title = 'DELIVERIES'
        all_deliveries = Delivery.objects.all()
        return render(request, 'warehousemanager-all-deliveries.html', locals())


# szczegóły dostawy
class DeliveryDetails(LoginRequiredMixin, View):
    login_url = '/'

    def get(self, request, delivery_id):
        delivery = Delivery.objects.get(id=delivery_id)
        quantities = OrderItemQuantity.objects.filter(delivery=delivery)
        palettes = PaletteQuantity.objects.filter(delivery=delivery)

        order_item_q_form = OrderItemQuantityForm(initial={'delivery': delivery}, provider=delivery.provider)
        palette_q_form = PaletteQuantityForm(initial={'delivery': delivery})

        return render(request, 'warehousemanager-delivery-details.html', locals())

    def post(self, request, delivery_id):
        delivery = Delivery.objects.get(id=delivery_id)
        order_item_q_form = OrderItemQuantityForm(delivery.provider, request.POST)
        palette_q_form = PaletteQuantityForm(request.POST)

        if palette_q_form.is_valid():
            delivery = Delivery.objects.get(id=int(request.POST.get('delivery')))
            palette = Palette.objects.get(id=int(request.POST.get('palette')))
            quantity = int(request.POST.get('quantity'))
            status = request.POST.get('status')

            new_palette_quantity = PaletteQuantity.objects.create(delivery=delivery, palette=palette, quantity=quantity,
                                                                  status=status)

            new_palette_quantity.save()

            return redirect('/delivery/{}'.format(delivery_id))

        if order_item_q_form.is_valid():
            delivery = request.POST.get('delivery')
            order_item = request.POST.get('order_item')
            quantity = request.POST.get('quantity')

            new_oiq = OrderItemQuantity.objects.create(delivery=Delivery.objects.get(id=int(delivery)),
                                                       order_item=OrderItem.objects.get(id=int(order_item)),
                                                       quantity=int(quantity))

            new_oiq.save()

            return redirect('/delivery/{}'.format(delivery_id))


# dodawanie dostawy
class DeliveryAdd(PermissionRequiredMixin, View):
    permission_required = 'warehousemanager.view_delivery'

    def get(self, request):
        delivery_form = DeliveryForm()

        return render(request, 'warehousemanager-delivery-add.html', locals())

    def post(self, request):
        delivery_form = DeliveryForm(request.POST)
        if delivery_form.is_valid():
            provider = delivery_form.cleaned_data['provider']
            date_of_delivery = delivery_form.cleaned_data['date_of_delivery']

            new_delivery = Delivery.objects.create(provider=provider, date_of_delivery=date_of_delivery)

            new_delivery.save()

            return redirect('/delivery/{}'.format(new_delivery.id))

        else:
            return HttpResponse('fail')


# dodawanie notatek
class NoteAdd(PermissionRequiredMixin, View):
    permission_required = 'warehousemanager.view_note'

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

            return redirect('notes')


# wszystkie notatki
class AllNotes(PermissionRequiredMixin, View):
    permission_required = 'warehousemanager.view_note'

    def get(self, request):
        all_notes = Note.objects.all()
        return render(request, 'warehousemanager-all-notes.html', locals())


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
            'November',
            'December')

        month = request.GET.get('month')

        if not month:
            month = datetime.date.today()
            aa = today_month()
            month_date = datetime.datetime.today()
            day_num = month_date.day
            prev_month, next_month = previous_and_next_month(datetime.date.strftime(month, '%Y-%m-%d'))
        else:
            aa = month
            month_split = month.split()
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

        workers = Person.objects.all().filter(
            job_start__lte=datetime.date(int(month_year[1]), months.index(month_year[0]) + 1, month_days))
        workers = workers.exclude(job_end__lte=datetime.date(int(month_year[1]), months.index(month_year[0]) + 1, 1))
        '''to_delete = []
        for worker in workers:
            if worker.job_end:
                if worker.job_end < datetime.date(int(month_year[1]), months.index(month_year[0]) + 1, 1):
                    to_delete.append(worker.id)
                    print(worker.first_name, worker.last_name)
        workers.filter(id__in=to_delete).delete()'''
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

        end_list_condition = next_month == f'{months[datetime.date.today().month]} {str(datetime.date.today().year)}'
        end_plus_31 = datetime.datetime.today() + datetime.timedelta(days=31)
        z = month_list('01-01-2017', datetime.datetime.strftime(end_plus_31, '%d-%m-%Y'))

        return render(request, 'warehousemanager-absenceslist.html', locals())


class AbsencesAndHolidays(View):

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
        for h in holiday_objects:
            absences = Absence.objects.all().filter(absence_date=h.holiday_date)
            if len(absences) > 0:
                for a in absences:
                    a.delete()

        workers = Person.objects.all()
        non_work_days = []

        for w in workers:
            r = days_without_work(w, f'{month_}-{year}')
            if len(r[1]) > 0:
                non_work_days.append(r)

        extra_hours = []
        non_full_days = []
        acquaintances = []
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
            if a.absence_type != 'SP':
                absences_and_holidays.append((a.worker.id, a.absence_date.day, a.absence_type, a.id))
            else:
                value = change_minutes_to_hours(a.value) if a.value else 'no value'
                acquaintances.append((a.worker.id, a.absence_date.day, a.absence_type, value))
        for h in holiday_objects:
            absences_and_holidays.append((-1, h.holiday_date.day, h.name))
        return HttpResponse(
            json.dumps((absences_and_holidays, non_work_days, extra_hours, non_full_days, acquaintances)))


class GetLocalVar(View):
    def get(self, request, variable_name):
        if os.environ[variable_name]:
            return HttpResponse(json.dumps(os.environ[variable_name]))
        else:
            return redirect('manage')


class AbsenceEdit(LoginRequiredMixin, View):
    login_url = '/'

    def get(self, request, absence_id):
        absence = Absence.object.get(id=int(absence_id))


# absence-view
class AbsenceAdd(LoginRequiredMixin, View):
    login_url = '/'

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
            print(default_date)
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
                    new_extras.quantity = extras_quantity
                    new_extras.full_day = extras_day
                    new_extras.save()
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

            print(condition_two, condition_one)

            if all((condition_one, condition_two)):

                if len(Absence.objects.filter(worker=worker, absence_date=absence_date)) > 0:
                    new_absence = Absence.objects.filter(worker=worker, absence_date=absence_date)[0]
                    new_absence.absence_type = absence_type
                    new_absence.save()
                else:

                    new_absence = Absence.objects.create(worker=worker, absence_date=absence_date,
                                                         absence_type=absence_type)

                    new_absence.save()

                if absence_type == 'SP':
                    new_absence.create_acquaintance(value=int(short_absence_form.cleaned_data['value']))

            response = redirect('absence-list')
            response['Location'] += f'?month={change_month_num_to_name(absence_date.month)} {absence_date.year}'

            return response

        else:
            worker = request.POST.get('worker')
            first_day = request.POST.get('first_day')
            last_day = request.POST.get('last_day')
            absence_type = request.POST.get('type')

            worker_s = worker.split()
            worker_object = Person.objects.filter(first_name=worker_s[0], last_name=worker_s[1])[0]
            first_day_date = datetime.datetime.strptime(first_day, '%Y-%m-%d')
            last_day_date = datetime.datetime.strptime(last_day, '%Y-%m-%d')

            safety_counter = 0
            while first_day_date != last_day_date:
                if safety_counter < 15:
                    safety_counter += 1
                    if first_day_date.weekday() < 5:
                        new_absence = Absence(worker=worker_object, absence_date=first_day_date,
                                              absence_type=absence_type)
                        new_absence.save()
                    else:
                        if absence_type == 'UZ':
                            new_absence = Absence(worker=worker_object, absence_date=first_day_date,
                                                  absence_type=absence_type)
                            new_absence.save()
                        else:
                            pass
                    first_day_date = first_day_date + datetime.timedelta(days=1)
                    if first_day_date == last_day_date:
                        new_absence = Absence(worker=worker_object, absence_date=first_day_date,
                                              absence_type=absence_type)
                        new_absence.save()
                else:
                    break

            return redirect('absence-list')


# absence-delete
class AbsenceDelete(PermissionRequiredMixin, View):
    permission_required = 'warehousemanager.delete_absence'

    def post(self, request):
        Absence.objects.get(id=int(request.POST.get('absence_id'))).delete()

        return HttpResponse(request.POST.get('absence_id'))


class PunchesList(PermissionRequiredMixin, View):
    permission_required = 'warehousemanager.view_punch'

    def get(self, request):
        user = request.user
        visit_counter(user, 'punches')

        punches = Punch.objects.all().order_by('type', 'type_letter', 'type_num')
        punch_types = PUNCH_TYPES
        title = 'PUNCHES'

        return render(request, 'warehousemanager-punches-list.html', locals())


class PunchAdd(PermissionRequiredMixin, View):
    permission_required = 'warehousemanager.view_punch'

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
    permission_required = 'warehousemanager.view_punch'

    def get(self, request, punch_id):
        p = get_object_or_404(Punch, id=punch_id)
        punch_form = PunchForm(instance=p)
        edit = True

        return render(request, 'warehousemanager-punch-add.html', locals())

    def post(self, request, punch_id):
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
    permission_required = 'warehousemanager.view_buyer'

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


class PunchProductions(PermissionRequiredMixin, View):
    permission_required = 'warehousemanager.view_punchproduction'

    def get(self, request):
        production = PunchProduction.objects.all()

        return render(request, 'warehousemanager-punch-production.html', locals())


class PunchProductionAdd(PermissionRequiredMixin, View):
    permission_required = 'warehousemanager.view_punchproduction'

    def get(self, request):
        punch_id = request.GET.get('punch_id')
        if punch_id:
            punch = Punch.objects.get(id=int(punch_id))
            form = PunchProductionForm(initial={'punch': punch})

        else:
            form = PunchProductionForm()

        return render(request, 'warehousemanager-punch-production-add.html', locals())

    def post(self, request):
        form = PunchProductionForm(request.POST)

        if form.is_valid():
            punch = form.cleaned_data['punch']
            worker = form.cleaned_data['worker']
            date_start = form.cleaned_data['date_start']
            date_end = form.cleaned_data['date_end']
            quantity = form.cleaned_data['quantity']
            comments = form.cleaned_data['comments']

            production = PunchProduction.objects.create(punch=punch, worker=worker, date_start=date_start,
                                                        date_end=date_end, quantity=quantity, comments=comments)
            production.save()

            return redirect('punches')


class CardboardUsed(View):
    def get(self, request, cardboard_stock_id):
        cardboard = OrderItemQuantity.objects.get(id=cardboard_stock_id)
        if cardboard.is_used:
            return HttpResponse(json.dumps(True))
        else:
            return HttpResponse(json.dumps(False))


class StockManagement(PermissionRequiredMixin, View):
    permission_required = 'warehousemanager.view_punchproduction'

    def get(self, request):
        stocks = OrderItemQuantity.objects.filter(is_used=False)
        history_stocks = OrderItemQuantity.objects.filter(is_used=True)

        return render(request, 'warehousemanager-stock-management.html', locals())


class Announcement(View):
    def get(self, request):
        return render(request, 'warehousemanager-announcement.html')


class ChangeOrderState(View):
    def get(self, request):
        order_item_id = request.GET.get('order_item_id')
        order_item = OrderItem.objects.get(id=int(order_item_id))
        if order_item.is_completed:
            order_item.is_completed = False
        else:
            order_item.is_completed = True

        order_item.save()

        return HttpResponse(json.dumps(order_item.is_completed))


class ProductionView(View):
    def get(self, request):
        items_to_do = OrderItem.objects.filter(is_completed=True)
        return render(request, 'warehousemanager-production-status.html', locals())


class OrderItemDetails(View):
    def get(self, request, order_item_id):
        order_item = OrderItem.objects.get(id=order_item_id)
        productions = ProductionProcess.objects.filter(order_item=order_item)
        quantity_delivered = 0
        for oiq in OrderItemQuantity.objects.filter(order_item=order_item):
            quantity_delivered += oiq.quantity
        return render(request, 'warehousemanager-order-item-details.html', locals())


# printing tests
class OrderItemPrint(View):
    def get(self, request, order_item_id):
        order_item = OrderItem.objects.get(id=order_item_id)
        productions = ProductionProcess.objects.filter(order_item=order_item)

        productions_cutting = productions.filter(Q(type='WY') | Q(type='WY+DR') | Q(type='DR') | Q(type='SZ'))

        quantity_delivered = 0

        for oiq in OrderItemQuantity.objects.filter(order_item=order_item):
            quantity_delivered += oiq.quantity

        logo_url = os.environ['PAKER_MAIN'] + 'static/images/paker-logo.png'

        delta_date = order_item.order.date_of_order + datetime.timedelta(days=14)

        date_end = delta_date.strftime('%d.%m.%Y')

        now = datetime.date.today().strftime('%d.%m.%Y')

        buyer_list = order_item.buyer.all()

        buyer = ''

        for b in buyer_list:
            if buyer != '':
                buyer += ', '
            buyer += str(b)

        machine = ''

        if order_item.sort in ('201', '202', '203'):
            machine = 'SLO'
        elif order_item.sort == 'SZTANCA':
            machine = 'TYG'
        elif order_item.sort == 'PRZEKLADKA':
            machine = 'MAG'
            if order_item.dimension_one != order_item.format_width:
                machine = 'KRA'
            elif order_item.dimension_two != order_item.format_height:
                machine = 'KRA'

        punch_id = '.'

        if order_item.sort == 'SZTANCA':
            punches = Punch.objects.filter(dimension_one=order_item.dimension_one).filter(
                dimension_two=order_item.dimension_two).filter(dimension_three=order_item.dimension_three)
            if punches.count() > 0:
                punch_id = ''
                for p in punches:
                    if punch_id != '':
                        punch_id += ', '
                    punch_id += p.punch_name()

        # return render(request, 'warehousemanager-printtest.html', locals())

        template_path = 'warehousemanager-printtest.html'
        context = locals()
        # Create a Django response object, and specify content_type as pdf
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'filename="report.pdf"'
        # find the template and render it.
        template = get_template(template_path)
        html = template.render(context)

        # create a pdf
        pisa_status = pisa.CreatePDF(
            html, dest=response)
        # if error then show some funy view
        if pisa_status.err:
            return HttpResponse('We had some errors <pre>' + html + '</pre>')
        return response


# connecting with google sheets
class GoogleSheetTest(View):
    def get(self, request):
        order_item_id = request.GET.get('orderitemid')

        order_item = OrderItem.objects.get(id=int(order_item_id))

        delta_date = order_item.order.date_of_order + datetime.timedelta(days=14)

        date_end = delta_date.strftime('%d.%m.%Y')

        now = datetime.date.today().strftime('%d.%m.%Y')

        scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']

        creds_dict = {
            "type": "service_account",
            "project_id": os.environ['PROJECT_ID'],
            "private_key_id": os.environ['PRIVATE_KEY_ID'],
            "private_key": google_key(),
            "client_email": os.environ['CLIENT_EMAIL'],
            "client_id": os.environ['CLIENT_ID'],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": os.environ['CLIENT_CERT_URL']
        }

        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)

        client = gspread.authorize(creds)

        sheet_zam = client.open('zlecenie produkcyjne')

        sheet = sheet_zam.sheet1

        all_sheets = SpreadsheetCopy.objects.all()

        for s in all_sheets:
            if timezone.now() > s.created + datetime.timedelta(minutes=30):
                client.del_spreadsheet(s.gs_id)
                s.delete()

        new_title = f'{order_item}'

        new_gs = client.copy(file_id='1II0BeYj-FuJtWFSkU8mUmU6lMRPqXvWTQw-DXqfzmio', title=new_title,
                             copy_permissions=True)

        SpreadsheetCopy.objects.create(gs_id=new_gs.id)

        sheet.update_cell(18, 21, order_item.ordered_quantity)

        sheet.update_cell(12, 16, date_end)

        sheet.update_cell(15, 9, now)

        if order_item.name:
            sheet.update_cell(12, 28, order_item.name)
        else:
            sheet.update_cell(12, 28, '')

        sheet.update_cell(18, 16,
                          f'{order_item.cardboard_type}{order_item.cardboard_weight}{order_item.cardboard_additional_info}')

        buyer_list = order_item.buyer.all()

        buyer = ''

        for b in buyer_list:
            if buyer != '':
                buyer += ', '
            buyer += str(b.shortcut)

        machine = ''

        if order_item.sort in ('201', '202', '203'):
            machine = 'SLO'
        elif order_item.sort == 'SZTANCA':
            machine = 'TYG'
        elif order_item.sort == 'PRZEKLADKA':
            machine = 'MAG'
            if order_item.dimension_one != order_item.format_width:
                machine = 'KRA'
            elif order_item.dimension_two != order_item.format_height:
                machine = 'KRA'

        punch_id = ''

        if order_item.sort == 'SZTANCA':
            punches = Punch.objects.filter(dimension_one=order_item.dimension_one).filter(
                dimension_two=order_item.dimension_two).filter(dimension_three=order_item.dimension_three)
            if punches.count() > 0:
                punch_id = ''
                for p in punches:
                    if punch_id != '':
                        punch_id += ', '
                    punch_id += p.punch_name()

        sheet.update_cell(12, 21, machine)

        sheet.update_cell(20, 6, punch_id)

        sheet.update_cell(18, 24, f'{order_item.format_width}x{order_item.format_height}')

        sheet.update_cell(17, 1, order_item.dimension_one)

        sheet.update_cell(17, 6, order_item.dimension_two)

        if order_item.dimension_three:
            sheet.update_cell(17, 11, order_item.dimension_three)
        else:
            sheet.update_cell(17, 11, '')

        provider_lower = str(order_item.order.provider).lower()

        if provider_lower == 'convert':
            prov_shortcut = 'CN'
        elif provider_lower == 'aquila':
            prov_shortcut = 'AQ'
        elif provider_lower == 'werner':
            prov_shortcut = 'WER'
        else:
            prov_shortcut = 'NN'

        sheet.update_cell(6, 11,
                          f'{prov_shortcut} {order_item.order.order_provider_number}/{order_item.item_number} {buyer}')

        return redirect(
            'https://docs.google.com/spreadsheets/d/1VLDQa9HAdvWeHqX6QEpsTUPpyJz5fDcS4x2qTTjkEWA/edit#gid=1727884471')


class ImportOrderItems(View):

    def get(self, request):

        if request.GET.get('record') or request.GET.get('final_record'):
            val_1 = int(request.GET.get('record')) if request.GET.get('record') else None
            val_2 = int(request.GET.get('final_record')) if request.GET.get('final_record') else None

            if val_2 and val_1 and (val_2 < val_1):
                statement = 'Value LAST ROW cannot be lower than FIRST ROW '
                return render(request, 'warehousemanager-import-records.html', locals())

            if not val_1:
                val_1 = 4

            # connecting to spreadsheet
            scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']

            creds_dict = {
                "type": "service_account",
                "project_id": os.environ['PROJECT_ID'],
                "private_key_id": os.environ['PRIVATE_KEY_ID'],
                "private_key": google_key(),
                "client_email": os.environ['CLIENT_EMAIL'],
                "client_id": os.environ['CLIENT_ID'],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_x509_cert_url": os.environ['CLIENT_CERT_URL']
            }

            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)

            client = gspread.authorize(creds)

            sheet = client.open('tz2021').sheet1

            if not val_2:
                val_2 = len(sheet.get_all_values())

            if val_2 - val_1 > 15:
                if request.GET.get('record') and request.GET.get('final_record'):
                    statement = 'Max 15 records during one request'
                elif request.GET.get('record') and not request.GET.get('_final_record'):
                    statement = f'Max 15 records during one request(there is {len(sheet.get_all_values())} records in sheet)'
                return render(request, 'warehousemanager-import-records.html', locals())

            record = 4 if not request.GET.get('record') else int(request.GET.get('record'))

            final_record = len(sheet.get_all_values()) + 1 if not request.GET.get('final_record') else int(
                request.GET.get('final_record'))

            new_rows = []

            result = []

            # collecting data

            for x in range(record, final_record):
                new_rows.append((sheet.row_values(x), x))

            for row, row_num in new_rows:
                break_condition = False
                provider_object = None

                # provider
                provider_shortcut = row[0]
                if provider_shortcut == 'AQ':
                    provider = 'AQUILA'
                elif provider_shortcut == 'CV' or provider_shortcut == 'CN':
                    provider = 'CONVERT'
                elif provider_shortcut == 'WER':
                    provider = 'WERNER'
                else:
                    provider = 'OTHER'

                try:
                    provider_object = CardboardProvider.objects.get(name=provider)
                except ObjectDoesNotExist:
                    result.append('!# PROVIDER DOES NOT EXISTS !!! ERROR ###')
                    break_condition = True

                if not break_condition:
                    break_condition2 = False
                    order_num = None

                    # collecting data from rows

                    try:
                        order_num = int(row[1])
                    except ValueError:
                        result.append(f'VALUE ERROR IN ROW: {row_num}(WRONG ORDER NUMBER)')
                        break_condition2 = True

                    try:
                        order_item_num = int(row[2])
                    except ValueError:
                        result.append(f'VALUE ERROR IN ROW: {row_num}(WRONG ORDER ITEM NUMBER)')
                        break_condition2 = True

                    try:
                        width = int(row[8])
                    except ValueError:
                        result.append(f'VALUE ERROR IN ROW: {row_num}(WRONG FORMAT WIDTH)')
                        break_condition2 = True

                    try:
                        height = int(row[9])
                    except ValueError:
                        result.append(f'VALUE ERROR IN ROW: {row_num}(WRONG FORMAT HEIGHT)')
                        break_condition2 = True

                    # sort
                    sheet_value = row[6]
                    if sheet_value in ('ROT F201', 'SLO F201'):
                        sort = '201'
                    elif sheet_value in ('ROT F200', 'SLO F200'):
                        sort = '200'
                    elif sheet_value in ('ROT F203', 'SLO F203'):
                        sort = '203'
                    elif sheet_value in ('SLO 301 WIEKO', 'SLO 301 DNO'):
                        sort = '301'
                    elif sheet_value in ('ROT F409', 'SLO F409'):
                        sort = '409'
                    elif sheet_value == 'TYGIEL':
                        sort = 'SZTANCA'
                    elif sheet_value == 'ROT/TYG':
                        sort = 'ROT/TYG'
                    elif sheet_value == 'MAG':
                        sort = 'MAG'
                    elif sheet_value == 'KRA':
                        sort = 'PRZEKLADKA'
                    else:
                        sort = 'PRZEKLADKA'

                    # quantity handling

                    try:
                        quantity_cell = row[10]
                        if quantity_cell == '':
                            quantity_cell = 0
                        quantity = int(quantity_cell)
                    except ValueError:
                        result.append(f'VALUE ERROR IN ROW: {row_num}(WRONG QUANTITY)')
                        break_condition2 = True

                    # order_dimensions
                    dimensions = ''
                    dim1 = 0
                    dim2 = 0
                    dim3 = 0
                    name = ''
                    try:
                        dimensions = row[18]

                    except IndexError:
                        result.append(f'VALUE ERROR IN ROW: {row_num}(NO DIMENSIONS)')
                        break_condition2 = True

                    dimensions_split = dimensions.split('x')

                    if len(dimensions_split) == 0:
                        result.append(f'NO DIMENSIONS ERROR IN ROW: {row_num}')
                    elif len(dimensions_split) == 1:
                        try:
                            if dimensions_split[0] != '':
                                punch = Punch.objects.get(name=dimensions_split[0])
                                dim1 = punch.dimension_one
                                dim2 = punch.dimension_two
                                dim3 = punch.dimension_three
                                name = punch.name
                            else:
                                result.append(f'NO DIMENSIONS ERROR IN ROW: {row_num}')
                        except ObjectDoesNotExist:
                            name = dimensions_split[0]
                            result.append(f'DIMENSIONS ERROR {dimensions_split[0]}')
                    elif len(dimensions_split) == 2:
                        dim1 = dimensions_split[0]
                        dim2 = dimensions_split[1].split()[0]
                    else:
                        dim1 = dimensions_split[0]
                        dim2 = dimensions_split[1]
                        dim3 = dimensions_split[2].split()[0]

                    try:
                        name = row[19]
                    except IndexError:
                        name = ''

                    try:
                        dim1 = int(dim1) if dim1 else 0
                    except ValueError:
                        result.append(f'VALUE ERROR IN ROW: {row_num}(WRONG FIRST DIMENSION)')
                        break_condition2 = True

                    try:
                        dim2 = int(dim2) if dim2 else 0
                    except ValueError:
                        result.append(f'VALUE ERROR IN ROW: {row_num}(WRONG SECOND DIMENSION)')
                        break_condition2 = True

                    try:
                        if dim3 != '':
                            dim3 = int(dim3) if dim3 else None
                        else:
                            dim3 = None
                    except ValueError:
                        result.append(f'VALUE ERROR IN ROW: {row_num}(WRONG THIRD DIMENSION)')
                        break_condition2 = True

                    # scores
                    scores = row[13]
                    if scores == '':
                        scores = '-'

                    # cardboard
                    cardboard_type = row[15]
                    if len(cardboard_type) > 6:
                        cardboard_type = 'BB'
                    cardboard_weight = row[16]
                    if cardboard_weight == '':
                        cardboard_weight = 0
                    cardboard_extra = row[17]

                    # customer
                    customer = row[14]
                    customer_object = None
                    if customer != '':
                        customer = customer.upper()

                        try:
                            customer_object = Buyer.objects.get(name=customer)
                        except ObjectDoesNotExist:
                            customer_object = Buyer.objects.create(name=customer, shortcut=customer[:7])

                    # delivery date
                    delivery_date = ''
                    if row[5] != '':
                        delivery_date = row[5]

                    if sort == 'PRZEKLADKA':
                        dim1 = width
                        dim2 = height

                    if not break_condition2:
                        if len(name) > 15:
                            name = 'too long'

                        def add_order_item_object(function_order):
                            statement = ''
                            try:
                                order_item = OrderItem.objects.get(order=function_order, item_number=order_item_num)

                                if delivery_date != '':
                                    order_item.planned_delivery = datetime.datetime.strptime(delivery_date, '%Y-%m-%d')
                                    order_item.save()

                                statement += f'{order_item} || {width}x{height} :: {dimensions}({name}) ALREADY EXISTS'
                            except ObjectDoesNotExist:
                                new_order_item = OrderItem.objects.create(order=function_order,
                                                                          item_number=order_item_num,
                                                                          sort=sort,
                                                                          dimension_one=dim1, dimension_two=dim2,
                                                                          dimension_three=dim3, scores=scores,
                                                                          format_width=width,
                                                                          format_height=height,
                                                                          ordered_quantity=quantity,
                                                                          cardboard_type=cardboard_type,
                                                                          cardboard_weight=cardboard_weight,
                                                                          cardboard_additional_info=cardboard_extra,
                                                                          name=name)
                                if delivery_date != '':
                                    new_order_item.planned_delivery = datetime.datetime.strptime(delivery_date,
                                                                                                 '%Y-%m-%d')
                                    new_order_item.save()
                                statement += f'{new_order_item} || {width}x{height} :: {dimensions}({name}) CREATED'
                                if customer_object:
                                    new_order_item.buyer.add(customer_object)

                            return statement

                        try:
                            order = Order.objects.get(provider=provider_object, order_provider_number=order_num)
                            result.append(add_order_item_object(order))
                        except ObjectDoesNotExist:
                            # order date
                            order_date = row[4]

                            new_order = Order.objects.create(provider=provider_object, order_provider_number=order_num,
                                                             date_of_order=datetime.datetime.strptime(order_date,
                                                                                                      '%Y-%m-%d'),
                                                             is_completed=True)

                            new_order.save()
                            result.append(f'ORDER {new_order} CREATED')

                            result.append(add_order_item_object(new_order))

        return render(request, 'warehousemanager-import-records.html', locals())


class PrepareManySpreadsheetsForm(View):

    def get(self, request):
        all_orders = Order.objects.all()
        all_items = OrderItem.objects.all()

        return render(request, 'warehousemanager-prepare-gs.html', locals())

    def post(self, request):
        order_items = request.POST.get('order_items')

        '''scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']

        creds_dict = {
            "type": "service_account",
            "project_id": os.environ['PROJECT_ID'],
            "private_key_id": os.environ['PRIVATE_KEY_ID'],
            "private_key": google_key(),
            "client_email": os.environ['CLIENT_EMAIL'],
            "client_id": os.environ['CLIENT_ID'],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": os.environ['CLIENT_CERT_URL']
        }

        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)

        client = gspread.authorize(creds)'''

        '''for o in order_items:
            new_title = f'{o}'

            new_gs = client.copy(file_id='1II0BeYj-FuJtWFSkU8mUmU6lMRPqXvWTQw-DXqfzmio', title=new_title,
                                 copy_permissions=True)

            SpreadsheetCopy.objects.create(gs_id=new_gs.id)'''

        return HttpResponse('CREATED', order_items)


class PrepareManySpreadsheets(View):

    def get(self, request):
        nums = []
        prepared_gs = []
        items_nums = request.GET.get('items_nums')
        split_nums = items_nums.split('*')
        for s in split_nums:
            if s != '':
                nums.append(int(s))
        scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']

        creds_dict = {
            "type": "service_account",
            "project_id": os.environ['PROJECT_ID'],
            "private_key_id": os.environ['PRIVATE_KEY_ID'],
            "private_key": google_key(),
            "client_email": os.environ['CLIENT_EMAIL'],
            "client_id": os.environ['CLIENT_ID'],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": os.environ['CLIENT_CERT_URL']
        }

        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)

        client = gspread.authorize(creds)

        for n in nums:
            order_name = f'{OrderItem.objects.get(id=n)}'
            prepared_gs.append((order_name, create_spreadsheet_copy(n)))

        return HttpResponse(json.dumps(prepared_gs))


class ScheduledDelivery(View, PermissionRequiredMixin):
    permission_required = 'warehousemanager.view_delivery'

    def get(self, request):
        date = request.GET.get('date')
        date_range = request.GET.get('date_range')

        items = None

        if date and not date_range:
            items = OrderItem.objects.filter(planned_delivery=datetime.datetime.strptime(date, '%Y-%m-%d'))
        elif date and date_range:
            items = OrderItem.objects.filter(planned_delivery__gte=datetime.datetime.strptime(date, '%Y-%m-%d'))
            items = items.filter(planned_delivery__lte=datetime.datetime.strptime(date_range, '%Y-%m-%d')).order_by(
                'planned_delivery')

        return render(request, 'warehousemanager-scheduled-delivery.html', locals())


class PhotoPolymers(View, PermissionRequiredMixin):
    permission_required = 'warehousemanager.view_photopolymer'

    def get(self, request):

        user = request.user
        visit_counter(user, 'polymer_list')

        polymers = Photopolymer.objects.all().order_by('customer__name', 'name')
        services = PhotopolymerService.objects.all()
        current_services = []
        history_services = []

        for s in services:
            if s.status():
                current_services.append(s)
            else:
                history_services.append(s)
        return render(request, 'warehousemanager-photopolymers.html', locals())


class PhotoPolymerDetail(View, PermissionRequiredMixin):
    permission_required('warehousemanager.view_photopolymer')

    def get(self, request, polymer_id):
        polymer = Photopolymer.objects.get(id=polymer_id)
        services = PhotopolymerService.objects.filter(photopolymer=polymer)
        colors = polymer.colors.all()

        return render(request, 'warehousemanager-polymer-detail.html', locals())


'''class PolymerCreate(CreateView):
    model = Photopolymer
    fields = ['producer', 'identification_number', 'customer', 'name', 'delivery_date', 'project']'''


class PolymerCreate(View):

    def get(self, request):
        form = PolymerForm()
        return render(request, 'warehousemanager/photopolymer_form.html', locals())

    def post(self, request):
        form = PolymerForm(request.POST, request.FILES)

        if form.is_valid():
            form.save()
            return HttpResponse('ok')


class PolymerUpdate(UpdateView):
    model = Photopolymer
    fields = ['producer', 'identification_number', 'customer', 'name', 'delivery_date', 'project']
    template_name_suffix = '_update_form'


class PolymerDelete(DeleteView):
    model = Photopolymer
    success_url = reverse_lazy('photopolymers')


class ServiceDetailView(DetailView):
    model = PhotopolymerService


class ServiceListView(ListView):
    model = PhotopolymerService


class ServiceCreate(CreateView):
    model = PhotopolymerService
    fields = ['photopolymer', 'send_date', 'company', 'service_description', 'return_date']


class ServiceUpdate(UpdateView):
    model = PhotopolymerService
    fields = ['photopolymer', 'send_date', 'company', 'service_description', 'return_date']
    template_name_suffix = '_update_form'


class ServiceDelete(DeleteView):
    model = PhotopolymerService
    success_url = reverse_lazy('photopolymers')


class ColorListView(ListView, PermissionRequiredMixin):
    permission_required = 'warehousemanager.view_color'
    # add_random_color(15)
    model = Color


class ColorDetail(View, PermissionRequiredMixin):
    permission_required = 'warehousemanager.view_color'

    def get(self, request, color_id):
        c = Color.objects.get(id=color_id)

        history = []

        polymers = Photopolymer.objects.filter(colors=c)

        deliveries = ColorDelivery.objects.filter(color=c)
        usage = ColorUsage.objects.filter(color=c)
        events = ColorSpecialEvent.objects.filter(color=c)

        for d in deliveries:
            history.append((datetime.datetime.strftime(d.date, '%Y-%m-%d'), d, d.weight))

        for u in usage:
            history.append(
                (datetime.datetime.strftime(u.production.date_end, '%Y-%m-%d'), u.production, float(u.value * (-1))))

        for e in events:
            history.append((datetime.datetime.strftime(e.date, '%Y-%m-%d'), e.event, e.difference))

        history = sorted(history, key=lambda x: x[0])

        return render(request, 'warehousemanager-color-detail.html', locals())


class ProductionProcessListView(ListView, PermissionRequiredMixin):
    permission_required = 'warehousemanager.view_productionprocess'
    model = ProductionProcess


class ProductionProcessCreate(CreateView):
    model = ProductionProcess
    fields = ['order_item', 'production', 'stock', 'type', 'worker', 'machine', 'quantity_start', 'quantity_end',
              'date_start', 'date_end', 'punch', 'polymer']


class AvailableVacation(View):

    def get(self, request):
        title = 'Available Vacations'
        year = datetime.datetime.now().year if not request.GET.get('year-choice') else int(
            request.GET.get('year-choice'))
        years = [x for x in range(2020, datetime.datetime.now().year + 2)]
        persons_data = []
        persons = Person.objects.filter(job_end=None)
        for p in persons:
            used_vacation_in_year = 0
            previous_year = year - 1
            absences = Absence.objects.filter(worker=p, absence_date__gt=datetime.date(int(previous_year), 12, 31),
                                              absence_date__lte=datetime.date(int(year), 12, 31))
            for a in absences:
                if a.absence_type == 'UW':
                    used_vacation_in_year += 1
            left_vacation = p.yearly_vacation_limit - used_vacation_in_year
            persons_data.append((p, p.yearly_vacation_limit, p.end_year_vacation(previous_year), used_vacation_in_year,
                                 p.end_year_vacation(year)))

        return render(request, 'warehousemanager-vacation-list.html', locals())


class PersonsVacations(View):

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
class PersonListView(View, PermissionRequiredMixin):
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
class PersonDetailView(View, PermissionRequiredMixin):
    permission_required = 'warehousemanager.view_person'

    def get(self, request, person_id):
        person = Person.objects.get(id=person_id)
        visit_counter(request.user, f'Person details - {person.get_initials()}')
        contracts = Contract.objects.filter(worker=person).order_by('date_start')
        return render(request, 'warehousemanager-person-details.html', locals())


# contract view
class ContractCreate(CreateView):
    model = Contract
    fields = ['worker', 'type', 'date_start', 'date_end', 'salary', 'extra_info']


# reminder view
class ReminderListView(View, PermissionRequiredMixin):
    permission_required = 'warehousemanager.view_reminder'

    def get(self, request):
        reminders = Reminder.objects.all().order_by('create_date')
        return render(request, 'warehousemanager-reminders-list.html', locals())


class ReminderDetailsView(View, PermissionRequiredMixin):
    permission_required = 'warehousemanager.view_reminder'

    def get(self, request, reminder_id):
        reminder = Reminder.objects.get(id=int(reminder_id))
        reminder_content = compose_mail(reminder)
        if not reminder.sent_date:
            reminder.sent_date = datetime.date.today()
            reminder.save()

        return render(request, 'warehousemanager-reminder-details.html', locals())


class ReminderDeleteView(View, PermissionRequiredMixin):
    permission_required = 'warehousemanager.view_reminder'

    def get(self, request, reminder_id):
        reminder = Reminder.objects.get(id=int(reminder_id))
        reminder.delete()

        print('visit')

        return redirect('reminders')


class PaletteQuantitiesView(View, PermissionRequiredMixin):
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
            result = [delivery.date_of_delivery] + ['-' for _ in palettes_list] + ['-' for _ in palettes_list]
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
