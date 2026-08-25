from django.shortcuts import render, HttpResponse, redirect, reverse
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from deliveries.models import Event
from deliveries.forms import EventForm
from warehousemanager.models import Note
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


from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views import View

from deliveries.services.calendar import (
    get_month_context, create_event, get_events_for_day, get_week_context
)

from deliveries.services.calendar import (
    complete_event,
    create_event,
    delete_event,
    get_event,
    get_events_for_day,
    serialize_event,
    update_event,
)


class CalendarView(
    LoginRequiredMixin,
    View,
):
    login_url = reverse_lazy("login")
    template_name = "deliveries/calendar_new.html"

    def get(self, request):
        today = datetime.date.today()

        calendar_view = (
            request.GET.get(
                "view",
                "month",
            )
        )

        if calendar_view == "week":
            date_raw = (
                request.GET.get(
                    "date"
                )
            )

            try:
                selected_date = (
                    datetime.date.fromisoformat(
                        date_raw
                    )
                    if date_raw
                    else today
                )

            except (
                TypeError,
                ValueError,
            ):
                selected_date = today

            context = (
                get_week_context(
                    selected_date=
                        selected_date,
                )
            )

        else:
            year_raw = (
                request.GET.get(
                    "year"
                )
            )

            month_raw = (
                request.GET.get(
                    "month"
                )
            )

            try:
                year = int(
                    year_raw
                )
            except (
                TypeError,
                ValueError,
            ):
                year = today.year

            try:
                month = int(
                    month_raw
                )
            except (
                TypeError,
                ValueError,
            ):
                month = today.month

            if not 1 <= month <= 12:
                month = today.month

            context = (
                get_month_context(
                    year=year,
                    month=month,
                )
            )

        return render(
            request,
            self.template_name,
            context,
        )


class EventsByDay(LoginRequiredMixin, View):
    login_url = reverse_lazy('start-page')

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


class EventCheck(LoginRequiredMixin, View):
    login_url = reverse_lazy('start-page')

    def get(self, request, event_id):
        event = Event.objects.get(id=event_id)
        if event.event_type == 'ZREALIZOWANA DOSTAWA':
            return JsonResponse({'success': False})
        else:
            event.event_type = 'ZREALIZOWANA DOSTAWA'
            event.save()
            return JsonResponse({'success': True})


class DayDetails(LoginRequiredMixin, View):
    login_url = reverse_lazy('start-page')

    def get(self, request, date):
        year, month, day = date.split('-')
        day = datetime.datetime(int(year), int(month), int(day))

        events = Event.objects.filter(day=day)

        return render(request, 'deliveries/day-details.html', locals())


class AddEvent(LoginRequiredMixin, View):
    login_url = reverse_lazy('start-page')

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

            return redirect(f'{reverse("deliveries-calendar")}?start={day.year}-{day.month}')


class EventDetail(LoginRequiredMixin, View):
    login_url = reverse_lazy('start-page')

    def get(self, request, event_id):
        event = Event.objects.get(id=int(event_id))

        str_date = f'{event.day.year}-{event.day.month}-{event.day.day}'

        return render(request, 'deliveries/event-details.html', locals())
    
    
class EventEdit(LoginRequiredMixin, View):
    login_url = reverse_lazy('start-page')

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


class EventDelete(LoginRequiredMixin, View):
    login_url = reverse_lazy('start-page')

    def get(self, request, event_id):
        event = Event.objects.get(id=event_id)
        day = f'{event.day.year}-{event.day.month}-{event.day.day}'
        event.delete()

        return redirect('day-details', date=day)


class CalendarDayEventsView(
    LoginRequiredMixin,
    View,
):
    login_url = reverse_lazy("login")

    def get(self, request):
        day_raw = request.GET.get("day")

        try:
            day = datetime.date.fromisoformat(
                day_raw
            )
        except (TypeError, ValueError):
            return JsonResponse(
                {
                    "success": False,
                    "error": "Nieprawidłowa data.",
                },
                status=400,
            )

        return JsonResponse({
            "success": True,
            "day": day.isoformat(),
            "events": get_events_for_day(
                day
            ),
        })


class CalendarEventCreateView(
    LoginRequiredMixin,
    View,
):
    login_url = reverse_lazy("login")

    def post(self, request):
        try:
            event = create_event(
                event_type=request.POST.get(
                    "event_type"
                ),
                title=request.POST.get(
                    "title"
                ),
                day=request.POST.get(
                    "day"
                ),
                details=request.POST.get(
                    "details"
                ),
            )

        except ValueError as error:
            return JsonResponse(
                {
                    "success": False,
                    "error": str(error),
                },
                status=400,
            )

        return JsonResponse({
            "success": True,
            "event": {
                "id": event.id,
            },
        })


class CalendarEventDetailView(
    LoginRequiredMixin,
    View,
):
    login_url = reverse_lazy("login")

    def get(self, request, event_id):
        event = get_event(event_id)

        return JsonResponse({
            "success": True,
            "event": serialize_event(
                event
            ),
        })


class CalendarEventUpdateView(
    LoginRequiredMixin,
    View,
):
    login_url = reverse_lazy("login")

    def post(
        self,
        request,
        event_id,
    ):
        try:
            event = update_event(
                event_id=event_id,
                event_type=request.POST.get(
                    "event_type"
                ),
                title=request.POST.get(
                    "title"
                ),
                day=request.POST.get(
                    "day"
                ),
                details=request.POST.get(
                    "details"
                ),
            )

        except ValueError as error:
            return JsonResponse(
                {
                    "success": False,
                    "error": str(error),
                },
                status=400,
            )

        return JsonResponse({
            "success": True,
            "event": serialize_event(
                event
            ),
        })


class CalendarEventCompleteView(
    LoginRequiredMixin,
    View,
):
    login_url = reverse_lazy("login")

    def post(
        self,
        request,
        event_id,
    ):
        event = complete_event(
            event_id
        )

        return JsonResponse({
            "success": True,
            "event": serialize_event(
                event
            ),
        })


class CalendarEventDeleteView(
    LoginRequiredMixin,
    View,
):
    login_url = reverse_lazy("login")

    def post(
        self,
        request,
        event_id,
    ):
        delete_event(
            event_id
        )

        return JsonResponse({
            "success": True,
        })