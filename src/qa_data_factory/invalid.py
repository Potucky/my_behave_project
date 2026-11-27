"""Graphs that break one published rule and leave the others intact.

Negative tests import these instead of hand-editing a fixture in the test
body, so the broken field stays obvious.
"""

from dataclasses import replace
from decimal import Decimal

from qa_data_factory.config import FactoryConfig
from qa_data_factory.constraints import QUANTITY_MAX
from qa_data_factory.factory import OrderGraphFactory
from qa_data_factory.models import OrderGraph
from qa_data_factory.money import format_money, line_total, order_totals

VIOLATIONS: tuple[str, ...] = (
    "email_format",
    "phone_format",
    "missing_required",
    "bad_date",
    "duplicate_customer_id",
    "orphan_foreign_key",
    "quantity_range",
    "total_mismatch",
)


class InvalidDataFactory:
    """Start from a valid seeded graph and inject a single defect."""

    def __init__(self, seed: int = 1, config: FactoryConfig | None = None) -> None:
        self.seed = seed
        self.config = config

    def build(self, violation: str) -> OrderGraph:
        if violation not in VIOLATIONS:
            known = ", ".join(VIOLATIONS)
            raise ValueError(f"unknown violation {violation!r}; expected one of {known}")
        factory = OrderGraphFactory(seed=self.seed, config=self.config)
        graph = factory.build(
            customers=2,
            orders_per_customer=1,
            lines_per_order=1,
            force_customer_status="active",
            force_status="paid" if violation == "total_mismatch" else "pending",
        )
        return _apply(graph, violation)


def _apply(graph: OrderGraph, violation: str) -> OrderGraph:
    if violation == "email_format":
        return _replace_customer(graph, 0, email="not-an-email")
    if violation == "phone_format":
        return _replace_customer(graph, 0, phone="555-0100")
    if violation == "missing_required":
        return _replace_customer(graph, 0, email=None)
    if violation == "bad_date":
        return _replace_order(graph, 0, order_date="2024-02-31")
    if violation == "duplicate_customer_id":
        return _replace_customer(
            graph, 1, customer_id=graph.customers[0].customer_id
        )
    if violation == "orphan_foreign_key":
        return _replace_order(graph, 0, customer_id="CUS-000000")
    if violation == "quantity_range":
        return _quantity_above_max(graph)
    if violation == "total_mismatch":
        return _payment_amount_mismatch(graph)
    raise ValueError(violation)


def _replace_customer(graph: OrderGraph, index: int, **changes: object) -> OrderGraph:
    updated = replace(graph.customers[index], **changes)
    customers = graph.customers[:index] + (updated,) + graph.customers[index + 1 :]
    return replace(graph, customers=customers)


def _replace_order(graph: OrderGraph, index: int, **changes: object) -> OrderGraph:
    updated = replace(graph.orders[index], **changes)
    orders = graph.orders[:index] + (updated,) + graph.orders[index + 1 :]
    return replace(graph, orders=orders)


def _quantity_above_max(graph: OrderGraph) -> OrderGraph:
    """Quantity 21 breaks the range. Totals are recomputed so they still add up."""
    quantity = QUANTITY_MAX + 1
    target = graph.lines[0]
    unit_price = Decimal(target.unit_price)
    updated_line = replace(
        target,
        quantity=quantity,
        line_total=format_money(line_total(unit_price, quantity)),
    )
    lines = (updated_line,) + graph.lines[1:]
    return _sync_order_amounts(replace(graph, lines=lines), target.order_id)


def _sync_order_amounts(graph: OrderGraph, order_id: str) -> OrderGraph:
    related = [row for row in graph.lines if row.order_id == order_id]
    subtotal, tax, total = order_totals(
        [Decimal(row.line_total) for row in related], Decimal(graph.tax_rate)
    )
    orders = tuple(
        replace(
            order,
            subtotal=format_money(subtotal),
            tax=format_money(tax),
            total=format_money(total),
        )
        if order.order_id == order_id
        else order
        for order in graph.orders
    )
    amount = format_money(total)
    payments = tuple(
        replace(payment, amount=amount) if payment.order_id == order_id else payment
        for payment in graph.payments
    )
    invoices = tuple(
        replace(invoice, amount=amount) if invoice.order_id == order_id else invoice
        for invoice in graph.invoices
    )
    return replace(graph, orders=orders, payments=payments, invoices=invoices)


def _payment_amount_mismatch(graph: OrderGraph) -> OrderGraph:
    payment = graph.payments[0]
    wrong = "0.01" if payment.amount != "0.01" else "0.02"
    updated = replace(payment, amount=wrong)
    return replace(graph, payments=(updated,) + graph.payments[1:])
