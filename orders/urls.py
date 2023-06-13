from django.urls import path
from orders.views import *


urlpatterns = [
    path('product/new', AddProduct.as_view(), name='new_product'),
]
