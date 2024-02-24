from django.urls import path
from deliveries.views import *


urlpatterns = [
    path('calendar/', CalendarView.as_view(), name='deliveries-calendar'),
    path('events-by-day/', EventsByDay.as_view()),
    path('day-details/<str:date>/', DayDetails.as_view(), name='day-details'),
    path('add-event/', AddEvent.as_view(), name='add-event'),
    path('event-details/<int:event_id>/', EventDetail.as_view(), name='event-detail'),
    path('event-edit/<int:event_id>/', EventEdit.as_view(), name='event-edit'),
    path('event-delete/<int:event_id>/', EventDelete.as_view(), name='event-delete')
]