from django.contrib.auth.mixins import (
    PermissionRequiredMixin,
)
from django.shortcuts import render
from django.views import View

from warehousemanager.services.punches import (
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