from django.urls import path
from warehousemanager.gluer_views import *
from warehousemanager.customer_views import *


urlpatterns = [
    path('add-gluernumber/', NewGluerNumberAdd.as_view(), name='gluernumber-add'),
]

urlpatterns += [
    path("map-deliveries/", DeliveryPlacesMapView.as_view(), name="delivery_places_map"),
]
