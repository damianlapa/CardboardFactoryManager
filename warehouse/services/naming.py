# warehouse/services/naming.py
import re


def norm_spaces(s: str) -> str:
    return " ".join((s or "").strip().split())


def norm_dimensions(dim: str) -> str:
    d = norm_spaces(dim).lower().replace(" ", "")
    d = d.replace("*", "x")
    d = re.sub(r"[xX]+", "x", d)
    return d


def build_product_name(customer: str, flute: str, dimensions: str, extra: str = "") -> str:
    customer = norm_spaces(customer).upper()
    flute = norm_spaces(flute).upper()
    dimensions = norm_dimensions(dimensions)
    extra = norm_spaces(extra).upper()

    parts = [customer, flute, dimensions]
    if extra:
        parts.append(extra)

    return " | ".join(parts)
