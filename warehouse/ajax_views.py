import datetime

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.db import transaction
from .models import Order, StockSupply, OrderSettlement, OrderSettlementProduct, WarehouseStock, WarehouseStockHistory, \
    Product, StockType, Stock, Warehouse


def settle_order(request, order_id):
    if request.method == "POST":
        settlement_date = request.POST.get('settlement_date') if request.POST.get('settlement_date') else datetime.datetime.today()
        order = get_object_or_404(Order, id=order_id)
        material_id = request.POST.get("material_id")
        material_quantity = int(request.POST.get("material_quantity", 0))

        material_ids = request.POST.getlist('material_id')
        material_quantities = request.POST.getlist('material_quantity')
        print(material_ids, material_quantities)

        for material_id2, quantity2 in zip(material_ids, material_quantities):
            print(material_id2, quantity2, '#MATER')

        product_ids = request.POST.getlist('product_id')
        product_types = request.POST.getlist('product_type')
        product_quantities = request.POST.getlist('product_quantity')
        product_warehouses = request.POST.getlist('product_warehouse')

        # print(product_names, product_quantities)
        #
        # for name3, quantity3 in zip(product_names, product_quantities):
        #     print(name3, quantity3, '#PROD')

        try:
            with transaction.atomic():
                material = WarehouseStock.objects.get(id=int(material_id))

                # Create settlement
                settlement, created = OrderSettlement.objects.get_or_create(
                    order=order,
                    material=material,
                    material_quantity=material_quantity,
                    settlement_date=settlement_date
                )

                history, created = WarehouseStockHistory.objects.get_or_create(
                    warehouse_stock=material,
                    order_settlement=settlement,
                    quantity_before=material.quantity,
                    quantity_after=material.quantity - int(material_quantity)
                )

                material.quantity -= int(material_quantity)
                material.save()

                # Create products
                # for stock_supply_id, quantity in zip(stock_supply_ids, stock_quantities):
                #     if int(quantity) > 0:
                #         stock_supply = get_object_or_404(StockSupply, id=stock_supply_id)
                #         OrderSettlementProduct.objects.create(
                #             settlement=settlement,
                #             stock_supply=stock_supply,
                #             quantity=int(quantity),
                #             is_semi_product=False
                #         )
                for product_id, product_type, product_quantity, warehouse in zip(product_ids, product_types,
                                                                                 product_quantities,
                                                                                 product_warehouses):
                    product = Product.objects.get(id=int(product_id))
                    dimensions = product.dimensions
                    product_type = StockType.objects.get(id=int(product_type))
                    warehouse = Warehouse.objects.get(id=int(warehouse))

                    supply, created = StockSupply.objects.get_or_create(
                        stock_type=product_type,
                        date=settlement_date,
                        quantity=int(product_quantity),
                        name=product.name,
                    )

                    stock, created = Stock.objects.get_or_create(
                        stock_type=product_type,
                        name=f'{product_type} | {dimensions}'
                    )

                    warehouse_stock, created = WarehouseStock.objects.get_or_create(
                        stock=stock,
                        warehouse=warehouse
                    )

                    warehouse_stock_history = WarehouseStockHistory.objects.create(
                        warehouse_stock=warehouse_stock,
                        order_settlement=settlement,
                        stock_supply=supply,
                        quantity_before=warehouse_stock.quantity,
                        quantity_after=warehouse_stock.quantity + int(product_quantity),
                        date=settlement_date
                    )

                    warehouse_stock.quantity = warehouse_stock.quantity + int(product_quantity)
                    warehouse_stock.save()

            return JsonResponse({"success": True})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})

    return JsonResponse({"success": False, "error": "Invalid request"})


def order_status(request):
    if request.method == 'GET':
        order_id = request.GET.get('order_id')
        action = request.GET.get('action')
        order = Order.objects.get(id=int(order_id))
        if action == 'delivered':
            order.delivered = False if order.delivered else True
        else:
            order.finished = False if order.delivered else True
        order.save()
        print(order.delivered, order.finished)
        return JsonResponse({'success': True})
