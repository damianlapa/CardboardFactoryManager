import os
import gspread
import datetime
import random
from django.utils import timezone
from oauth2client.service_account import ServiceAccountCredentials
from warehousemanager.models import *
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import send_mail

COLORS = ('Red', 'Green', 'Blue', 'Yellow', 'Pink', 'Orange', 'Purple', 'Brown')

MONTHS = {
    '1': 'January',
    '2': 'February',
    '3': 'March',
    '4': 'April',
    '5': 'May',
    '6': 'June',
    '7': 'July',
    '8': 'August',
    '9': 'September',
    '10': 'October',
    '11': 'November',
    '12': 'December'
}


def visit_counter(user, page):
    # personal setting
    if user.is_authenticated and user.username != 'damian':
        try:
            visit = UserVisitCounter.objects.get(user=user, page=page)
            visit.counter += 1
            visit.last_visit = datetime.datetime.now()
            visit.save()
        except ObjectDoesNotExist:
            new_visit = UserVisitCounter.objects.create(user=user, page=page, first_visit=timezone.now(),
                                                        last_visit=timezone.now())
            new_visit.save()


def change_minutes_to_hours(minutes):
    return f'{minutes // 60}:{minutes % 60}' if minutes % 60 > 9 else f'{minutes // 60}:0{minutes % 60}'


def change_month_num_to_name(num):
    return MONTHS[str(num)]


def check_contract_expiration_date(worker):
    if worker.job_end:
        return -1
    else:
        worker_contracts = Contract.objects.filter(worker=worker)
        if len(worker_contracts) == 0:
            return 0
        else:
            for c in worker_contracts:
                if not c.date_end:
                    return 10000
                else:
                    if c.date_end >= datetime.date.today() > c.date_start:
                        return (c.date_end - datetime.date.today()).days


def check_medical_examination_expiration_date(worker):
    if not worker.medical_examination:
        return 0
    else:
        return (worker.medical_examination - datetime.date.today()).days


def compose_mail(reminder):
    reason, days, event_day = reminder.title.split('*')
    days = int(days)
    reason_text = reason.lower()

    if days == 0:
        title = f"{reminder.worker}'s {reason_text} just ends!"
        html = f"{reminder.worker}'s {reason_text} just ends! Did you prepare new one with this worker?"

    else:
        title = f"{reminder.worker}'s {reason_text} ends within next {days} days!"
        html = f"{reminder.worker}'s {reason_text} ends within next {days} days({event_day})! Consider prepare new one!"

    return title, html


def create_or_send_reminder(worker, days_left, topic):
    topic = topic.upper()
    if days_left:
        date = datetime.date.today() + datetime.timedelta(days=int(days_left))
        date = datetime.date.strftime(date, '%Y-%m-%d')
        if days_left == 0:
            try:
                reminder = Reminder.objects.filter(worker=worker, title=f'{topic}*0*{date}')[0]
                if not reminder.sent_date:
                    title, text = compose_mail(reminder)
                    # send_mail(title, '', '', [os.environ.get('MAIL_RECIPIENT')], html_message=text)
                    # reminder.sent_date = datetime.date.today()
                    reminder.save()
            except IndexError:
                Reminder.objects.create(worker=worker, title=f'{topic}*0*{date}', create_date=datetime.date.today())
        elif 8 > days_left > 0:
            try:
                reminder = Reminder.objects.filter(worker=worker, title=f'{topic}*7*{date}')[0]
                if not reminder.sent_date:
                    # title, text = compose_mail(reminder)
                    # send_mail(title, '', '', [os.environ.get('MAIL_RECIPIENT')], html_message=text)
                    # reminder.sent_date = datetime.date.today()
                    reminder.save()
            except IndexError:
                Reminder.objects.create(worker=worker, title=f'{topic}*7*{date}', create_date=datetime.date.today())
        elif 29 > days_left > 7:
            try:
                reminder = Reminder.objects.filter(worker=worker, title=f'{topic}*28*{date}')[0]
                if not reminder.sent_date:
                    title, text = compose_mail(reminder)
                    # send_mail(title, '', '', [os.environ.get('MAIL_RECIPIENT')], html_message=text)
                    # reminder.sent_date = datetime.date.today()
                    reminder.save()
            except IndexError:
                Reminder.objects.create(worker=worker, title=f'{topic}*28*{date}', create_date=datetime.date.today())


def reminders_qs():
    today_workers = Person.objects.filter(job_end=None)
    for t in today_workers:
        create_or_send_reminder(t, check_contract_expiration_date(t), 'contract')
        create_or_send_reminder(t, check_medical_examination_expiration_date(t), 'medical examination')
    reminders = Reminder.objects.filter(sent_date=None)
    if len(reminders) > 0:
        return True

    return False


def new_messages_function(request):
    user = request.user
    messages = Message.objects.filter(recipient=user, date_read__isnull=True).exclude(
        date_sent__isnull=True) if not user.is_anonymous else ()
    return len(messages) if len(messages) > 0 else False
