from django.http import JsonResponse
from warehouse.models import Product


def customer_products(request):
    from warehousemanager.models import Buyer
    customer_id = request.GET.get("customer_id")

    if not customer_id:
        return JsonResponse({"products": []})

    customer_name = Buyer.objects.get(id=int(customer_id)).name

    # products = (
    #     Product.objects
    #     .filter(order__customer_id=customer_id)
    #     .distinct()
    #     .order_by("name")
    #     .values("id", "name")
    # )

    products = (
        Product.objects
        .filter(name__icontains=customer_name)
        .distinct()
        .order_by("name")
        .values("id", "name")
    )

    return JsonResponse({
        "products": list(products)
    })