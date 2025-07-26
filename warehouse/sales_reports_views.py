from django.shortcuts import render
from datetime import datetime
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
from .models import ProductSell3


def sales_report_view(request):
    start_raw = request.GET.get('start')
    end_raw = request.GET.get('end')

    start_date = datetime.fromisoformat(start_raw).date() if start_raw else None
    end_date = datetime.fromisoformat(end_raw).date() if end_raw else None

    sales = ProductSell3.objects.all()
    if start_date and end_date:
        sales = sales.filter(date__range=(start_date, end_date))

    context = {
        'sales': sales,
        'start_date': start_date,
        'end_date': end_date,
    }
    return render(request, 'warehouse/sales_report.html', context)


def parse_custom_date(date_str):
    """Obsługuje formaty typu 'Dec. 12, 2024' lub 'July 25, 2025'."""
    for fmt in ("%b. %d, %Y", "%B %d, %Y"):  # grudzień jako 'Dec.' lub 'December'
        try:
            return datetime.strptime(date_str, fmt).date()
        except (ValueError, TypeError):
            continue
    return None

def sales_pdf_view(request):
    start_raw = request.GET.get('start')
    end_raw = request.GET.get('end')

    print("START RAW:", start_raw)
    print("END RAW:", end_raw)

    start_date = parse_custom_date(start_raw)
    end_date = parse_custom_date(end_raw)

    print("START PARSED:", start_date)
    print("END PARSED:", end_date)

    if not start_date or not end_date:
        return HttpResponse("Nieprawidłowy format daty!", status=400)

    result = []
    sales = ProductSell3.objects.filter(date__range=(start_date, end_date))

    for s in sales:
        row = []
        row.append(s)


    template = get_template('warehouse/sales_pdf.html')
    html = template.render({
        'sales': sales,
        'start_date': start_date,
        'end_date': end_date,
    })

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="raport_sprzedazy.pdf"'
    pisa.CreatePDF(html, dest=response)
    return response