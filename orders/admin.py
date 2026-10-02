from django.contrib import admin, messages
from django.shortcuts import render, redirect
from django.urls import path

from .models import (
    CustomerOrder,
    MaterialRequirement,
    CardboardGrade,
    CardboardPriceList,
    CardboardPriceListItem,
    CardboardPriceTier,
    CardboardOrder,
    CardboardOrderItem,
    MaterialAllocation,
    MaterialRequirementScore,
    ProductMaterialRequirement,
    CustomerOrderSequence
)


from .forms import CardboardPriceListImportForm
from .services.price_list_import import import_cardboard_price_list


# ============================================================
# CUSTOMER ORDER
# ============================================================


class MaterialRequirementInline(admin.TabularInline):
    model = MaterialRequirement
    extra = 0

    fields = (
        "sheet_length",
        "sheet_width",
        "pieces_per_sheet",
        "required_sheet_quantity",
        "layers",
        "flute",
        "min_gsm",
        "min_ect",
        "cover",
    )


@admin.register(CustomerOrder)
class CustomerOrderAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "display_order_number",
        "customer",
        "product",
        "quantity",
        "order_date",
        "requested_delivery_date",
        "status",
        "created_at",
    )

    list_filter = (
        "status",
        "order_date",
        "requested_delivery_date",
        "created_at",
        "year",
    )

    search_fields = (
        "=number",
        "=year",
        "customer__name",
        "product__name",
        "notes",
    )

    autocomplete_fields = (
        "customer",
        "product",
    )

    readonly_fields = (
        "display_order_number",
        "created_at",
        "created_by",
        "updated_at",
        "updated_by",
    )

    inlines = [
        MaterialRequirementInline,
    ]

    fieldsets = (
        (
            "Zamówienie klienta",
            {
                "fields": (
                    "display_order_number",
                    "customer",
                    "product",
                    "quantity",
                )
            },
        ),
        (
            "Terminy",
            {
                "fields": (
                    "order_date",
                    "requested_delivery_date",
                )
            },
        ),
        (
            "Status",
            {
                "fields": (
                    "status",
                )
            },
        ),
        (
            "Uwagi",
            {
                "fields": (
                    "notes",
                )
            },
        ),
        (
            "System",
            {
                "classes": ("collapse",),
                "fields": (
                    "created_at",
                    "created_by",
                    "updated_at",
                    "updated_by",
                    "legacy_production_order",
                ),
            },
        ),
    )

    @admin.display(
        description="Numer",
        ordering="number",
    )
    def display_order_number(self, obj):
        if not obj or not obj.pk:
            return "nadawany automatycznie"

        return obj.order_number

    def save_model(
        self,
        request,
        obj,
        form,
        change,
    ):
        if not obj.created_by_id:
            obj.created_by = request.user

        obj.updated_by = request.user

        super().save_model(
            request,
            obj,
            form,
            change,
        )


# ============================================================
# MATERIAL REQUIREMENT
# ============================================================


class MaterialAllocationInline(admin.TabularInline):
    model = MaterialAllocation
    extra = 0

    fields = (
        "source",
        "quantity",
        "stock_supply",
        "cardboard_order_item",
        "created_by",
    )

    autocomplete_fields = (
        "stock_supply",
        "cardboard_order_item",
        "created_by",
    )


class MaterialRequirementScoreInline(admin.TabularInline):
    model = MaterialRequirementScore
    extra = 1

    fields = (
        "position_mm",
    )

    ordering = (
        "position_mm",
    )


@admin.register(MaterialRequirement)
class MaterialRequirementAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "customer_order",
        "sheet_dimensions",
        "scores_display",
        "required_sheet_quantity",
        "pieces_per_sheet",
        "layers",
        "flute",
        "min_gsm",
        "min_ect",
        "cover",
        "required_area_display",
    )

    list_filter = (
        "layers",
        "flute",
        "cover",
    )

    search_fields = (
        "=customer_order__number",
        "=customer_order__year",
        "customer_order__customer__name",
        "customer_order__product__name",
    )

    autocomplete_fields = (
        "customer_order",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
        "required_area_display",
    )

    inlines = [
        MaterialRequirementScoreInline,
        MaterialAllocationInline,
    ]

    @admin.display(description="Arkusz")
    def sheet_dimensions(self, obj):
        return f"{obj.sheet_length} x {obj.sheet_width}"

    @admin.display(description="Potrzebna powierzchnia")
    def required_area_display(self, obj):
        if not obj.pk:
            return "-"

        return f"{obj.required_area_m2:.2f} m²"

    @admin.display(description="Bigi")
    def scores_display(self, obj):
        if not obj.pk:
            return "-"

        scores = obj.scores.values_list(
            "position_mm",
            flat=True,
        )

        return ", ".join(
            str(value)
            for value in scores
        ) or "-"


