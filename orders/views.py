from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)
from django.views import View

from .forms import (
    CustomerOrderForm,
    MaterialPurchaseForm,
    MaterialRequirementForm,
)

from .models import (
    CustomerOrder,
)

from .services.customer_order_list import (
    get_customer_order_list_context,
)

from .services.customer_orders import (
    create_customer_order,
    create_material_requirement,
)

from .services.material_purchase import (
    create_material_purchase,
    get_material_purchase_offer,
    get_material_purchase_offers,
)

from .services.scores import (
    scores_as_segments,
    order_item_scores_as_segments,
)

from .services.edi.aquila_orders import (
    build_aquila_xml_preview,
    is_aquila_provider,
    send_aquila_purchase,
)


# ============================================================
# CUSTOMER ORDER CREATE
# ============================================================


class CustomerOrderCreateView(
    LoginRequiredMixin,
    View,
):
    login_url = "login"

    template_name = (
        "orders/customer_order_form.html"
    )

    def get(self, request):

        return render(
            request,
            self.template_name,
            {
                "form": CustomerOrderForm(),
            },
        )

    def post(self, request):

        form = CustomerOrderForm(
            request.POST
        )

        if not form.is_valid():

            return render(
                request,
                self.template_name,
                {
                    "form": form,
                },
            )

        order = create_customer_order(
            form=form,
            user=request.user,
        )

        messages.success(
            request,
            (
                f"Utworzono zamówienie "
                f"{order.order_number}."
            ),
        )

        return redirect(
            "orders:customer_order_detail",
            pk=order.pk,
        )


# ============================================================
# CUSTOMER ORDER DETAIL
# ============================================================


