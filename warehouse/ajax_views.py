# from django.http import JsonResponse
# from django.shortcuts import get_object_or_404
# from django.db import transaction
# from .models import Order, StockSupply, OrderSettlement, OrderSettlementProduct
#
#
# def settle_order(request, order_id):
#     if request.method == "POST":
#         order = get_object_or_404(Order, id=order_id)
#         material_id = request.POST.get("material_id")
#         material_quantity = int(request.POST.get("material_quantity", 0))
#         stock_supply_ids = request.POST.getlist("stock_supply_id")
#         stock_quantities = request.POST.getlist("stock_quantity")
#
#         try:
#             with transaction.atomic():
#                 # material = get_object_or_404(Stock, id=material_id)
#                 material = ''
#
#                 # Create settlement
#                 settlement = OrderSettlement.objects.create(
#                     order=order,
#                     material=material,
#                     material_quantity=material_quantity,
#                 )
#
#                 # Create products
#                 for stock_supply_id, quantity in zip(stock_supply_ids, stock_quantities):
#                     if int(quantity) > 0:
#                         stock_supply = get_object_or_404(StockSupply, id=stock_supply_id)
#                         OrderSettlementProduct.objects.create(
#                             settlement=settlement,
#                             stock_supply=stock_supply,
#                             quantity=int(quantity),
#                             is_semi_product=False
#                         )
#             return JsonResponse({"success": True})
#         except Exception as e:
#             return JsonResponse({"success": False, "error": str(e)})
#
#     return JsonResponse({"success": False, "error": "Invalid request"})