from django.contrib import admin
from .models import *


admin.site.register(Provider)
admin.site.register(StockType)
admin.site.register(StockSupply)
admin.site.register(Stock)
admin.site.register(Warehouse)