class CustomerOrderDetailView(
    LoginRequiredMixin,
    View,
):
    login_url = "login"

    template_name = (
        "orders/customer_order_detail.html"
    )

    # ========================================================
    # QUERY
    # ========================================================

    def get_order(
        self,
        pk,
    ):
        return get_object_or_404(
            CustomerOrder.objects
            .select_related(
                "customer",
                "product",
                "created_by",
            )
            .prefetch_related(
                "material_requirements",
                "material_requirements__scores",
                "material_requirements__allocations",
                (
                    "material_requirements__"
                    "allocations__"
                    "cardboard_order_item"
                ),
                (
                    "material_requirements__"
                    "allocations__"
                    "cardboard_order_item__"
                    "order"
                ),
                (
                    "material_requirements__"
                    "allocations__"
                    "cardboard_order_item__"
                    "cardboard"
                ),
                (
                    "material_requirements__"
                    "allocations__"
                    "cardboard_order_item__"
                    "scores"
                ),
            ),
            pk=pk,
        )

    # ========================================================
    # CONTEXT
    # ========================================================

    def get_context(
        self,
        *,
        order,
        requirement_form=None,
    ):
        requirement = (
            order
            .material_requirements
            .first()
        )

        offers = []

        purchase_allocation = None

        requirement_scores_display = ""
        purchase_scores_display = ""

        if requirement:

            requirement_scores_display = (
                scores_as_segments(
                    requirement
                )
            )

            purchase_allocation = (
                requirement
                .allocations
                .filter(
                    source="PURCHASE"
                )
                .select_related(
                    "cardboard_order_item",
                    "cardboard_order_item__order",
                    "cardboard_order_item__cardboard",
                )
                .first()
            )

            if purchase_allocation:

                purchase_scores_display = (
                    order_item_scores_as_segments(
                        purchase_allocation
                        .cardboard_order_item
                    )
                )

            else:

                offers = (
                    get_material_purchase_offers(
                        requirement
                    )
                )

        return {
            "order":
                order,

            "requirement":
                requirement,

            "requirement_form": (
                requirement_form
                or MaterialRequirementForm()
            ),

            "offers":
                offers,

            "purchase_allocation":
                purchase_allocation,

            "requirement_scores_display":
                requirement_scores_display,

            "purchase_scores_display":
                purchase_scores_display,
        }

    # ========================================================
    # GET
    # ========================================================

    def get(
        self,
        request,
        pk,
    ):
        order = self.get_order(
            pk
        )

        return render(
            request,
            self.template_name,
            self.get_context(
                order=order
            ),
        )

    # ========================================================
    # POST
    # ========================================================

    def post(
        self,
        request,
        pk,
    ):
        order = self.get_order(
            pk
        )

        action = request.POST.get(
            "action"
        )

        # ====================================================
        # CREATE MATERIAL REQUIREMENT
        # ====================================================

        if action == "add_requirement":

            form = MaterialRequirementForm(
                request.POST
            )

            if form.is_valid():

                create_material_requirement(
                    customer_order=order,
                    form=form,
                )

                messages.success(
                    request,
                    (
                        "Wymagania materiałowe "
                        "zostały zapisane."
                    ),
                )

                return redirect(
                    "orders:customer_order_detail",
                    pk=order.pk,
                )

            return render(
                request,
                self.template_name,
                self.get_context(
                    order=order,
                    requirement_form=form,
                ),
            )

        # ====================================================
        # PURCHASE MATERIAL
        # ====================================================

        if action == "purchase_material":

            form = MaterialPurchaseForm(
                request.POST
            )

            if not form.is_valid():

                messages.error(
                    request,
                    (
                        "Formularz zamówienia "
                        "materiału zawiera błędy."
                    ),
                )

                return redirect(
                    "orders:customer_order_detail",
                    pk=order.pk,
                )

            requirement = get_object_or_404(
                order.material_requirements,
                pk=form.cleaned_data[
                    "requirement_id"
                ],
            )

            try:

                # ============================================
                # SELECT OFFER AGAIN ON BACKEND
                # ============================================

                offer = (
                    get_material_purchase_offer(
                        requirement,
                        form.cleaned_data[
                            "price_list_item_id"
                        ],
                    )
                )

                provider = offer["provider"]

                edi_action = request.POST.get(
                    "edi_action"
                )

                # ============================================
                # AQUILA
                # ============================================

                if is_aquila_provider(
                    provider
                ):

                    # ----------------------------------------
                    # PREVIEW XML
                    # ----------------------------------------

                    if edi_action == "preview":

                        xml_body = (
                            build_aquila_xml_preview(
                                requirement=requirement,
                                offer=offer,

                                order_number=(
                                    form.cleaned_data[
                                        "order_number"
                                    ]
                                ),

                                delivery_date=(
                                    form.cleaned_data[
                                        "delivery_date"
                                    ]
                                ),
                            )
                        )

                        return HttpResponse(
                            xml_body,
                            content_type=(
                                "application/xml; "
                                "charset=utf-8"
                            ),
                        )

                    # ----------------------------------------
                    # SEND EDI
                    # ----------------------------------------

                    if edi_action == "send":

                        edi_result = (
                            send_aquila_purchase(
                                requirement=requirement,
                                offer=offer,

                                order_number=(
                                    form.cleaned_data[
                                        "order_number"
                                    ]
                                ),

                                delivery_date=(
                                    form.cleaned_data[
                                        "delivery_date"
                                    ]
                                ),
                            )
                        )

                        # ------------------------------------
                        # SAVE LOCALLY ONLY AFTER EDI SUCCESS
                        # ------------------------------------

                        cardboard_order = (
                            create_material_purchase(
                                requirement=requirement,
                                offer=offer,

                                order_number=(
                                    form.cleaned_data[
                                        "order_number"
                                    ]
                                ),

                                order_date=(
                                    form.cleaned_data[
                                        "order_date"
                                    ]
                                ),

                                delivery_date=(
                                    form.cleaned_data[
                                        "delivery_date"
                                    ]
                                ),

                                user=request.user,
                            )
                        )

                        messages.success(
                            request,
                            (
                                "Zamówienie zostało "
                                "wysłane do Aquila przez EDI "
                                "i zapisane w systemie jako "
                                f"{cardboard_order.number}. "
                                f"HTTP "
                                f"{edi_result['status_code']}."
                            ),
                        )

                        return redirect(
                            "orders:customer_order_detail",
                            pk=order.pk,
                        )

                    raise ValidationError(
                        (
                            "Nie wybrano akcji "
                            "dla zamówienia Aquila."
                        )
                    )

                # ============================================
                # OTHER PROVIDERS
                # ============================================

                cardboard_order = (
                    create_material_purchase(
                        requirement=requirement,
                        offer=offer,

                        order_number=(
                            form.cleaned_data[
                                "order_number"
                            ]
                        ),

                        order_date=(
                            form.cleaned_data[
                                "order_date"
                            ]
                        ),

                        delivery_date=(
                            form.cleaned_data[
                                "delivery_date"
                            ]
                        ),

                        user=request.user,
                    )
                )

            except ValidationError as e:

                messages.error(
                    request,
                    (
                        e.messages[0]
                        if e.messages
                        else str(e)
                    ),
                )

                return redirect(
                    "orders:customer_order_detail",
                    pk=order.pk,
                )

            except Exception as e:

                messages.error(
                    request,
                    (
                        "Nie udało się zrealizować "
                        f"zamówienia materiału: {e}"
                    ),
                )

                return redirect(
                    "orders:customer_order_detail",
                    pk=order.pk,
                )

            # =================================================
            # SUCCESS - NORMAL PROVIDER
            # =================================================

            messages.success(
                request,
                (
                    "Utworzono zamówienie "
                    f"materiału "
                    f"{cardboard_order.number}."
                ),
            )

            return redirect(
                "orders:customer_order_detail",
                pk=order.pk,
            )

        return redirect(
            "orders:customer_order_detail",
            pk=order.pk,
        )


# ============================================================
# CUSTOMER ORDER LIST
# ============================================================


class CustomerOrderListView(
    LoginRequiredMixin,
    View,
):
    login_url = "login"

    template_name = (
        "orders/customer_order_list.html"
    )

    def get(
        self,
        request,
    ):
        context = (
            get_customer_order_list_context(
                request
            )
        )

        context["create_form"] = (
            CustomerOrderForm()
        )

        return render(
            request,
            self.template_name,
            context,
        )

    def post(
        self,
        request,
    ):
        form = CustomerOrderForm(
            request.POST
        )

        if form.is_valid():

            order = create_customer_order(
                form=form,
                user=request.user,
            )

            messages.success(
                request,
                (
                    f"Utworzono zamówienie "
                    f"{order.order_number}."
                ),
            )

            return redirect(
                "orders:customer_order_detail",
                pk=order.pk,
            )

        context = (
            get_customer_order_list_context(
                request
            )
        )

        context["create_form"] = form

        context[
            "open_create_modal"
        ] = True

        return render(
            request,
            self.template_name,
            context,
        )