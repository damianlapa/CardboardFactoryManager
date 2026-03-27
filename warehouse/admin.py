from django.contrib import admin
from .models import (
    Provider,
    StockType,
    StockSupply,
    Stock,
    Warehouse,
    Palette,
    Order,
    Delivery,
    DeliveryItem,
    DeliveryPalette,
    Product,
    WarehouseStock,
    OrderSettlement,
    OrderSettlementProduct,
    WarehouseStockHistory,
    MonthResults,
    CustomerPalette,
    ProductSell3,
    ProductComplexParts,
    ProductComplexAssembly,
    DeliverySpecial,
    DeliverySpecialItem,
    OrderToOrderShift,
    PriceList,
    PriceListItem,
    StockSupplySettlement,
    StockSupplySell,
    BOM,
    BOMPart,
    StockAlias,
    ProductSellOrderPart,
    ProductPackaging,
)


# =========================
# Inlines
# =========================

class DeliveryItemInline(admin.TabularInline):
    model = DeliveryItem
    extra = 0
    autocomplete_fields = ["order", "stock"]


class DeliveryPaletteInline(admin.TabularInline):
    model = DeliveryPalette
    extra = 0
    autocomplete_fields = ["palette"]


class DeliverySpecialItemInline(admin.TabularInline):
    model = DeliverySpecialItem
    extra = 0
    autocomplete_fields = ["stock"]


class PriceListItemInline(admin.TabularInline):
    model = PriceListItem
    extra = 0


class BOMPartInline(admin.TabularInline):
    model = BOMPart
    extra = 0
    autocomplete_fields = ["part"]


class ProductComplexPartsInline(admin.TabularInline):
    model = ProductComplexParts
    extra = 0
    autocomplete_fields = ["part"]


class OrderSettlementProductInline(admin.TabularInline):
    model = OrderSettlementProduct
    extra = 0
    autocomplete_fields = ["stock_supply"]


# =========================
# Simple dictionaries
# =========================

@admin.register(Provider)
class ProviderAdmin(admin.ModelAdmin):
    list_display = ("name", "shortcut")
    search_fields = ("name", "shortcut")
    ordering = ("name",)


@admin.register(StockType)
class StockTypeAdmin(admin.ModelAdmin):
    list_display = ("stock_type", "unit")
    search_fields = ("stock_type", "unit")
    list_filter = ("unit",)
    ordering = ("stock_type", "unit")


@admin.register(Palette)
class PaletteAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)
    ordering = ("name",)


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ("name", "description")
    search_fields = ("name", "description")
    ordering = ("name",)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "dimensions", "flute", "gsm", "price")
    search_fields = ("name", "dimensions", "flute")
    list_filter = ("flute",)
    ordering = ("name",)


# =========================
# Stocks / warehouse
# =========================

@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ("name", "stock_type", "quantity")
    search_fields = ("name", "stock_type__stock_type")
    list_filter = ("stock_type",)
    autocomplete_fields = ["stock_type"]
    ordering = ("stock_type__stock_type", "name")


@admin.register(WarehouseStock)
class WarehouseStockAdmin(admin.ModelAdmin):
    list_display = ("stock", "warehouse", "quantity")
    search_fields = (
        "stock__name",
        "stock__stock_type__stock_type",
        "warehouse__name",
    )
    list_filter = ("warehouse", "stock__stock_type")
    autocomplete_fields = ["warehouse", "stock"]
    ordering = ("warehouse__name", "stock__name")


@admin.register(StockSupply)
class StockSupplyAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "date",
        "name",
        "stock_type",
        "quantity",
        "value",
        "used",
        "delivery_item",
        "delivery_special_item",
    )
    search_fields = (
        "name",
        "dimensions",
        "delivery_item__order__order_id",
        "delivery_item__delivery__number",
        "delivery_special_item__name",
    )
    list_filter = ("used", "stock_type", "date")
    autocomplete_fields = ["stock_type", "delivery_item", "delivery_special_item"]
    date_hierarchy = "date"
    ordering = ("-date", "-id")


@admin.register(WarehouseStockHistory)
class WarehouseStockHistoryAdmin(admin.ModelAdmin):
    list_display = (
        "date",
        "warehouse_stock",
        "delta",
        "quantity_before",
        "quantity_after",
        "stock_supply",
        "order_settlement",
        "sell",
        "assembly",
    )
    search_fields = (
        "warehouse_stock__stock__name",
        "warehouse_stock__warehouse__name",
        "stock_supply__name",
        "sell__customer__name",
    )
    list_filter = ("date", "warehouse_stock__warehouse")
    autocomplete_fields = ["warehouse_stock", "stock_supply", "order_settlement", "assembly", "sell"]
    date_hierarchy = "date"
    ordering = ("-date", "-id")


