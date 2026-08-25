from django.urls import reverse, reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    UpdateView,
)

import datetime

from warehousemanager.forms import PolymerForm, PolymerServiceForm

from warehousemanager.models import Photopolymer, PhotopolymerService

from django.contrib.auth.mixins import (
    PermissionRequiredMixin,
)
from django.shortcuts import render
from django.views import View

from warehousemanager.functions import (
    visit_counter,
)
from warehousemanager.services.polymers import (
    get_polymer_list_context,
    get_polymer_detail_context,
)


class PolymerListView(
    PermissionRequiredMixin,
    View,
):
    permission_required = (
        "warehousemanager.view_photopolymer"
    )

    template_name = "polymers/list.html"

    def get(self, request):
        visit_counter(
            request.user,
            "polymer_list",
        )

        context = get_polymer_list_context(
            search=request.GET.get(
                "q",
                "",
            ),
            customer_id=request.GET.get(
                "customer",
                "",
            ),
            producer=request.GET.get(
                "producer",
                "",
            ),
            status=request.GET.get(
                "status",
                "",
            ),
        )

        return render(
            request,
            self.template_name,
            context,
        )


class PolymerDetailView(
    PermissionRequiredMixin,
    View,
):
    permission_required = (
        "warehousemanager.view_photopolymer"
    )

    template_name = "polymers/detail.html"

    def get(
        self,
        request,
        polymer_id,
    ):
        context = (
            get_polymer_detail_context(
                polymer_id=polymer_id,
            )
        )

        return render(
            request,
            self.template_name,
            context,
        )


POLYMER_FIELDS = [
    "producer",
    "identification_number",
    "identification_letter",
    "customer",
    "name",
    "dimensions",
    "colors",
    "delivery_date",
    "project",
    "link",
    "active",
]


class PolymerCreateView(
    PermissionRequiredMixin,
    CreateView,
):
    permission_required = (
        "warehousemanager.add_photopolymer"
    )

    model = Photopolymer

    form_class = PolymerForm

    template_name = "polymers/form.html"

    def get_success_url(self):
        return reverse(
            "polymer-details",
            kwargs={
                "polymer_id": self.object.pk,
            },
        )


class PolymerUpdateView(
    PermissionRequiredMixin,
    UpdateView,
):
    permission_required = (
        "warehousemanager.change_photopolymer"
    )

    model = Photopolymer

    form_class = PolymerForm

    template_name = "polymers/form.html"

    def get_success_url(self):
        return reverse(
            "polymer-details",
            kwargs={
                "polymer_id": self.object.pk,
            },
        )


class PolymerDeleteView(
    PermissionRequiredMixin,
    DeleteView,
):
    permission_required = (
        "warehousemanager.delete_photopolymer"
    )

    model = Photopolymer

    template_name = (
        "polymers/confirm_delete.html"
    )

    success_url = reverse_lazy(
        "polymers"
    )


class PolymerServiceCreateView(
    PermissionRequiredMixin,
    CreateView,
):
    permission_required = (
        "warehousemanager.add_photopolymerservice"
    )

    form_class = PolymerServiceForm

    template_name = (
        "polymers/service_form.html"
    )

    def get_initial(self):
        initial = super().get_initial()

        polymer_id = self.request.GET.get(
            "polymer"
        )

        if polymer_id:
            initial["photopolymer"] = (
                polymer_id
            )

        initial["send_date"] = (
            datetime.date.today()
        )

        return initial

    def get_success_url(self):
        return reverse(
            "polymer-details",
            kwargs={
                "polymer_id":
                    self.object.photopolymer_id,
            },
        )


class PolymerServiceUpdateView(
    PermissionRequiredMixin,
    UpdateView,
):
    permission_required = (
        "warehousemanager.change_photopolymerservice"
    )

    model = PhotopolymerService

    form_class = PolymerServiceForm

    template_name = (
        "polymers/service_form.html"
    )

    def get_success_url(self):
        return reverse(
            "polymer-details",
            kwargs={
                "polymer_id":
                    self.object.photopolymer_id,
            },
        )


class PolymerServiceDeleteView(
    PermissionRequiredMixin,
    DeleteView,
):
    permission_required = (
        "warehousemanager.delete_photopolymerservice"
    )

    model = PhotopolymerService

    template_name = (
        "polymers/service_confirm_delete.html"
    )

    def get_success_url(self):
        return reverse(
            "polymer-details",
            kwargs={
                "polymer_id":
                    self.object.photopolymer_id,
            },
        )