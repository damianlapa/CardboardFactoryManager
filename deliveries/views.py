from django.shortcuts import render, HttpResponse, redirect
from django.views import View
from deliveries.models import Event
from deliveries.forms import EventForm
from django.http import JsonResponse
import json

import datetime

MONTHS = (
    'JANUARY',
    'FEBRUARY',
    'MARCH',
    'APRIL',
    'MAY',
    'JUNE',
    'JULY',
    'AUGUST',
    'SEPTEMBER',
    'OCTOBER',
    'NOVEMBER',
    'DECEMBER'
)


class CalendarView(View):
    def get(self, request):

        another_start = request.GET.get('start')

        if another_start:
            y, m = another_start.split('-')

            y = int(y)
            m = int(m)

            today = datetime.datetime(y, m, 1)
        else:
            today = datetime.datetime.today().date()

        month_desc = f'{MONTHS[today.month - 1]} {today.year}'

        month_start = datetime.datetime(today.year, today.month, 1)
        month_start_weekday = month_start.isoweekday()

        weeks = []

        day_start = month_start - datetime.timedelta(days=month_start_weekday - 1)

        for _ in range(5):
            week = []
            for _ in range(7):
                if day_start.isoweekday() <= 5:
                    week.append((day_start, f'{day_start.year}-{day_start.month}-{day_start.day}'))
                day_start += datetime.timedelta(days=1)
            weeks.append(week)

        today = datetime.datetime(today.year, today.month, today.day)

        n_month = f'{today.year}-{today.month + 1}' if today.month < 12 else f'{today.year + 1}-1'
        p_month = f'{today.year}-{today.month - 1}' if today.month > 1 else f'{today.year - 1}-12'

        today = datetime.datetime.today()

        today = datetime.datetime(today.year, today.month, today.day)

        return render(request, 'deliveries/calendar.html', locals())


class EventsByDay(View):
    def get(self, request):
        calendar_date = request.GET.get('calendar')
        year, month, day = calendar_date.split('-')
        events = Event.objects.filter(day=datetime.datetime(int(year), int(month), int(day)))

        if events:
            result = []
            for e in events:
                result.append((e.title, e.event_type, e.id))
            return HttpResponse(json.dumps(result))
        else:
            return HttpResponse('')


class EventCheck(View):
    def get(self, request, event_id):
        event = Event.objects.get(id=event_id)
        if event.event_type == 'ZREALIZOWANA DOSTAWA':
            return JsonResponse({'success': False})
        else:
            event.event_type = 'ZREALIZOWANA DOSTAWA'
            event.save()
            return JsonResponse({'success': True})


class DayDetails(View):
    def get(self, request, date):
        year, month, day = date.split('-')
        day = datetime.datetime(int(year), int(month), int(day))

        events = Event.objects.filter(day=day)

        return render(request, 'deliveries/day-details.html', locals())


class AddEvent(View):
    def get(self, request):
        form = EventForm()

        if request.GET.get('day'):
            year, month, day = request.GET.get('day').split('-')
            form = EventForm(initial={'day': datetime.datetime(int(year), int(month), int(day))})

        return render(request, 'deliveries/add-event.html', locals())

    def post(self, request):
        form = EventForm(request.POST)

        if form.is_valid():
            data = form.cleaned_data

            event_type = data['event_type']
            title = data['title']
            day = data['day']
            details = data['details']

            e = Event.objects.create(event_type=event_type, title=title, day=day, details=details)

            e.save()

            return redirect('deliveries-calendar')


class EventDetail(View):
    def get(self, request, event_id):
        event = Event.objects.get(id=int(event_id))

        str_date = f'{event.day.year}-{event.day.month}-{event.day.day}'

        return render(request, 'deliveries/event-details.html', locals())
    
    
class EventEdit(View):
    def get(self, request, event_id):
        event = Event.objects.get(id=int(event_id))
        form = EventForm(initial={
            'title': event.title,
            'event_type': event.event_type,
            'details': event.details,
            'day': event.day,
        })

        return render(request, 'deliveries/add-event.html', locals())

    def post(self, request, event_id):
        form = EventForm(request.POST)

        if form.is_valid():
            data = form.cleaned_data

            event_type = data['event_type']
            title = data['title']
            day = data['day']
            details = data['details']

            event = Event.objects.get(id=event_id)

            event.event_type = event_type
            event.title = title
            event.day = day
            event.details = details

            event.save()

            return redirect('event-detail', event_id=event.id)


class EventDelete(View):
    def get(self, request, event_id):
        event = Event.objects.get(id=event_id)
        day = f'{event.day.year}-{event.day.month}-{event.day.day}'
        event.delete()

        return redirect('day-details', date=day)
