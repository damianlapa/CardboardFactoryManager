from django.contrib import messages
from django.contrib.auth.mixins import (
    PermissionRequiredMixin,
)
from django.shortcuts import redirect, render
from django.views import View

from warehousemanager.services.colors import (
    get_bucket_details,
    get_color_details,
    get_color_list,
    register_bucket_usage,
)


class ModernColorListView(
    PermissionRequiredMixin,
    View,
):
    permission_required = (
        "warehousemanager.view_color"
    )

    template_name = (
        "modern/colors/list.html"
    )

    def get(self, request):
        return render(
            request,
            self.template_name,
            {
                "colors": get_color_list(),
            },
        )


class ModernColorDetailView(
    PermissionRequiredMixin,
    View,
):
    permission_required = (
        "warehousemanager.view_color"
    )

    template_name = (
        "modern/colors/detail.html"
    )

    def get(self, request, color_id):
        return render(
            request,
            self.template_name,
            get_color_details(color_id),
        )


class ModernBucketDetailView(
    PermissionRequiredMixin,
    View,
):
    permission_required = (
        "warehousemanager.view_color"
    )

    template_name = (
        "modern/colors/bucket_detail.html"
    )

    def get(self, request, bucket_id):
        return render(
            request,
            self.template_name,
            get_bucket_details(bucket_id),
        )

    def post(self, request, bucket_id):
        try:
            register_bucket_usage(
                bucket_id=bucket_id,
                usage_date=request.POST.get(
                    "usage_date"
                ),
                weight_before=request.POST.get(
                    "weight_before"
                ),
                weight_after=request.POST.get(
                    "weight_after"
                ),
            )

        except ValueError as error:
            messages.error(
                request,
                str(error),
            )

        else:
            messages.success(
                request,
                "Zużycie farby zostało zapisane.",
            )

        return redirect(
            "bucket-details",
            bucket_id=bucket_id,
        )