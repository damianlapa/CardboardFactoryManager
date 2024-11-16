from django.contrib import admin
from .models import *


admin.site.register(Provider)
admin.site.register(StockType)
admin.site.register(StockSupply)
admin.site.register(Stock)
admin.site.register(Warehouse)
admin.site.register(Palette)
admin.site.register(Order)
admin.site.register(Delivery)
admin.site.register(DeliveryItem)
admin.site.register(DeliveryPalette)
admin.site.register(Product)
admin.site.register(WarehouseStock)
admin.site.register(OrderSettlement)
admin.site.register(OrderSettlementProduct)
