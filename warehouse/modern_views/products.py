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
from warehousemanager.models import Buyer
from warehouse.services.naming import build_product_name, norm_names
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


class ProductCreateForm:
    def __init__(self, data=None):
        self.product_form = ProductForm(data=data, prefix="product")
        self.packaging_form = PackagingForm(data=data, prefix="packaging")
        self.material_form = MaterialForm(data=data, prefix="material")
        self.has_packaging = data is not None and data.get("include_packaging") == "1"
        self.has_material = data is not None and data.get("include_material") == "1"

    def is_valid(self):
        valid = self.product_form.is_valid()
        if self.has_packaging:
            valid = self.packaging_form.is_valid() and valid
        if self.has_material:
            valid = self.material_form.is_valid() and valid
        return valid

    def save(self):
        with transaction.atomic():
            product = self.product_form.save()
            if self.has_packaging:
                packaging = self.packaging_form.save(commit=False)
                packaging.product = product
                packaging.save()
            if self.has_material:
                material = self.material_form.save(commit=False)
                material.product = product
                material.save()
            return product


class ProductConfigurationEditView(LoginRequiredMixin, View):
    login_url = 'login'
    form_template = 'warehouse/products/_modal_form.html'

    def get_form(self, product, kind, data=None):
        if kind == "product":
            return ProductForm(
                data=data,
                instance=product,
            )
        if kind == 'packaging':
            instance = ProductPackaging.objects.filter(product=product).first()
            return PackagingForm(data=data, instance=instance)
        if kind == 'material':
            instance = ProductMaterialRequirement.objects.filter(product=product).first()
            return MaterialForm(data=data, instance=instance)
        return None

    def dispatch(self, request, *args, **kwargs):
        self.product = get_object_or_404(
            Product,
            pk=kwargs["pk"],
        )

        self.kind = kwargs["kind"]

        if self.kind not in (
                "product",
                "packaging",
                "material",
        ):
            return JsonResponse(
                {
                    "ok": False,
                    "message": "Nieznany typ konfiguracji.",
                },
                status=404,
            )

        if not request.user.is_staff and not request.user.is_superuser:
            return JsonResponse(
                {
                    "ok": False,
                    "message": "Brak uprawnień do edycji.",
                },
                status=403,
            )

        return super().dispatch(request, *args, **kwargs)

    def render_form(self, form):
        from django.template.loader import render_to_string
        return render_to_string(self.form_template, {
            'form': form,
            'kind': self.kind,
            'product': self.product,
            'heading': {'product': 'Edytuj produkt', 'packaging': 'Edytuj pakowanie', 'material': 'Edytuj wymagania materiałowe'}[self.kind],
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
            if self.kind != "product":
                obj.product = self.product
            obj.save()
        return JsonResponse({'ok': True, 'message': 'Zapisano zmiany.'})


class ProductForm(forms.ModelForm):
    customer = forms.ModelChoiceField(
        queryset=Buyer.objects.all(), label="Klient", required=True,
        empty_label="Wybierz klienta",
    )
    extra_name = forms.CharField(label="Nazwa dodatkowa", required=False, max_length=100)

    class Meta:
        model = Product
        fields = ("FEFCO_code", "dimensions", "flute", "gsm", "price")
        labels = {
            "FEFCO_code": "Kod FEFCO", "dimensions": "Wymiary produktu",
            "flute": "Fala produktu", "gsm": "Gramatura (g/m²)", "price": "Cena",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            parts = [part.strip() for part in (self.instance.name or "").split("|")]
            if parts:
                customer = next(
                    (buyer for buyer in Buyer.objects.all() if str(buyer).strip().casefold() == parts[0].casefold()),
                    None,
                )
                if customer:
                    self.fields["customer"].initial = customer
            if len(parts) > 3:
                self.fields["extra_name"].initial = " | ".join(parts[3:])

    def clean(self):
        cleaned = super().clean()
        customer = cleaned.get("customer")
        flute = cleaned.get("flute")
        dimensions = cleaned.get("dimensions")
        if customer and flute and dimensions:
            name = norm_names(build_product_name(
                customer=str(customer), flute=flute, dimensions=dimensions,
                extra=cleaned.get("extra_name", ""),
            ))
            if len(name) > Product._meta.get_field("name").max_length:
                self.add_error("extra_name", "Wygenerowana nazwa jest zbyt długa (maks. 128 znaków).")
            elif Product.objects.filter(name=name).exclude(pk=self.instance.pk).exists():
                self.add_error("extra_name", "Produkt o takiej nazwie już istnieje.")
            else:
                cleaned["generated_name"] = name
        return cleaned

    def save(self, commit=True):
        product = super().save(commit=False)
        product.name = self.cleaned_data["generated_name"]
        if commit:
            product.save()
            self.save_m2m()
        return product


class ProductCreateView(LoginRequiredMixin, View):
    login_url = "login"

    form_template = "warehouse/products/_modal_create.html"

    def dispatch(self, request, *args, **kwargs):
        if not (
            request.user.is_staff
            or request.user.is_superuser
        ):
            return JsonResponse(
                {
                    "ok": False,
                    "message": "Brak uprawnień do dodawania produktów.",
                },
                status=403,
            )

        return super().dispatch(request, *args, **kwargs)

    def render_form(self, form):
        from django.template.loader import render_to_string

        return render_to_string(
            self.form_template,
            {
                "heading": "Dodaj nowy produkt",
                "product_form": form.product_form,
                "packaging_form": form.packaging_form,
                "material_form": form.material_form,
                "include_packaging": form.has_packaging,
                "include_material": form.has_material,
            },
            request=self.request,
        )

    def get(self, request, *args, **kwargs):
        form = ProductCreateForm()

        return JsonResponse(
            {
                "ok": True,
                "html": self.render_form(form),
            }
        )

    def post(self, request, *args, **kwargs):
        form = ProductCreateForm(request.POST)

        if not form.is_valid():
            return JsonResponse(
                {
                    "ok": False,
                    "html": self.render_form(form),
                },
                status=422,
            )

        product = form.save()

        return JsonResponse(
            {
                "ok": True,
                "message": "Produkt i jego konfiguracja zostały zapisane.",
                "product_id": product.pk,
            }
        )
