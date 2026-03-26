from django.db import IntegrityError, transaction
from warehouse.models import Product
from warehouse.services.naming import build_product_name


def safe_get_or_create_product(customer, flute, dimensions, extra=""):
    name = build_product_name(customer, flute, dimensions, extra)
    print("created name:", name)
    try:
        with transaction.atomic():
            product, _ = Product.objects.get_or_create(
                name=name,
                defaults={
                    # "dimensions": dimensions,
                    "flute": flute,
                    "gsm": 0,
                }
            )
            print('sgcop returns:', product)
            return product
    except IntegrityError:
        # jeśli drugi proces zdążył wstawić
        return Product.objects.get(name=name)
