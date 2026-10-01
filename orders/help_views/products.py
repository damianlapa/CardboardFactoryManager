from django.http import JsonResponse
from warehouse.models import Product


def customer_products(request):
    customer_id = request.GET.get("customer_id")

    if not customer_id:
        return JsonResponse({"products": []})

    products = (
        Product.objects
        .filter(order__customer_id=customer_id)
        .distinct()
        .order_by("name")
        .values("id", "name")
    )

    print(products)

    return JsonResponse({
        "products": list(products)
    })