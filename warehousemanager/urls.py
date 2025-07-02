from django.urls import path
from warehousemanager.gluer_views import *


urlpatterns = [
    path('add-gluernumber/', NewGluerNumberAdd.as_view(), name='gluernumber-add'),
]