import datetime
from django.shortcuts import render, HttpResponse, redirect
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.db import transaction
from .models import Order, StockSupply, OrderSettlement, OrderSettlementProduct, WarehouseStock, WarehouseStockHistory, \
    Product, StockType, Stock, Warehouse, StockSupplySettlement
from warehouse.services.stock_moves import move_ws
from django.db import IntegrityError


def normalize_name(n: str) -> str:
    n = " ".join((n or "").strip().split())
    if "|" in n:
        parts = [p.strip() for p in n.split("|")]
        while parts and parts[-1] == "":
            parts.pop()
        n = " | ".join(parts)
    return n


def settle_order(request, order_id):
    if request.method == "POST":
        settlement_date = request.POST.get('settlement_date') if request.POST.get('settlement_date') else datetime.datetime.today()
        order = get_object_or_404(Order, id=order_id)
        material_id = request.POST.get("material_id")
        material_quantity = int(request.POST.get("material_quantity", 0))

        material_ids = request.POST.getlist('material_id')
        material_quantities = request.POST.getlist('material_quantity')

        product_ids = request.POST.getlist('product_id')
        product_types = request.POST.getlist('product_type')
        product_quantities = request.POST.getlist('product_quantity')
        product_warehouses = request.POST.getlist('product_warehouse')

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

                result, value = material.use_specified_stock_supply(settlement, material_quantity)

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

                    stock_name = normalize_name(product.name)

                    supply = StockSupply.objects.create(
                        stock_type=product_type,
                        date=settlement_date,
                        quantity=int(product_quantity),
                        name=stock_name,
                        value=value
                    )

                    stock_supply_settlement = StockSupplySettlement.objects.create(
                        stock_supply=supply,
                        settlement=settlement,
                        quantity=int(product_quantity),
                        value=value,
                        as_result=True
                    )

                    try:
                        stock, created = Stock.objects.get_or_create(
                            stock_type=product_type,
                            name=stock_name,
                        )
                    except IntegrityError:
                        # wyścig / normalizacja -> dociągnij istniejący
                        stock = Stock.objects.get(stock_type=product_type, name=stock_name)
                        created = False

                    warehouse_stock, created = WarehouseStock.objects.get_or_create(
                        stock=stock,
                        warehouse=warehouse
                    )

                    move_ws(
                        ws=warehouse_stock,
                        delta=int(product_quantity),
                        date=settlement_date,
                        stock_supply=supply,
                        order_settlement=settlement,
                    )

            return redirect(request.META.get('HTTP_REFERER', '/'))
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})

    # return JsonResponse({"success": False, "error": "Invalid request"})

    return redirect(request.META.get('HTTP_REFERER', '/'))


def order_status(request):
    if request.method == 'GET':
        order_id = request.GET.get('order_id')
        action = request.GET.get('action')
        order = Order.objects.get(id=int(order_id))
        if action == 'delivered':
            order.delivered = False if order.delivered else True
        elif action == 'finished':
            order.finished = False if order.finished else True
        order.save()
        return JsonResponse({'success': True, 'delivery': order.delivered, 'finished': order.finished})