@admin.register(StockAlias)
class StockAliasAdmin(admin.ModelAdmin):
    list_display = ("provider", "provider_sku", "dimensions", "stock", "is_active")
    search_fields = (
        "provider__name",
        "provider__shortcut",
        "provider_sku",
        "dimensions",
        "stock__name",
    )
    list_filter = ("is_active", "provider")
    autocomplete_fields = ["provider", "stock"]
    ordering = ("provider__name", "provider_sku", "dimensions")


# =========================
# Orders / deliveries
# =========================

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "provider",
        "order_id",
        "order_year",
        "customer",
        "name",
        "dimensions",
        "order_date",
        "delivery_date",
        "order_quantity",
        "delivered_quantity",
        "delivered",
        "finished",
    )
    search_fields = (
        "order_id",
        "order_year",
        "name",
        "dimensions",
        "customer__name",
        "provider__name",
        "provider__shortcut",
    )
    list_filter = (
        "provider",
        "delivered",
        "finished",
        "updated",
        "order_date",
        "delivery_date",
    )
    autocomplete_fields = ["customer", "provider", "product", "bom"]
    date_hierarchy = "order_date"
    ordering = ("-order_date", "provider", "order_id")


@admin.register(Delivery)
class DeliveryAdmin(admin.ModelAdmin):
    list_display = (
        "number",
        "provider",
        "date",
        "car_number",
        "processed",
        "updated",
    )
    search_fields = ("number", "provider__name", "provider__shortcut", "car_number", "telephone")
    list_filter = ("processed", "updated", "date", "provider")
    autocomplete_fields = ["provider"]
    inlines = [DeliveryItemInline, DeliveryPaletteInline]
    date_hierarchy = "date"
    ordering = ("-date", "-id")


@admin.register(DeliveryItem)
class DeliveryItemAdmin(admin.ModelAdmin):
    list_display = (
        "delivery",
        "order",
        "quantity",
        "provider_sku",
        "stock",
        "processed",
        "updated",
    )
    search_fields = (
        "delivery__number",
        "order__order_id",
        "order__name",
        "provider_sku",
        "stock__name",
    )
    list_filter = ("processed", "updated", "delivery__provider")
    autocomplete_fields = ["delivery", "order", "stock"]
    ordering = ("-delivery__date", "-id")


@admin.register(DeliveryPalette)
class DeliveryPaletteAdmin(admin.ModelAdmin):
    list_display = ("delivery", "palette", "quantity")
    search_fields = ("delivery__number", "palette__name")
    autocomplete_fields = ["delivery", "palette"]


@admin.register(DeliverySpecial)
class DeliverySpecialAdmin(admin.ModelAdmin):
    list_display = ("name", "provider", "date", "processed")
    search_fields = ("name", "provider", "description")
    list_filter = ("processed", "date")
    inlines = [DeliverySpecialItemInline]
    date_hierarchy = "date"
    ordering = ("-date", "-id")


@admin.register(DeliverySpecialItem)
class DeliverySpecialItemAdmin(admin.ModelAdmin):
    list_display = (
        "delivery",
        "name",
        "quantity",
        "price",
        "processed",
        "provider_sku",
        "stock",
    )
    search_fields = ("delivery__name", "name", "provider_sku", "stock__name")
    list_filter = ("processed", "delivery__date")
    autocomplete_fields = ["delivery", "stock"]
    ordering = ("-delivery__date", "-id")


@admin.register(OrderToOrderShift)
class OrderToOrderShiftAdmin(admin.ModelAdmin):
    list_display = ("date", "order_from", "order_to", "quantity")
    search_fields = (
        "order_from__order_id",
        "order_to__order_id",
        "order_from__name",
        "order_to__name",
    )
    autocomplete_fields = ["order_from", "order_to"]
    date_hierarchy = "date"
    ordering = ("-date", "-id")


# =========================
# Settlements / sales
# =========================

@admin.register(OrderSettlement)
class OrderSettlementAdmin(admin.ModelAdmin):
    list_display = ("order", "material", "material_quantity", "settlement_date")
    search_fields = (
        "order__order_id",
        "order__name",
        "material__stock__name",
        "material__warehouse__name",
    )
    list_filter = ("settlement_date",)
    autocomplete_fields = ["order", "material"]
    inlines = [OrderSettlementProductInline]
    date_hierarchy = "settlement_date"
    ordering = ("-settlement_date", "-id")


@admin.register(OrderSettlementProduct)
class OrderSettlementProductAdmin(admin.ModelAdmin):
    list_display = ("settlement", "stock_supply", "quantity", "is_semi_product")
    search_fields = (
        "settlement__order__order_id",
        "stock_supply__name",
    )
    list_filter = ("is_semi_product",)
    autocomplete_fields = ["settlement", "stock_supply"]


