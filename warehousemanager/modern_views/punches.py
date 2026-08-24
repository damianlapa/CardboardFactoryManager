from django.contrib import messages
from django.contrib.auth.mixins import (
    PermissionRequiredMixin,
)
from django.shortcuts import redirect, render
from django.views import View

from warehousemanager.forms import PunchForm
from warehousemanager.services.punches import (
    delete_punch,
    get_punch,
    get_punch_details,
    get_punch_list,
    get_punch_types,
)


class ModernPunchListView(
    PermissionRequiredMixin,
    View,
):
    permission_required = (
        "warehousemanager.view_punch"
    )

    template_name = (
        "modern/punches/list.html"
    )

    def get(self, request):
        include_inactive = (
            request.GET.get("all") == "1"
        )

        context = {
            "punches": get_punch_list(
                include_inactive=include_inactive,
            ),
            "punch_types": get_punch_types(),
            "include_inactive": include_inactive,
        }

        return render(
            request,
            self.template_name,
            context,
        )


class ModernPunchDetailView(
    PermissionRequiredMixin,
    View,
):
    permission_required = (
        "warehousemanager.view_punch"
    )

    template_name = (
        "modern/punches/detail.html"
    )

    def get(self, request, punch_id):
        context = get_punch_details(
            punch_id=punch_id,
        )

        return render(
            request,
            self.template_name,
            context,
        )


class ModernPunchCreateView(
    PermissionRequiredMixin,
    View,
):
    permission_required = (
        "warehousemanager.add_punch"
    )

    template_name = (
        "modern/punches/form.html"
    )

    def get(self, request):
        form = PunchForm()

        return render(
            request,
            self.template_name,
            {
                "form": form,
                "is_edit": False,
            },
        )

    def post(self, request):
        form = PunchForm(
            request.POST,
        )

        if form.is_valid():
            punch = form.save()

            messages.success(
                request,
                "Wykrojnik został dodany.",
            )

            return redirect(
                "punch-details",
                punch_id=punch.id,
            )

        return render(
            request,
            self.template_name,
            {
                "form": form,
                "is_edit": False,
            },
        )


class ModernPunchUpdateView(
    PermissionRequiredMixin,
    View,
):
    permission_required = (
        "warehousemanager.change_punch"
    )

    template_name = (
        "modern/punches/form.html"
    )

    def get(self, request, punch_id):
        punch = get_punch(
            punch_id,
        )

        form = PunchForm(
            instance=punch,
        )

        return render(
            request,
            self.template_name,
            {
                "form": form,
                "punch": punch,
                "is_edit": True,
            },
        )

    def post(self, request, punch_id):
        punch = get_punch(
            punch_id,
        )

        form = PunchForm(
            request.POST,
            instance=punch,
        )

        if form.is_valid():
            punch = form.save()

            messages.success(
                request,
                "Zmiany zostały zapisane.",
            )

            return redirect(
                "punch-details",
                punch_id=punch.id,
            )

        return render(
            request,
            self.template_name,
            {
                "form": form,
                "punch": punch,
                "is_edit": True,
            },
        )


class ModernPunchDeleteView(
    PermissionRequiredMixin,
    View,
):
    permission_required = (
        "warehousemanager.delete_punch"
    )

    def post(self, request, punch_id):
        punch = get_punch(
            punch_id,
        )

        if not delete_punch(punch):
            messages.error(
                request,
                (
                    "Nie można usunąć wykrojnika, "
                    "ponieważ posiada historię produkcji."
                ),
            )

            return redirect(
                "punch-details",
                punch_id=punch.id,
            )

        messages.success(
            request,
            "Wykrojnik został usunięty.",
        )

        return redirect("punches")