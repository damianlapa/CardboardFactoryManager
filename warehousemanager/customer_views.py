from django.views import View
from django.shortcuts import render
from .models import CustomerDeliveryPlace


class DeliveryPlacesMapView(View):
    template_name = "whm/delivery_places_map.html"

    def get(self, request):
        places = CustomerDeliveryPlace.objects.select_related("customer").all()
        context = {
            "places": places
        }
        return render(request, self.template_name, context)
