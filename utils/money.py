# utils/money.py
from decimal import Decimal, ROUND_HALF_UP

MONEY = Decimal("0.01")
ROUNDING = ROUND_HALF_UP


def D(x, default="0.00") -> Decimal:
    if x is None:
        return Decimal(default)
    if isinstance(x, Decimal):
        return x
    return Decimal(str(x))


def money(x, default="0.00") -> Decimal:
    return D(x, default=default).quantize(MONEY, rounding=ROUNDING)


def money_sum(values, default="0.00") -> Decimal:
    total = Decimal("0.00")
    for v in values:
        total += D(v, default=default)
    return total
