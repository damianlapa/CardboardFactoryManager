from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.decorators import method_decorator
from django.views.generic import FormView

from .forms import PriceListUploadForm
from .models import PriceList, PriceListItem, Provider
from .services.pricelist_parser import parse_pricelist_pdf


@method_decorator([login_required, permission_required('app.add_pricelist', raise_exception=True)], name='dispatch')
class PriceListUploadView(FormView):
    template_name = 'warehouse/load_price_list.html'
    form_class = PriceListUploadForm

    def form_valid(self, form):
        pdf_file = form.cleaned_data['pdf_file']
        date_start = form.cleaned_data['date_start']
        date_end = form.cleaned_data['date_end']

        pdf_bytes = pdf_file.read()

        try:
            provider_code, items = parse_pricelist_pdf(pdf_bytes)
        except Exception as e:
            messages.error(self.request, f'Błąd parsowania PDF: {e}')
            return self.form_invalid(form)

        # Dopasuj providera po nazwie/kodzie
        provider = Provider.objects.filter(name__icontains=provider_code).first()
        if not provider:
            messages.error(self.request, f'Nie znaleziono providera o nazwie/kodzie: {provider_code}')
            return self.form_invalid(form)

        try:
            with transaction.atomic():
                price_list = PriceList.objects.create(
                    provider=provider,
                    date_start=date_start,
                    date_end=date_end
                )

                created = 0
                updated = 0
                for row in items:
                    # Jeśli w modelu PriceListItem name jest CharField:
                    name_value = row['name']

                    obj, is_created = PriceListItem.objects.update_or_create(
                        price_list=price_list,
                        name=name_value,  # Jeśli masz FK do Product, to przemapuj tutaj
                        defaults={
                            'flute': row.get('flute') or '',
                            'weight': int(row.get('weight') or 0),
                            'etc': row.get('ect'),
                            'price': int(row.get('price') or 0),
                            'price2': (int(row['price2']) if row.get('price2') is not None else None),
                        }
                    )
                    if is_created:
                        created += 1
                    else:
                        updated += 1

        except Exception as e:
            messages.error(self.request, f'Błąd zapisu do bazy: {e}')
            return self.form_invalid(form)

        messages.success(
            self.request,
            f'Załadowano cennik dla {provider} ({date_start} – {date_end or "—"}). '
            f'Wiersze: utworzono {created}, zaktualizowano {updated}.'
        )
        return redirect('warehouse:price_list-upload')
