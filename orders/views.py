from decimal import Decimal, ROUND_CEILING

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

from .services.edi.jassboard_orders import (
    build_jassboard_preview,
    is_jassboard_provider,
    send_jassboard_purchase,
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

        # ========================================================
        # MATERIAL REQUIREMENT TEMPLATE FROM PRODUCT
        # ========================================================

        product_requirement_template = None

        if not requirement and order.product_id:
            product_requirement_template = getattr(
                order.product,
                "material_requirement_template",
                None,
            )

        # ========================================================
        # EXISTING REQUIREMENT
        # ========================================================

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

        # ========================================================
        # REQUIREMENT FORM
        # ========================================================

        if requirement_form is None:

            initial = {}

            if product_requirement_template:
                pieces_per_sheet = (
                        product_requirement_template.pieces_per_sheet
                        or Decimal("1")
                )

                required_sheet_quantity = int(
                    (
                            Decimal(order.quantity)
                            / Decimal(pieces_per_sheet)
                    ).quantize(
                        Decimal("1"),
                        rounding=ROUND_CEILING,
                    )
                )

                initial = {
                    "sheet_length":
                        product_requirement_template.sheet_length,

                    "sheet_width":
                        product_requirement_template.sheet_width,

                    "pieces_per_sheet":
                        product_requirement_template.pieces_per_sheet,

                    "required_sheet_quantity":
                        required_sheet_quantity,

                    "layers":
                        product_requirement_template.layers,

                    "flute":
                        product_requirement_template.flute,

                    "min_gsm":
                        product_requirement_template.min_gsm,

                    "min_ect":
                        product_requirement_template.min_ect,

                    "cover":
                        product_requirement_template.cover,

                    "scores":
                        product_requirement_template.scores,

                    "notes":
                        product_requirement_template.notes,
                }

            requirement_form = MaterialRequirementForm(
                initial=initial
            )

        return {
            "order":
                order,

            "requirement":
                requirement,

            "requirement_form":
                requirement_form,

            "offers":
                offers,

            "purchase_allocation":
                purchase_allocation,

            "requirement_scores_display":
                requirement_scores_display,

            "purchase_scores_display":
                purchase_scores_display,

            "product_requirement_template":
                product_requirement_template,
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
                # JASSBOARD
                # ============================================

                if is_jassboard_provider(
                        provider
                ):

                    # ----------------------------------------
                    # PREVIEW JSON
                    # ----------------------------------------

                    if edi_action == "preview":
                        payload = (
                            build_jassboard_preview(
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

                        import json

                        return HttpResponse(
                            json.dumps(
                                payload,
                                indent=4,
                                ensure_ascii=False,
                            ),
                            content_type=(
                                "application/json; "
                                "charset=utf-8"
                            ),
                        )

                    # ----------------------------------------
                    # SEND JASSBOARD
                    # ----------------------------------------

                    if edi_action == "send":
                        api_result = (
                            send_jassboard_purchase(
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
                        # SAVE LOCALLY ONLY AFTER API SUCCESS
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
                                "Zamówienie zostało wysłane "
                                "do JASS i zapisane w systemie "
                                f"jako {cardboard_order.number}."
                            ),
                        )

                        return redirect(
                            "orders:customer_order_detail",
                            pk=order.pk,
                        )

                    raise ValidationError(
                        (
                            "Nie wybrano akcji "
                            "dla zamówienia JASS."
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


########### TEMPORARY

import tempfile
from pathlib import Path

from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.views import View

from .forms import ProductMaterialRequirementImportForm
from .services.material_requirement_import import *


class ProductMaterialRequirementImportView(
    LoginRequiredMixin,
    View,
):
    login_url = "login"

    template_name = (
        "orders/"
        "product_material_requirement_import.html"
    )

    def get(self, request):
        form = ProductMaterialRequirementImportForm()

        return render(
            request,
            self.template_name,
            {
                "form": form,
                "result": None,
            },
        )

    def post(self, request):

        action = request.POST.get("action")

        form = ProductMaterialRequirementImportForm(
            request.POST,
            request.FILES,
        )

        if not form.is_valid():
            return render(
                request,
                self.template_name,
                {
                    "form": form,
                    "result": None,
                },
            )

        uploaded_files = form.cleaned_data["files"]

        temp_paths = []

        try:
            # -----------------------------------------
            # Zapis uploadowanych plików tymczasowo
            # -----------------------------------------

            for uploaded_file in uploaded_files:

                suffix = (
                    Path(uploaded_file.name).suffix
                    or ".txt"
                )

                temp_file = tempfile.NamedTemporaryFile(
                    mode="wb",
                    delete=False,
                    suffix=suffix,
                )

                try:
                    for chunk in uploaded_file.chunks():
                        temp_file.write(chunk)

                finally:
                    temp_file.close()

                temp_paths.append(
                    temp_file.name
                )

            # -----------------------------------------
            # TYLKO ANALIZA
            # -----------------------------------------

            result = analyze_files(
                temp_paths
            )

            if action == "save_one":

                product_id = request.POST.get(
                    "product_id"
                )

                row_to_save = None

                for row in result["ready"]:

                    if str(
                            row["product"].id
                    ) == str(
                        product_id
                    ):
                        row_to_save = row
                        break

                if not row_to_save:
                    raise ValueError(
                        "Nie znaleziono produktu w wyniku analizy."
                    )

                requirement = (
                    create_requirement_from_analysis_row(
                        row_to_save
                    )
                )

                messages.success(
                    request,
                    (
                        "Zapisano konfigurację dla: "
                        f"{requirement.product}"
                    ),
                )

        except Exception as exc:

            return render(
                request,
                self.template_name,
                {
                    "form": form,
                    "result": None,
                    "import_error": str(exc),
                },
            )

        finally:
            # -----------------------------------------
            # Usunięcie plików tymczasowych
            # -----------------------------------------

            for temp_path in temp_paths:

                try:
                    Path(
                        temp_path
                    ).unlink(
                        missing_ok=True
                    )

                except Exception:
                    pass

        return render(
            request,
            self.template_name,
            {
                "form": form,
                "result": result,
            },
        )


import shutil
import uuid

from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.shortcuts import render
from django.views import View

from orders.forms import (
    ProductMaterialRequirementImportForm,
)

from orders.services.material_requirement_import import (
    analyze_files,
    get_complete_import_rows,
    import_complete_rows,
)


class ProductMaterialRequirementBulkImportView(
    LoginRequiredMixin,
    View,
):
    login_url = "login"

    template_name = (
        "orders/"
        "product_material_requirement_bulk_import.html"
    )

    session_key = (
        "product_material_requirement_import_token"
    )

    def get(self, request):

        form = (
            ProductMaterialRequirementImportForm()
        )

        return render(
            request,
            self.template_name,
            {
                "form": form,
            },
        )

    def get_import_root(self):

        root = (
            Path(settings.MEDIA_ROOT)
            / "temp"
            / "material_requirement_import"
        )

        root.mkdir(
            parents=True,
            exist_ok=True,
        )

        return root

    def get_token_directory(
        self,
        token,
    ):

        return (
            self.get_import_root()
            / token
        )

    def clear_previous_files(
        self,
        request,
    ):

        old_token = request.session.get(
            self.session_key
        )

        if not old_token:
            return

        directory = (
            self.get_token_directory(
                old_token
            )
        )

        if directory.exists():

            shutil.rmtree(
                directory,
                ignore_errors=True,
            )

        request.session.pop(
            self.session_key,
            None,
        )

    def save_uploaded_files(
        self,
        request,
        uploaded_files,
    ):

        self.clear_previous_files(
            request
        )

        token = uuid.uuid4().hex

        directory = (
            self.get_token_directory(
                token
            )
        )

        directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        saved_paths = []

        for number, uploaded_file in enumerate(
            uploaded_files,
            start=1,
        ):

            original_name = Path(
                uploaded_file.name
            ).name

            filename = (
                f"{number:02d}_"
                f"{original_name}"
            )

            destination = (
                directory
                / filename
            )

            with destination.open(
                "wb"
            ) as target:

                for chunk in (
                    uploaded_file.chunks()
                ):
                    target.write(
                        chunk
                    )

            saved_paths.append(
                str(destination)
            )

        request.session[
            self.session_key
        ] = token

        request.session.modified = True

        return saved_paths

    def get_saved_paths(
        self,
        request,
    ):

        token = request.session.get(
            self.session_key
        )

        if not token:
            return []

        directory = (
            self.get_token_directory(
                token
            )
        )

        if not directory.exists():
            return []

        return [
            str(path)
            for path in sorted(
                directory.glob("*.txt")
            )
        ]

    def post(self, request):

        action = request.POST.get(
            "action",
            "analyze",
        )

        # ==========================================
        # ANALIZA
        # ==========================================

        if action == "analyze":

            form = (
                ProductMaterialRequirementImportForm(
                    request.POST,
                    request.FILES,
                )
            )

            if not form.is_valid():

                return render(
                    request,
                    self.template_name,
                    {
                        "form": form,
                    },
                )

            uploaded_files = (
                form.cleaned_data[
                    "files"
                ]
            )

            try:

                paths = (
                    self.save_uploaded_files(
                        request,
                        uploaded_files,
                    )
                )

                result = analyze_files(
                    paths
                )

                complete_rows = (
                    get_complete_import_rows(
                        result
                    )
                )

            except Exception as exc:

                messages.error(
                    request,
                    (
                        "Błąd analizy: "
                        f"{exc}"
                    ),
                )

                return render(
                    request,
                    self.template_name,
                    {
                        "form": form,
                    },
                )

            return render(
                request,
                self.template_name,
                {
                    "form": form,

                    "result":
                        result,

                    "complete_rows":
                        complete_rows,

                    "complete_count":
                        len(
                            complete_rows
                        ),
                },
            )

        # ==========================================
        # IMPORT WSZYSTKICH KOMPLETNYCH
        # ==========================================

        if action == "import_all":

            paths = self.get_saved_paths(
                request
            )

            if not paths:

                messages.error(
                    request,
                    (
                        "Brak plików do importu. "
                        "Wykonaj analizę ponownie."
                    ),
                )

                return redirect(
                    request.path
                )

            try:

                # Analizujemy jeszcze raz
                # bezpośrednio przed zapisem.
                #
                # Dzięki temu nie ufamy danym
                # przesłanym przez HTML.

                result = analyze_files(
                    paths
                )

                import_result = (
                    import_complete_rows(
                        result
                    )
                )

            except Exception as exc:

                messages.error(
                    request,
                    (
                        "Import nie został wykonany: "
                        f"{exc}"
                    ),
                )

                return redirect(
                    request.path
                )

            created = (
                import_result[
                    "created_count"
                ]
            )

            skipped = (
                import_result[
                    "skipped_count"
                ]
            )

            # Po poprawnym imporcie
            # usuwamy tymczasowe pliki.

            self.clear_previous_files(
                request
            )

            messages.success(
                request,
                (
                    f"Import zakończony. "
                    f"Utworzono: {created}. "
                    f"Pominięto: {skipped}."
                ),
            )

            return redirect(
                request.path
            )

        messages.error(
            request,
            "Nieznana akcja.",
        )

        return redirect(
            request.path
        )