# views.py
import csv
from datetime import datetime
from django.shortcuts import render
from .forms import CSVUploadForm
from .models import MonthResults


def import_csv_view(request):
    success = 0
    error_lines = []

    if request.method == 'POST':
        form = CSVUploadForm(request.POST, request.FILES)
        if form.is_valid():
            file = form.cleaned_data['file']
            decoded = file.read().decode('utf-8').splitlines()
            reader = csv.DictReader(decoded, delimiter=';')

            month = 1
            year = 2022

            for line_num, row in enumerate(reader, start=2):
                try:
                    management = int(float(row['management_expenses'].replace(',', '.')))
                    logistic = int(float(row['logistic_expenses'].replace(',', '.')))
                    other = int(float(row['other_expenses'].replace(',', '.')))

                    MonthResults.objects.create(
                        year=year,
                        month=month,
                        expenses=int(row['expenses']),
                        financial_expenses=int(row['financial_expenses']),
                        management_expenses=management,
                        logistic_expenses=logistic,
                        other_expenses=other,
                    )
                    success += 1
                    month += 1
                    if month > 12:
                        month = 1
                        year += 1

                except Exception as e:
                    error_lines.append((line_num, str(e)))

    else:
        form = CSVUploadForm()

    return render(request, 'warehouse/import_csv.html', {
        'form': form,
        'success': success,
        'error_lines': error_lines,
    })
