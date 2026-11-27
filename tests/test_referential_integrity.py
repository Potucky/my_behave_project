"""Foreign keys resolve, and money is recomputed from the catalog."""

from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal

import pytest

from qa_data_factory import ConstraintError, OrderGraphFactory, validate_graph
from qa_data_factory.catalog import PRODUCTS_BY_SKU
from qa_data_factory.money import format_money, order_totals


def _graph():
    return OrderGraphFactory(seed=21).build(
        customers=6,
        orders_per_customer=2,
        lines_per_order=3,
        force_customer_status="active",
    )


def test_foreign_keys_point_at_rows_in_the_same_batch():
    graph = _graph()
    validate_graph(graph)
    customer_ids = {row.customer_id for row in graph.customers}
    order_ids = {row.order_id for row in graph.orders}
    assert customer_ids
    assert all(row.customer_id in customer_ids for row in graph.orders)
    assert all(row.order_id in order_ids for row in graph.lines)
    assert all(row.order_id in order_ids for row in graph.payments)
    assert all(row.order_id in order_ids for row in graph.invoices)
    assert len({row.customer_id for row in graph.customers}) == len(graph.customers)
    assert len({row.order_id for row in graph.orders}) == len(graph.orders)
    assert len({row.line_id for row in graph.lines}) == len(graph.lines)
    assert len({row.invoice_number for row in graph.invoices}) == len(graph.invoices)


def test_lines_copy_the_catalog_and_order_totals_follow_the_lines():
    graph = _graph()
    tax_rate = Decimal(graph.tax_rate)
    lines_by_order: dict[str, list] = {}
    for line in graph.lines:
        product = PRODUCTS_BY_SKU[line.sku]
        assert line.product_name == product.name
        assert Decimal(line.unit_price) == product.unit_price
        assert 1 <= line.quantity <= 20
        lines_by_order.setdefault(line.order_id, []).append(line)

    orders = {row.order_id: row for row in graph.orders}
    for order_id, lines in lines_by_order.items():
        subtotal, tax, total = order_totals(
            [Decimal(line.line_total) for line in lines], tax_rate
        )
        order = orders[order_id]
        assert order.subtotal == format_money(subtotal)
        assert order.tax == format_money(tax)
        assert order.total == format_money(total)


def test_dates_and_invoice_terms_line_up():
    graph = _graph()
    customers = {row.customer_id: row for row in graph.customers}
    invoices = {row.order_id: row for row in graph.invoices}
    payments = {row.order_id: row for row in graph.payments}
    for order in graph.orders:
        created = date.fromisoformat(customers[order.customer_id].created_at or "")
        ordered = date.fromisoformat(order.order_date)
        assert created <= ordered
        invoice = invoices[order.order_id]
        assert invoice.issued_at == order.order_date
        assert date.fromisoformat(invoice.due_at) == ordered + timedelta(days=30)
        assert invoice.amount == order.total
        if order.status in {"paid", "shipped"}:
            payment = payments[order.order_id]
            assert payment.amount == order.total
            assert payment.paid_at.startswith(order.order_date + "T")
        else:
            assert order.order_id not in payments


def test_changed_catalog_price_is_rejected():
    graph = _graph()
    broken_line = replace(graph.lines[0], unit_price="0.01")
    broken = replace(graph, lines=(broken_line,) + graph.lines[1:])
    with pytest.raises(ConstraintError, match="unit_price"):
        validate_graph(broken)


def test_invoice_term_must_be_thirty_days():
    graph = _graph()
    invoice = graph.invoices[0]
    broken_invoice = replace(invoice, due_at=invoice.issued_at)
    broken = replace(graph, invoices=(broken_invoice,) + graph.invoices[1:])
    with pytest.raises(ConstraintError, match="due_at"):
        validate_graph(broken)
