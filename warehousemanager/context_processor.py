from django.utils import timezone


def actual_date(request):
    ctx = {
        'now': timezone.now()
    }
    return ctx
