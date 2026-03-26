from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count, Q, Max

from warehouse.models import StockSupply, StockSupplySettlement, StockSupplySell


class Command(BaseCommand):
    help = "Usuwa duplikaty StockSupply bez value (value=0) gdy istnieje identyczny wpis z value>0. Przepina FK settlements/sells na wpis KEEP."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="Wykonaj zmiany (domyślnie DRY-RUN).")
        parser.add_argument("--limit", type=int, default=0, help="Limit grup do przetworzenia (0 = bez limitu).")

    def handle(self, *args, **opts):
        apply = opts["apply"]
        limit = opts["limit"]

        # Grupy duplikatów: (stock_type, date, name, quantity)
        # Interesują nas tylko takie, gdzie istnieje jednocześnie value==0 i value>0
        groups = (
            StockSupply.objects
            .values("stock_type_id", "date", "name", "quantity")
            .annotate(
                total=Count("id"),
                zeros=Count("id", filter=Q(value=0)),
                positives=Count("id", filter=Q(value__gt=0)),
                max_value=Max("value"),
            )
            .filter(total__gt=1, zeros__gt=0, positives__gt=0)
            .order_by("-total")
        )

        if limit and limit > 0:
            groups = groups[:limit]

        self.stdout.write(f"=== CLEANUP STOCKSUPPLY DUPLICATES (value=0 vs value>0) ===")
        self.stdout.write(f"mode = {'APPLY' if apply else 'DRY-RUN'}")
        self.stdout.write(f"groups found: {groups.count()}")

        total_deleted = 0
        total_rewired_settlements = 0
        total_rewired_sells = 0

        for g in groups:
            qs = StockSupply.objects.filter(
                stock_type_id=g["stock_type_id"],
                date=g["date"],
                name=g["name"],
                quantity=g["quantity"],
            ).order_by("-value", "id")  # najwyższe value jako pierwsze

            keep = qs.filter(value__gt=0).first()
            if not keep:
                continue

            delete_qs = qs.filter(value=0).exclude(id=keep.id)
            if not delete_qs.exists():
                continue

            delete_ids = list(delete_qs.values_list("id", flat=True))

            # policz referencje przed przepinaniem (raport)
            settlements_count = StockSupplySettlement.objects.filter(stock_supply_id__in=delete_ids).count()
            sells_count = StockSupplySell.objects.filter(stock_supply_id__in=delete_ids).count()

            self.stdout.write("-" * 100)
            self.stdout.write(
                f"date={g['date']} | name={g['name']} | qty={g['quantity']} | stock_type_id={g['stock_type_id']} | "
                f"KEEP={keep.id} (value={keep.value}) DELETE={delete_ids} "
                f"| refs: settlements={settlements_count}, sells={sells_count}"
            )

            if not apply:
                continue

            with transaction.atomic():
                # 1) przepnij settlements
                rew_sett = StockSupplySettlement.objects.filter(stock_supply_id__in=delete_ids).update(stock_supply=keep)
                # 2) przepnij sells
                rew_sell = StockSupplySell.objects.filter(stock_supply_id__in=delete_ids).update(stock_supply=keep)
                # 3) usuń duplikaty value=0
                deleted, _ = StockSupply.objects.filter(id__in=delete_ids).delete()

            total_deleted += deleted
            total_rewired_settlements += rew_sett
            total_rewired_sells += rew_sell

        self.stdout.write("=" * 100)
        self.stdout.write(f"Done. deleted={total_deleted} rewired_settlements={total_rewired_settlements} rewired_sells={total_rewired_sells}")
