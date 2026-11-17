from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.views import View
from django.views.generic.edit import FormView

from .forms import QuotationCreateForm, QuotationItemForm
from .services.create import create_quotation
from .services.dashboard import get_dashboard_context
from .services.detail import get_detail_context, get_item_formset, get_quotation
from .services.items import save_quotation_items
from .services.materials import search_materials
from django.http import JsonResponse


class QuotationDashboardView(LoginRequiredMixin, View):
    login_url = "login"
    template_name = "quotations/dashboard.html"

    def get(self, request):
        return render(request, self.template_name, get_dashboard_context(request.GET))


class QuotationCreateView(LoginRequiredMixin, FormView):
    login_url = "login"
    template_name = "quotations/create.html"
    form_class = QuotationCreateForm

    def form_valid(self, form):
        quotation = create_quotation(**form.cleaned_data)
        messages.success(self.request, f"Utworzono wycenę #{quotation.pk} dla firmy {quotation.customer.name}.")
        return redirect("quotations:detail", quotation_id=quotation.pk)


class QuotationDetailView(LoginRequiredMixin, View):
    login_url = "login"
    template_name = "quotations/detail.html"

    def get(self, request, quotation_id):
        quotation = get_quotation(quotation_id)
        formset = get_item_formset(quotation)
        return render(request, self.template_name, get_detail_context(quotation, formset))

    def post(self, request, quotation_id):
        quotation = get_quotation(quotation_id)
        formset = get_item_formset(quotation, request.POST)
        if formset.is_valid():
            save_quotation_items(formset)
            messages.success(request, "Zapisano pozycje wyceny.")
            return redirect("quotations:detail", quotation_id=quotation.pk)
        return render(request, self.template_name, get_detail_context(quotation, formset))


class QuotationMaterialSearchView(LoginRequiredMixin, View):
    login_url = "login"

    def get(self, request):
        return JsonResponse(search_materials(request.GET))
