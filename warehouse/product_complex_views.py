from django.contrib import messages
from django.db import transaction
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import CreateView, UpdateView
from .models import ProductComplexAssembly, WarehouseStock, WarehouseStockHistory, Product, StockType, Stock, StockSupply, Warehouse
from .forms import ProductComplexAssemblyForm, PartsFormSet


class AssemblyMixin:
    model = ProductComplexAssembly
    form_class = ProductComplexAssemblyForm
    template_name = "warehouse/assembly_form.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if self.request.method == "POST":
            ctx["parts_formset"] = PartsFormSet(self.request.POST, instance=self.object)
        else:
            ctx["parts_formset"] = PartsFormSet(instance=self.object)
        return ctx

    def form_invalid(self, form):
        # Dopnij formset do invalid, żeby pokazać błędy z obu
        ctx = self.get_context_data(form=form)
        return self.render_to_response(ctx)

    @transaction.atomic
    def form_valid(self, form):
        ctx = self.get_context_data()
        parts_formset = ctx["parts_formset"]
        if not parts_formset.is_valid():
            return self.render_to_response(self.get_context_data(form=form))
        self.object = form.save()
        parts_formset.instance = self.object
        parts_formset.save()
        messages.success(self.request, "Zapisano montaż i części.")
        return redirect(self.get_success_url())

    def get_success_url(self):
        # po zapisie wracamy do edycji bieżącego montażu
        return reverse("warehouse:assembly_update", args=[self.object.pk])


class AssemblyCreateView(AssemblyMixin, CreateView):

    @transaction.atomic
    def form_valid(self, form):
        # 1) Walidacja i zapis assembly + formsetu (bez commitów magazynowych)
        ctx = self.get_context_data()
        parts_formset = ctx["parts_formset"]
        if not parts_formset.is_valid():
            return self.render_to_response(self.get_context_data(form=form))

        self.object = form.save()  # ma już date, product, quantity

        product = self.object.product
        dimensions = product.dimensions
        product_type = StockType.objects.get(stock_type="Product")
        warehouse = Warehouse.objects.get(name="MAGAZYN WYROBÓW GOTOWYCH")

        supply, created = StockSupply.objects.get_or_create(
            stock_type=product_type,
            date=self.object.date,
            quantity=self.object.quantity,
            name=product.name,
        )

        stock, created = Stock.objects.get_or_create(
            stock_type=product_type,
            name=f'{product.name}'
        )

        warehouse_stock, created = WarehouseStock.objects.get_or_create(
            stock=stock,
            warehouse=warehouse
        )

        warehouse_stock_history = WarehouseStockHistory.objects.create(
            warehouse_stock=warehouse_stock,
            assembly=self.object,
            stock_supply=supply,
            quantity_before=warehouse_stock.quantity,
            quantity_after=warehouse_stock.quantity + self.object.quantity,
            date=self.object.date
        )

        warehouse_stock.quantity = warehouse_stock.quantity + self.object.quantity
        warehouse_stock.save()


        parts_formset.instance = self.object
        parts_formset.save()

        # 2) Wylicz zapotrzebowanie per WarehouseStock (sumujemy duplikaty)
        assembly_qty = self.object.quantity or 0
        required_per_stock = {}  # {stock_id: total_required}

        for cd in parts_formset.cleaned_data:
            if not cd or cd.get("DELETE"):
                continue
            ws = cd["part"]  # WarehouseStock
            per_unit = cd.get("quantity") or 0
            total_need = per_unit * assembly_qty
            if total_need <= 0:
                continue
            required_per_stock[ws.pk] = required_per_stock.get(ws.pk, 0) + total_need

        if not required_per_stock:
            messages.success(self.request, "Zapisano montaż (brak części do rozliczenia).")
            return redirect(self.get_success_url())

        # 3) Zablokuj wiersze magazynowe i sprawdź dostępność
        stocks = (
            WarehouseStock.objects
            .select_for_update()
            .select_related("stock", "warehouse")
            .filter(pk__in=required_per_stock.keys())
        )

        lacks = []  # [(WarehouseStock, missing)]
        for s in stocks:
            need = required_per_stock[s.pk]
            if s.quantity < need:
                lacks.append((s, need - s.quantity))

        if lacks:
            # Dodaj czytelny błąd i wycofaj transakcję (nie zapisujemy zmian magazynu)
            msg_lines = [
                f"- {s.stock.name} ({s.warehouse.name}): brakuje {missing}"
                for s, missing in lacks
            ]
            form.add_error(None, "Brak części na magazynie:\n" + "\n".join(msg_lines))

            # Cofnij zapis assembly i parts (bo jesteśmy w jednej transakcji)
            # Najprościej: rzuć ValidationError i wyrenderuj błędy.
            transaction.set_rollback(True)
            return self.render_to_response(self.get_context_data(form=form))

        # 4) Zastosuj zmiany i przygotuj historię
        histories = []
        for s in stocks:
            before = s.quantity
            need = required_per_stock[s.pk]
            s.quantity = before - need
            histories.append(WarehouseStockHistory(
                warehouse_stock=s,
                assembly=self.object,
                quantity_before=before,
                quantity_after=s.quantity,
                date=self.object.date,  # ustawiamy jawnie datę z montażu
            ))

        # 5) Zapis masowy
        WarehouseStock.objects.bulk_update(stocks, ["quantity"])
        WarehouseStockHistory.objects.bulk_create(histories)

        messages.success(self.request, "Zapisano montaż, zaktualizowano stany i historię.")
        return redirect(self.get_success_url())



class AssemblyUpdateView(AssemblyMixin, UpdateView):
    pass
