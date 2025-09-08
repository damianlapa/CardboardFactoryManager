from django.views import View
from django.shortcuts import render
from .models import CustomerDeliveryPlace, Buyer


class DeliveryPlacesMapView(View):
    template_name = "whm/delivery_places_map.html"

    def get(self, request):
        places = CustomerDeliveryPlace.objects.exclude(latitude__isnull=True).exclude(longitude__isnull=True)
        context = {
            "places": places
        }
        return render(request, self.template_name, context)


# views.py
from django.http import HttpResponse
from django.views import View
from django.db.models import Prefetch
from openpyxl import Workbook

from .models import Buyer, CustomerDeliveryPlace  # dostosuj ścieżkę importu

class AllCustomersView(View):
    """
    Zwraca Excela: [Nazwa klienta] | [Adres dostawy (Main)] | [lat_long]
    """

    def get(self, request, *args, **kwargs):
        # Prefetch miejsc dostaw, żeby uniknąć N+1:
        buyers = (
            Buyer.objects.all()
            .order_by("name")
            .prefetch_related(
                Prefetch(
                    "customerdeliveryplace_set",
                    queryset=CustomerDeliveryPlace.objects.all(),
                    to_attr="delivery_places",
                )
            )
        )

        wb = Workbook()
        ws = wb.active
        ws.title = "Klienci"
        ws.append(["Nazwa klienta", "Adres dostawy (Main)", "lat_long"])

        for buyer in buyers:
            # znajdź "Main" (case-insensitive), albo None
            main_place = None
            if hasattr(buyer, "delivery_places"):
                main_place = next(
                    (p for p in buyer.delivery_places if str(p.name).lower() == "main"),
                    None,
                )
            else:
                main_place = (
                    CustomerDeliveryPlace.objects
                    .filter(customer=buyer, name__iexact="Main")
                    .first()
                )

            # zbuduj adres z dostępnych pól (elastycznie)
            address = ""
            if main_place:
                # najpierw prosto: jedno pole 'address' jeżeli istnieje
                addr_raw = getattr(main_place, "address", None)
                if addr_raw:
                    address = str(addr_raw)
                else:
                    # spróbuj złożyć z części: street / address_line / postal_code / city / country itp.
                    parts = []
                    for attr in ("street", "address_line", "address1", "address2", "postal_code", "zip_code", "city", "country"):
                        val = getattr(main_place, attr, None)
                        if val:
                            parts.append(str(val))
                    address = ", ".join(parts)

            lat_long = getattr(main_place, "lat_long", "") if main_place else ""

            ws.append([
                getattr(buyer, "name", str(buyer)),
                address,
                lat_long,
            ])

        # przygotuj odpowiedź HTTP z plikiem XLSX
        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = 'attachment; filename="buyers_delivery_places.xlsx"'
        wb.save(response)
        return response
