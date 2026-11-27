"""Cent rounding is fixed here so the graph tests are not the only check."""

from decimal import Decimal

from qa_data_factory.money import format_money, order_totals


def test_tax_rounds_half_up_to_the_cent():
    subtotal, tax, total = order_totals([Decimal("10.01")], Decimal("0.08"))
    assert format_money(subtotal) == "10.01"
    assert format_money(tax) == "0.80"
    assert format_money(total) == "10.81"


def test_line_sum_and_tax_on_a_multi_line_order():
    subtotal, tax, total = order_totals(
        [Decimal("19.99"), Decimal("19.99"), Decimal("19.99")],
        Decimal("0.08"),
    )
    assert format_money(subtotal) == "59.97"
    assert format_money(tax) == "4.80"
    assert format_money(total) == "64.77"


def test_zero_tax_rate_keeps_the_subtotal():
    subtotal, tax, total = order_totals([Decimal("8.75")], Decimal("0"))
    assert (format_money(subtotal), format_money(tax), format_money(total)) == (
        "8.75",
        "0.00",
        "8.75",
    )
