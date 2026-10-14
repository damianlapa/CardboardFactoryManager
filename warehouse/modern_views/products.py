import json

from django import forms
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views import View

from warehouse.models import Product, ProductPackaging
from orders.models import ProductMaterialRequirement
from warehouse.services.products import products_queryset, summarize_product


class ModernProductListView(LoginRequiredMixin, View):
    login_url = 'login'
    template_name = 'warehouse/products/list.html'

    def get(self, request):
        search = request.GET.get('search', '').strip()
        status = request.GET.get('status', 'all')
        if status not in {'all', 'complete', 'missing', 'packaging', 'material'}:
            status = 'all'
        base = products_queryset(search=search)
        counters = base.aggregate(
            total=Count('pk'),
            complete=Count('pk', filter=Q(has_valid_packaging=True, has_valid_material=True)),
            packaging=Count('pk', filter=Q(has_valid_packaging=False)),
            material=Count('pk', filter=Q(has_valid_material=False)),
        )
        counters['missing'] = counters['total'] - counters['complete']
        qs = products_queryset(search=search, status=status).select_related(
            'packaging__palette', 'material_requirement_template'
        )
        paginator = Paginator(qs, 30)
        page_obj = paginator.get_page(request.GET.get('page'))
        rows = [summarize_product(product) for product in page_obj.object_list]
        return render(request, self.template_name, {
            'rows': rows, 'page_obj': page_obj, 'search': search,
            'status': status, 'counters': counters,
        })


class PackagingForm(forms.ModelForm):
    class Meta:
        model = ProductPackaging
        fields = ('palette', 'columns', 'layers', 'qty_per_pack', 'additional_info')
        labels = {
            'palette': 'Paleta', 'columns': 'Słupki', 'layers': 'Warstwy',
            'qty_per_pack': 'Sztuk w paczce', 'additional_info': 'Dodatkowe informacje',
        }
        widgets = {'additional_info': forms.Textarea(attrs={'rows': 3})}

    def clean(self):
        cleaned = super().clean()
        for key in ('columns', 'layers', 'qty_per_pack'):
            value = cleaned.get(key)
            if value is None or value <= 0:
                self.add_error(key, 'Podaj liczbę większą od zera.')
        if not cleaned.get('palette'):
            self.add_error('palette', 'Wybierz paletę.')
        return cleaned


class MaterialForm(forms.ModelForm):
    class Meta:
        model = ProductMaterialRequirement
        fields = (
            'sheet_length', 'sheet_width', 'pieces_per_sheet', 'layers',
            'flute', 'min_gsm', 'min_ect', 'cover', 'scores', 'notes',
        )
        labels = {
            'sheet_length': 'Długość arkusza (mm)', 'sheet_width': 'Szerokość arkusza (mm)',
            'pieces_per_sheet': 'Produktów z arkusza', 'layers': 'Warstwy',
            'flute': 'Fala', 'min_gsm': 'Minimalna gramatura (g/m²)',
            'min_ect': 'Minimalne ECT (kN/m)', 'cover': 'Pokrycie',
            'scores': 'Bigowanie', 'notes': 'Uwagi',
        }
        widgets = {'notes': forms.Textarea(attrs={'rows': 3})}

    def clean(self):
        cleaned = super().clean()
        for key in ('sheet_length', 'sheet_width', 'pieces_per_sheet', 'layers', 'min_gsm', 'min_ect'):
            value = cleaned.get(key)
            if value is None or value <= 0:
                self.add_error(key, 'Podaj wartość większą od zera.')
        for key in ('flute', 'cover'):
            if not cleaned.get(key):
                self.add_error(key, 'To pole jest wymagane.')
        return cleaned


class ProductConfigurationEditView(LoginRequiredMixin, View):
    login_url = 'login'
    form_template = 'warehouse/products/_modal_form.html'

    def get_form(self, product, kind, data=None):
        if kind == 'packaging':
            instance = ProductPackaging.objects.filter(product=product).first()
            return PackagingForm(data=data, instance=instance)
        if kind == 'material':
            instance = ProductMaterialRequirement.objects.filter(product=product).first()
            return MaterialForm(data=data, instance=instance)
        return None

    def dispatch(self, request, *args, **kwargs):
        self.product = get_object_or_404(Product, pk=kwargs['pk'])
        self.kind = kwargs['kind']
        if self.kind not in ('packaging', 'material'):
            return JsonResponse({'ok': False, 'message': 'Nieznany typ konfiguracji.'}, status=404)
        # Dopasuj do własnej polityki dostępu, jeżeli edycja jest zastrzeżona dla innych grup.
        if not request.user.is_staff and not request.user.is_superuser:
            return JsonResponse({'ok': False, 'message': 'Brak uprawnień do edycji.'}, status=403)
        return super().dispatch(request, *args, **kwargs)

    def render_form(self, form):
        from django.template.loader import render_to_string
        return render_to_string(self.form_template, {
            'form': form,
            'kind': self.kind,
            'product': self.product,
            'heading': 'Edytuj pakowanie' if self.kind == 'packaging' else 'Edytuj wymagania materiałowe',
        }, request=self.request)

    def get(self, request, *args, **kwargs):
        form = self.get_form(self.product, self.kind)
        return JsonResponse({'ok': True, 'html': self.render_form(form)})

    def post(self, request, *args, **kwargs):
        form = self.get_form(self.product, self.kind, request.POST)
        if not form.is_valid():
            return JsonResponse({'ok': False, 'html': self.render_form(form)}, status=422)
        with transaction.atomic():
            obj = form.save(commit=False)
            obj.product = self.product
            obj.save()
        return JsonResponse({'ok': True, 'message': 'Zapisano zmiany.'})
