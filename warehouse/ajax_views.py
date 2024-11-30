from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.db import transaction
from .models import Order, StockSupply, OrderSettlement, OrderSettlementProduct, WarehouseStock, WarehouseStockHistory


def settle_order(request, order_id):
    if request.method == "POST":
        order = get_object_or_404(Order, id=order_id)
        material_id = request.POST.get("material_id")
        material_quantity = int(request.POST.get("material_quantity", 0))

        material_ids = request.POST.getlist('material_id')
        material_quantities = request.POST.getlist('material_quantity')

        for material_id2, quantity2 in zip(material_ids, material_quantities):
            print(material_id2, quantity2, '#MATER')

        product_names = request.POST.getlist('product_name')
        product_quantities = request.POST.getlist('product_quantity')

        for name3, quantity3 in zip(product_names, product_quantities):
            print(name3, quantity3, '#PROD')

        try:
            with transaction.atomic():
                material = WarehouseStock.objects.get(id=int(material_id))

                # Create settlement
                settlement, created = OrderSettlement.objects.get_or_create(
                    order=order,
                    material=material,
                    material_quantity=material_quantity,
                )

                history, created = WarehouseStockHistory.objects.get_or_create(
                    warehouse_stock=material,
                    order_settlement=settlement,
                    quantity_before=material.quantity,
                    quantity_after=material.quantity - int(material_quantity)
                )

                material.quantity -= int(material_quantity)
                material.save()


                # # Create products
                # for stock_supply_id, quantity in zip(stock_supply_ids, stock_quantities):
                #     if int(quantity) > 0:
                #         stock_supply = get_object_or_404(StockSupply, id=stock_supply_id)
                #         OrderSettlementProduct.objects.create(
                #             settlement=settlement,
                #             stock_supply=stock_supply,
                #             quantity=int(quantity),
                #             is_semi_product=False
                #         )
            return JsonResponse({"success": True})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})

    return JsonResponse({"success": False, "error": "Invalid request"})