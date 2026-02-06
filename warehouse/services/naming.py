# warehouse/services/naming.py
import re


def norm_spaces(s: str) -> str:
    return " ".join((s or "").strip().split())


def norm_dimensions(dim: str) -> str:
    d = norm_spaces(dim).lower().replace(" ", "")
    d = d.replace("*", "x")
    d = re.sub(r"[xX]+", "x", d)
    return d


def norm_names(name: str) -> str:
    parts = name.split('|')
    parts = list(map(lambda x: x.strip(), parts))
    parts[2] = parts[2].lower() if not "komplet" in parts[2].lower() else parts[2]
    return " | ".join(parts)


def build_product_name(customer: str, flute: str, dimensions: str, extra: str = "") -> str:
    customer = norm_spaces(customer).upper()
    flute = norm_spaces(flute).upper()
    dimensions = norm_dimensions(dimensions).lower()
    extra = norm_spaces(extra).upper()

    parts = [customer, flute, dimensions]
    if extra:
        parts.append(extra)

    return " | ".join(parts)
