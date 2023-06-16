from django.shortcuts import render, HttpResponse, redirect
from django.views import View
from deliveries.models import Event

import json

import datetime


class CalendarView(View):
    def get(self, request):
        today = datetime.datetime.today().date()

        month_start = datetime.datetime(today.year, today.month, 1)
        month_start_weekday = month_start.isoweekday()

        weeks = []

        day_start = month_start - datetime.timedelta(days=month_start_weekday - 1)

        for _ in range(5):
            week = []
            for _ in range(7):
                week.append(day_start)
                day_start += datetime.timedelta(days=1)
            weeks.append(week)

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
                result.append((e.title, e.event_type))
            return HttpResponse(json.dumps(result))
        else:
            return HttpResponse('')
