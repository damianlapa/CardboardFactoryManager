from django.urls import path
from deliveries.views import *


urlpatterns = [
    path('calendar/', CalendarView.as_view(), name='deliveries-calendar'),
    path('events-by-day/', EventsByDay.as_view())
]