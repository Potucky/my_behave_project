"""Cent-accurate money helpers used by the factory and the validators."""

from decimal import Decimal, ROUND_HALF_UP

TWOPLACES = Decimal("0.01")


def quantize_money(value: Decimal) -> Decimal:
    return value.quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def format_money(value: Decimal) -> str:
    return f"{quantize_money(value):.2f}"


def format_rate(value: Decimal) -> str:
    """Stable, non-scientific text for a tax rate such as 0.08."""
    return format(value, "f")


def line_total(unit_price: Decimal, quantity: int) -> Decimal:
    return quantize_money(unit_price * quantity)


def order_totals(
    line_totals: list[Decimal], tax_rate: Decimal
) -> tuple[Decimal, Decimal, Decimal]:
    subtotal = quantize_money(sum(line_totals, Decimal("0.00")))
    tax = quantize_money(subtotal * tax_rate)
    total = quantize_money(subtotal + tax)
    return subtotal, tax, total
