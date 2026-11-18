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

from .services.processes import (
    get_process_settings_context,
    save_process_settings,
)

from urllib.parse import urlencode

from django.urls import reverse

from .services.settings import (
    get_sheet_settings_context,
    save_sheet_settings,
)

from .services.sheet import calculate_sheet


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


class QuotationSettingsView(LoginRequiredMixin, View):
    login_url = "login"
    template_name = "quotations/settings.html"

    def get(self, request):
        context = get_sheet_settings_context(
            request.GET,
        )

        return render(
            request,
            self.template_name,
            context,
        )

    def post(self, request):
        context = get_sheet_settings_context(
            request.POST,
            data=request.POST,
        )

        if save_sheet_settings(context):
            messages.success(
                request,
                "Zapisano dodatki dla wybranego FEFCO.",
            )

            query = urlencode({
                "packaging_type": (
                    context["packaging_type"].pk
                ),
            })

            return redirect(
                f"{reverse('quotations:settings')}?{query}"
            )

        return render(
            request,
            self.template_name,
            context,
        )


class QuotationSheetCalculationView(LoginRequiredMixin, View):
    login_url = "login"

    def get(self, request):
        return JsonResponse(
            calculate_sheet(request.GET)
        )


class QuotationProcessSettingsView(LoginRequiredMixin, View):
    login_url = "login"
    template_name = "quotations/process_settings.html"

    def get(self, request):
        return render(
            request,
            self.template_name,
            get_process_settings_context(),
        )

    def post(self, request):
        context = get_process_settings_context(
            data=request.POST,
        )

        if save_process_settings(context):
            messages.success(
                request,
                "Zapisano ustawienia rotacji bez nadruku.",
            )

            return redirect(
                "quotations:process_settings"
            )

        return render(
            request,
            self.template_name,
            context,
        )
