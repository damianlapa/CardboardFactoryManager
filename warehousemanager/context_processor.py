from django.utils import timezone
from warehousemanager.models import Reminder
from warehousemanager.functions import reminders_qs, new_messages_function


def actual_date(request):
    ctx = {
        'now': timezone.now()
    }
    return ctx


def new_reminders(request):

    return {
        'new_reminders': reminders_qs()
    }


def new_messages(request):

    return {
        'new_messages': new_messages_function(request)
    }


