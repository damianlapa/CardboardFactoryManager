import datetime


def work_days_during_period(year=None, start=None, end=None):
    if not year:
        year = datetime.datetime.today().year

    if not start:
        start = datetime.datetime.strptime(f'{year}-01-01', '%Y-%m-%d')

    if not end:
        end = datetime.datetime.strptime(f'{year}-12-31', '%Y-%m-%d')

    full_weeks_start_day = start + datetime.timedelta(days=(7-start.weekday()))
    full_weeks_end_day = end - datetime.timedelta(end.weekday())

    if isinstance(full_weeks_start_day, datetime.datetime):
        full_weeks_start_day = full_weeks_start_day.date()
    if isinstance(full_weeks_end_day, datetime.datetime):
        full_weeks_end_day = full_weeks_end_day.date()

    days_to_add = 5 - start.weekday() if start.weekday() < 5 else 0
    days_to_add_2 = 1 + end.weekday() if end.weekday() < 5 else 5

    return days_to_add_2 + days_to_add + ((full_weeks_end_day - full_weeks_start_day).days // 7)*5