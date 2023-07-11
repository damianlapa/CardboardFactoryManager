from django.contrib import admin
from finances.models import *

admin.site.register(Resource)
admin.site.register(Product)
admin.site.register(Expense)
admin.site.register(Customer)
admin.site.register(ProductProduction)
admin.site.register(ProductResourceProduction)
admin.site.register(ProductSell)