@admin.register(StockSupplySettlement)
class StockSupplySettlementAdmin(admin.ModelAdmin):
    list_display = ("settlement", "stock_supply", "quantity", "value", "as_result")
    search_fields = (
        "settlement__order__order_id",
        "stock_supply__name",
    )
    list_filter = ("as_result", "settlement__settlement_date")
    autocomplete_fields = ["settlement", "stock_supply"]
    ordering = ("-settlement__settlement_date", "-id")


@admin.register(ProductSell3)
class ProductSell3Admin(admin.ModelAdmin):
    list_display = (
        "date",
        "customer",
        "customer_alter_name",
        "product",
        "stock",
        "warehouse_stock",
        "order",
        "quantity",
        "price",
    )
    search_fields = (
        "customer__name",
        "customer_alter_name",
        "product__name",
        "stock__name",
        "order__order_id",
    )
    list_filter = ("date", "customer", "product")
    autocomplete_fields = ["customer", "product", "stock", "warehouse_stock", "order"]
    date_hierarchy = "date"
    ordering = ("-date", "-id")


@admin.register(StockSupplySell)
class StockSupplySellAdmin(admin.ModelAdmin):
    list_display = ("sell", "stock_supply", "quantity")
    search_fields = (
        "sell__customer__name",
        "sell__order__order_id",
        "stock_supply__name",
    )
    autocomplete_fields = ["sell", "stock_supply"]
    ordering = ("-sell__date", "-id")


@admin.register(ProductSellOrderPart)
class ProductSellOrderPartAdmin(admin.ModelAdmin):
    list_display = ("sell", "order", "quantity")
    search_fields = (
        "sell__customer__name",
        "sell__order__order_id",
        "order__order_id",
    )
    autocomplete_fields = ["sell", "order"]


# =========================
# Price lists
# =========================

@admin.register(PriceList)
class PriceListAdmin(admin.ModelAdmin):
    list_display = ("provider", "date_start", "date_end")
    search_fields = ("provider__name", "provider__shortcut")
    list_filter = ("provider", "date_start", "date_end")
    autocomplete_fields = ["provider"]
    inlines = [PriceListItemInline]
    ordering = ("-date_start", "-id")


@admin.register(PriceListItem)
class PriceListItemAdmin(admin.ModelAdmin):
    list_display = ("price_list", "name", "flute", "weight", "etc", "price", "price2")
    search_fields = ("name", "flute", "price_list__provider__name")
    autocomplete_fields = ["price_list"]
    ordering = ("price_list", "name")


# =========================
# BOM
# =========================

@admin.register(BOM)
class BOMAdmin(admin.ModelAdmin):
    list_display = ("product", "version", "is_active", "created_at")
    search_fields = ("product__name",)
    list_filter = ("is_active", "created_at")
    autocomplete_fields = ["product"]
    inlines = [BOMPartInline]
    ordering = ("product__name", "-version")


@admin.register(BOMPart)
class BOMPartAdmin(admin.ModelAdmin):
    list_display = ("bom", "part", "quantity")
    search_fields = ("bom__product__name", "part__name")
    autocomplete_fields = ["bom", "part"]


# =========================
# Assemblies
# =========================

@admin.register(ProductComplexAssembly)
class ProductComplexAssemblyAdmin(admin.ModelAdmin):
    list_display = ("date", "product", "quantity", "is_locked")
    search_fields = ("product__name",)
    list_filter = ("date",)
    autocomplete_fields = ["product"]
    inlines = [ProductComplexPartsInline]
    date_hierarchy = "date"
    ordering = ("-date", "-id")


@admin.register(ProductComplexParts)
class ProductComplexPartsAdmin(admin.ModelAdmin):
    list_display = ("assembly", "part", "quantity")
    search_fields = (
        "assembly__product__name",
        "part__stock__name",
        "part__warehouse__name",
    )
    autocomplete_fields = ["assembly", "part"]


# =========================
# Other
# =========================

@admin.register(MonthResults)
class MonthResultsAdmin(admin.ModelAdmin):
    list_display = (
        "year",
        "month",
        "expenses",
        "financial_expenses",
        "management_expenses",
        "logistic_expenses",
        "other_expenses",
    )
    list_filter = ("year", "month")
    ordering = ("-year", "-month")


@admin.register(CustomerPalette)
class CustomerPaletteAdmin(admin.ModelAdmin):
    list_display = ("customer", "palette", "quantity")
    search_fields = ("customer__name", "palette__name")
    autocomplete_fields = ["customer", "palette"]


@admin.register(ProductPackaging)
class ProductPackagingAdmin(admin.ModelAdmin):
    list_display = (
        "product",
        "palette",
        "columns",
        "layers",
        "qty_per_pack",
        "qty_per_pallet",
        "updated_at",
    )
    search_fields = ("product__name", "palette__name")
    autocomplete_fields = ["product", "palette"]
    ordering = ("product__name",)