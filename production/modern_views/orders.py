from django.contrib.auth.mixins import (
    PermissionRequiredMixin,
)
from django.shortcuts import (
    redirect,
    render,
)
from django.urls import (
    reverse,
    reverse_lazy,
)
from django.views import View

from production.forms import (
    ProductionUnitForm,
)
from production.services.orders import (
    get_production_order_detail_context,
)


class ProductionOrderDetailView(
    PermissionRequiredMixin,
    View,
):
    permission_required = (
        "production.view_productionorder"
    )

    login_url = reverse_lazy(
        "login"
    )

    template_name = (
        "production/orders/detail.html"
    )

    def get(
        self,
        request,
        production_order_id,
    ):
        context = (
            get_production_order_detail_context(
                production_order_id=
                    production_order_id,
            )
        )

        return render(
            request,
            self.template_name,
            context,
        )

    def post(
        self,
        request,
        production_order_id,
    ):
        if not request.user.has_perm(
            "production.add_productionunit"
        ):
            from django.core.exceptions import (
                PermissionDenied,
            )

            raise PermissionDenied

        context = (
            get_production_order_detail_context(
                production_order_id=
                    production_order_id,
            )
        )

        production_order = (
            context["production_order"]
        )

        form = ProductionUnitForm(
            request.POST
        )

        if form.is_valid():

            unit = form.save(
                commit=False
            )

            unit.production_order = (
                production_order
            )

            unit.save()

            form.save_m2m()

            return redirect(
                "production-details",
                production_order_id=
                    production_order.id,
            )

        context["form"] = form

        return render(
            request,
            self.template_name,
            context,
        )