# ============================================================
# CARDBOARD GRADE
# ============================================================


@admin.register(CardboardGrade)
class CardboardGradeAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "provider",
        "index",
        "layers",
        "flute",
        "gsm",
        "ect",
        "cover",
        "is_active",
    )

    list_filter = (
        "provider",
        "layers",
        "flute",
        "cover",
        "is_active",
    )

    search_fields = (
        "index",
        "provider__name",
        "provider__shortcut",
        "composition",
    )

    autocomplete_fields = (
        "provider",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    fieldsets = (
        (
            "Materiał",
            {
                "fields": (
                    "provider",
                    "index",
                    "is_active",
                )
            },
        ),
        (
            "Parametry",
            {
                "fields": (
                    "layers",
                    "flute",
                    "gsm",
                    "ect",
                    "cover",
                    "composition",
                )
            },
        ),
        (
            "Pozostałe",
            {
                "fields": (
                    "notes",
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )


# ============================================================
# PRICE LIST INLINES
# ============================================================


class CardboardPriceListItemInline(admin.TabularInline):
    model = CardboardPriceListItem
    extra = 0

    fields = (
        "cardboard",
        "provider_status",
        "provider_status_raw",
    )

    autocomplete_fields = (
        "cardboard",
    )

    show_change_link = True


class CardboardPriceTierInline(admin.TabularInline):
    model = CardboardPriceTier
    extra = 1

    fields = (
        "min_area_m2",
        "max_area_m2",
        "price_per_1000_m2",
    )


# ============================================================
# PRICE LIST ITEM
# ============================================================


@admin.register(CardboardPriceListItem)
class CardboardPriceListItemAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "price_list",
        "cardboard",
        "provider_status",
        "provider_status_raw",
    )

    list_filter = (
        "provider_status",
        "price_list__provider",
    )

    search_fields = (
        "cardboard__index",
        "price_list__number",
        "price_list__provider__name",
        "provider_status_raw",
    )

    autocomplete_fields = (
        "price_list",
        "cardboard",
    )

    inlines = [
        CardboardPriceTierInline,
    ]


# ============================================================
# PRICE LIST
# ============================================================


@admin.register(CardboardPriceList)
class CardboardPriceListAdmin(admin.ModelAdmin):

    change_list_template = (
        "admin/orders/cardboardpricelist/change_list.html"
    )

    list_display = (
        "id",
        "provider",
        "number",
        "valid_from",
        "valid_to",
        "created_at",
    )

    list_filter = (
        "provider",
        "valid_from",
        "valid_to",
    )

    search_fields = (
        "number",
        "provider__name",
        "provider__shortcut",
    )

    autocomplete_fields = (
        "provider",
        "created_by",
    )

    readonly_fields = (
        "created_at",
    )

    inlines = [
        CardboardPriceListItemInline,
    ]

    # ========================================================
    # CUSTOM ADMIN URL
    # ========================================================

    def get_urls(self):
        urls = super().get_urls()

        custom_urls = [
            path(
                "import/",
                self.admin_site.admin_view(
                    self.import_price_list_view
                ),
                name="orders_cardboardpricelist_import",
            ),
        ]

        return custom_urls + urls

    # ========================================================
    # IMPORT PRICE LIST
    # ========================================================

    def import_price_list_view(self, request):

        if request.method == "POST":

            form = CardboardPriceListImportForm(
                request.POST,
                request.FILES,
            )

            if form.is_valid():

                provider = form.cleaned_data["provider"]
                file = form.cleaned_data["file"]

                action = request.POST.get("action")

                # --------------------------------------------
                # PREVIEW
                # --------------------------------------------

                if action == "preview":

                    try:
                        result = import_cardboard_price_list(
                            file=file,
                            provider=provider,
                            user=request.user,
                            dry_run=True,
                        )

                    except Exception as e:

                        messages.error(
                            request,
                            f"Błąd podczas parsowania cennika: {e}",
                        )

                        return render(
                            request,
                            "admin/orders/cardboardpricelist/import.html",
                            {
                                "form": form,
                            },
                        )

                    return render(
                        request,
                        "admin/orders/cardboardpricelist/import.html",
                        {
                            "form": form,
                            "preview": result,
                            "provider": provider,
                        },
                    )

                # --------------------------------------------
                # IMPORT
                # --------------------------------------------

                elif action == "import":

                    try:
                        result = import_cardboard_price_list(
                            file=file,
                            provider=provider,
                            user=request.user,
                            dry_run=False,
                        )

                    except Exception as e:

                        messages.error(
                            request,
                            f"Błąd podczas importu cennika: {e}",
                        )

                        return render(
                            request,
                            "admin/orders/cardboardpricelist/import.html",
                            {
                                "form": form,
                            },
                        )

                    messages.success(
                        request,
                        (
                            "Cennik został zaimportowany. "
                            f"Pozycje: {result['items']}, "
                            f"nowe tektury: "
                            f"{result['created_grades']}, "
                            f"zaktualizowane tektury: "
                            f"{result['updated_grades']}, "
                            f"progi cenowe: "
                            f"{result['created_tiers']}."
                        ),
                    )

                    return redirect(
                        "admin:orders_cardboardpricelist_change",
                        result["price_list"].pk,
                    )

        else:
            form = CardboardPriceListImportForm()

        return render(
            request,
            "admin/orders/cardboardpricelist/import.html",
            {
                "form": form,
            },
        )


# ============================================================
# CARDBOARD ORDER
# ============================================================


class CardboardOrderItemInline(admin.TabularInline):
    model = CardboardOrderItem
    extra = 0

    fields = (
        "requirement",
        "cardboard",
        "sheet_length",
        "sheet_width",
        "quantity",
        "price_per_1000_m2",
        "value_display",
    )

    autocomplete_fields = (
        "requirement",
        "cardboard",
    )

    readonly_fields = (
        "value_display",
    )

    @admin.display(description="Wartość")
    def value_display(self, obj):
        if not obj.pk:
            return "-"

        return f"{obj.value:.2f}"


@admin.register(CardboardOrder)
class CardboardOrderAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "provider",
        "number",
        "order_date",
        "status",
        "created_at",
    )

    list_filter = (
        "provider",
        "status",
        "order_date",
    )

    search_fields = (
        "number",
        "provider__name",
        "provider__shortcut",
    )

    autocomplete_fields = (
        "provider",
        "created_by",
        "legacy_warehouse_order",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    inlines = [
        CardboardOrderItemInline,
    ]


# ============================================================
# CARDBOARD ORDER ITEM
# ============================================================


@admin.register(CardboardOrderItem)
class CardboardOrderItemAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "order",
        "cardboard",
        "dimensions_display",
        "quantity",
        "price_per_1000_m2",
        "area_display",
        "value_display",
    )

    list_filter = (
        "order__provider",
        "cardboard__flute",
        "cardboard__layers",
    )

    search_fields = (
        "order__number",
        "cardboard__index",
        "=requirement__customer_order__number",
        "=requirement__customer_order__year",
    )

    autocomplete_fields = (
        "order",
        "requirement",
        "cardboard",
        "price_list_item",
    )

    @admin.display(description="Wymiar")
    def dimensions_display(self, obj):
        return f"{obj.sheet_length} x {obj.sheet_width}"

    @admin.display(description="Powierzchnia")
    def area_display(self, obj):
        return f"{obj.total_area_m2:.2f} m²"

    @admin.display(description="Wartość")
    def value_display(self, obj):
        return f"{obj.value:.2f}"


# ============================================================
# MATERIAL ALLOCATION
# ============================================================


@admin.register(MaterialAllocation)
class MaterialAllocationAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "requirement",
        "source",
        "quantity",
        "stock_supply",
        "cardboard_order_item",
        "created_at",
    )

    list_filter = (
        "source",
        "created_at",
    )

    search_fields = (
        "=requirement__customer_order__number",
        "=requirement__customer_order__year",
        "requirement__customer_order__customer__name",
        "stock_supply__name",
        "cardboard_order_item__cardboard__index",
    )

    autocomplete_fields = (
        "requirement",
        "stock_supply",
        "cardboard_order_item",
        "created_by",
    )

    readonly_fields = (
        "created_at",
    )


@admin.register(ProductMaterialRequirement)
class ProductMaterialRequirementAdmin(admin.ModelAdmin):

    list_display = (
        "product",
        "sheet_format",
        "pieces_per_sheet",
        "flute",
        "min_gsm",
        "min_ect",
        "cover",
        "scores",
    )

    search_fields = (
        "product__name",
        "product__dimensions",
        "flute",
        "scores",
    )

    list_filter = (
        "layers",
        "flute",
        "cover",
    )

    autocomplete_fields = (
        "product",
    )

    ordering = (
        "product__name",
    )

    fieldsets = (
        (
            "Produkt",
            {
                "fields": (
                    "product",
                ),
            },
        ),
        (
            "Format arkusza",
            {
                "fields": (
                    ("sheet_length", "sheet_width"),
                    "pieces_per_sheet",
                    "scores",
                ),
            },
        ),
        (
            "Parametry tektury",
            {
                "fields": (
                    ("layers", "flute"),
                    ("min_gsm", "min_ect"),
                    "cover",
                ),
            },
        ),
        (
            "Dodatkowe informacje",
            {
                "fields": (
                    "notes",
                ),
            },
        ),
    )

    @admin.display(description="Format")
    def sheet_format(self, obj):
        return f"{obj.sheet_length}x{obj.sheet_width}"


admin.site.register(CustomerOrderSequence)
