from django.utils import timezone
from warehousemanager.models import Reminder
from warehousemanager.functions import reminders_qs


def actual_date(request):
    ctx = {
        'now': timezone.now()
    }
    return ctx


def new_reminders(request):

    return {
        'new_reminders': reminders_qs()
    }
