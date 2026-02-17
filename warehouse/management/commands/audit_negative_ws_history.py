import datetime
from typing import Optional

from django.core.management.base import BaseCommand

from warehouse.models import WarehouseStock, WarehouseStockHistory


class Command(BaseCommand):
    help = "Znajduje WarehouseStock, dla których symulacja historii (delta) schodzi poniżej 0 i wypisuje pełną historię."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=50, help="Ile WS wypisać (domyślnie 50).")
        parser.add_argument("--ws-id", type=int, default=None, help="Tylko jeden WarehouseStock id (opcjonalnie).")
        parser.add_argument("--max-rows", type=int, default=None, help="Limit wierszy historii na WS (opcjonalnie).")
        parser.add_argument("--from-date", type=str, default=None, help="Filtruj historię od daty YYYY-MM-DD (opcjonalnie).")
        parser.add_argument("--to-date", type=str, default=None, help="Filtruj historię do daty YYYY-MM-DD (opcjonalnie).")
        parser.add_argument("--only-negative", action="store_true", help="Wypisuj tylko wiersze, gdzie calc_after < 0.")
        parser.add_argument("--show-ok-prefix", action="store_true", help="Pokaż też wiersze przed pierwszym zejściem < 0.")
        parser.add_argument("--verbose", action="store_true", help="Dodatkowe info (min_running, first_negative).")

    def handle(self, *args, **opts):
        limit_ws = opts["limit"]
        ws_id = opts["ws_id"]
        max_rows = opts["max_rows"]
        only_negative = opts["only_negative"]
        show_ok_prefix = opts["show_ok_prefix"]
        verbose = opts["verbose"]

        from_date = self._parse_date(opts["from_date"])
        to_date = self._parse_date(opts["to_date"])

        qs = (
            WarehouseStock.objects
            .select_related("warehouse", "stock", "stock__stock_type")
            .order_by("id")
        )
        if ws_id:
            qs = qs.filter(id=ws_id)

        found = 0
        checked = 0

        self.stdout.write("=== AUDIT NEGATIVE WS HISTORY (delta simulation, start=0) ===")
        if from_date or to_date:
            self.stdout.write(f"Range: {from_date or '-inf'} .. {to_date or '+inf'}")
        self.stdout.write("")

        for ws in qs.iterator():
            checked += 1

            hqs = (
                WarehouseStockHistory.objects
                .filter(warehouse_stock=ws)
                .order_by("date", "id")
            )
            if from_date:
                hqs = hqs.filter(date__gte=from_date)
            if to_date:
                hqs = hqs.filter(date__lte=to_date)

            rows = list(hqs.values(
                "id", "date", "delta",
                "quantity_before", "quantity_after",
                "sell_id", "order_settlement_id", "stock_supply_id", "assembly_id",
            ))

            if not rows:
                continue

            # symulacja: running od 0
            running = 0
            min_running = 0
            first_negative_idx: Optional[int] = None

            calc = []
            for idx, r in enumerate(rows):
                d = int(r["delta"] or 0)
                calc_before = running
                calc_after = running + d
                running = calc_after

                if calc_after < min_running:
                    min_running = calc_after
                if first_negative_idx is None and calc_after < 0:
                    first_negative_idx = idx

                calc.append((calc_before, calc_after))

            if first_negative_idx is None:
                continue  # OK, nigdy nie schodzi poniżej 0

            found += 1
            if found > limit_ws:
                break

            # Nagłówek WS
            self.stdout.write("--------------------------------------------------------------------------------")
            self.stdout.write(
                f"[{found}] WS id={ws.id} | wh='{ws.warehouse.name}' | stock_type_id={ws.stock.stock_type_id} | name='{ws.stock.name}' | ws.quantity(now)={ws.quantity}"
            )
            if verbose:
                self.stdout.write(f"    min_running={min_running} | first_negative_row_index={first_negative_idx+1}")

            self.stdout.write("    HISTORY:")
            self.stdout.write("    # | date       | delta | DB(before->after) | CALC(before->after) | refs")
            self.stdout.write("    --+------------+-------+------------------+---------------------+-----------------------------")

            start_idx = 0
            if not show_ok_prefix:
                start_idx = first_negative_idx  # pokaż od pierwszego zejścia <0
            shown = 0

            for i in range(start_idx, len(rows)):
                r = rows[i]
                calc_before, calc_after = calc[i]

                if only_negative and calc_after >= 0:
                    continue

                refs = []
                if r["sell_id"]:
                    refs.append(f"sell={r['sell_id']}")
                if r["order_settlement_id"]:
                    refs.append(f"settle={r['order_settlement_id']}")
                if r["stock_supply_id"]:
                    refs.append(f"supply={r['stock_supply_id']}")
                if r["assembly_id"]:
                    refs.append(f"assembly={r['assembly_id']}")
                refs_s = ", ".join(refs) if refs else "-"

                flag = "  !!!" if calc_after < 0 else ""
                self.stdout.write(
                    f"    {i+1:>2} | {r['date']} | {int(r['delta'] or 0):>5} | "
                    f"{int(r['quantity_before'] or 0):>6}->{int(r['quantity_after'] or 0):<6} | "
                    f"{calc_before:>6}->{calc_after:<6} | {refs_s}{flag}"
                )

                shown += 1
                if max_rows and shown >= max_rows:
                    self.stdout.write(f"    ... (cut after {max_rows} rows)")
                    break

        self.stdout.write("")
        self.stdout.write(f"Checked WS: {checked}")
        self.stdout.write(f"Found negative histories: {found}")
        self.stdout.write("=== END ===")

    @staticmethod
    def _parse_date(s: Optional[str]) -> Optional[datetime.date]:
        if not s:
            return None
        return datetime.date.fromisoformat(s)
