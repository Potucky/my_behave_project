"""Happy-path batches obey the published shape, counts, and formats."""

import re

import pytest

from qa_data_factory import OrderGraphFactory, validate_graph
from qa_data_factory.factory import fictional_us_phone

EMAIL_SHAPE = re.compile(r"^[a-z]+\.[a-z]+\.\d+@example\.com$")
FICTIONAL_PHONE = re.compile(r"^\+1\d{3}55501\d{2}$")
ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ISO_DATETIME = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


def test_phone_sequence_uses_the_reserved_555_block():
    assert fictional_us_phone(1) == "+12025550100"
    assert fictional_us_phone(100) == "+12025550199"
    assert fictional_us_phone(101) == "+12125550100"


def test_generated_batch_passes_the_shared_validator():
    graph = OrderGraphFactory(seed=42).build(
        customers=8,
        orders_per_customer=2,
        lines_per_order=3,
    )
    validate_graph(graph)
    assert graph.seed == 42
    assert graph.currency == "USD"
    assert graph.tax_rate == "0.08"


def test_identifiers_emails_and_phones_follow_the_formats():
    graph = OrderGraphFactory(seed=4).build(
        customers=6,
        orders_per_customer=1,
        lines_per_order=1,
        force_customer_status="active",
    )
    assert [row.customer_id for row in graph.customers] == [
        f"CUS-{index:06d}" for index in range(1, 7)
    ]
    assert [row.order_id for row in graph.orders] == [
        f"ORD-{index:06d}" for index in range(1, 7)
    ]
    for customer in graph.customers:
        assert EMAIL_SHAPE.fullmatch(customer.email or "")
        assert FICTIONAL_PHONE.fullmatch(customer.phone or "")
        assert ISO_DATE.fullmatch(customer.created_at or "")
        assert customer.country == "United States"
    for payment in graph.payments:
        assert ISO_DATETIME.fullmatch(payment.paid_at)
    assert len({row.email for row in graph.customers}) == 6
    assert len({row.phone for row in graph.customers}) == 6


def test_active_customers_receive_the_requested_number_of_orders():
    graph = OrderGraphFactory(seed=8).build(
        customers=4,
        orders_per_customer=3,
        lines_per_order=2,
        force_customer_status="active",
    )
    assert len(graph.orders) == 12
    assert len(graph.lines) == 24
    assert len(graph.invoices) == 12
    lines_per_order: dict[str, int] = {}
    for line in graph.lines:
        lines_per_order[line.order_id] = lines_per_order.get(line.order_id, 0) + 1
    assert set(lines_per_order.values()) == {2}


def test_inactive_customers_do_not_get_orders():
    graph = OrderGraphFactory(seed=8).build(
        customers=4,
        orders_per_customer=3,
        lines_per_order=1,
        force_customer_status="inactive",
    )
    assert graph.customers
    assert graph.orders == ()
    assert graph.lines == ()
    assert graph.payments == ()
    assert graph.invoices == ()


def test_natural_mix_only_orders_for_active_customers():
    graph = OrderGraphFactory(seed=11).build(
        customers=20,
        orders_per_customer=2,
        lines_per_order=1,
    )
    active = {row.customer_id for row in graph.customers if row.status == "active"}
    inactive = {row.customer_id for row in graph.customers if row.status == "inactive"}
    assert active
    assert inactive
    assert {row.customer_id for row in graph.orders} <= active
    assert len(graph.orders) == len(active) * 2


def test_empty_batch_is_valid():
    graph = OrderGraphFactory(seed=1).build(
        customers=0,
        orders_per_customer=0,
        lines_per_order=1,
    )
    validate_graph(graph)
    assert graph.customers == ()


@pytest.mark.parametrize(
    ("status", "expect_payment", "invoice_status"),
    [
        ("pending", False, "open"),
        ("paid", True, "paid"),
        ("shipped", True, "paid"),
        ("cancelled", False, "void"),
    ],
)
def test_order_status_pairs_with_payment_and_invoice(
    status, expect_payment, invoice_status
):
    graph = OrderGraphFactory(seed=5).build(
        customers=3,
        orders_per_customer=1,
        lines_per_order=2,
        force_customer_status="active",
        force_status=status,
    )
    validate_graph(graph)
    assert {row.status for row in graph.orders} == {status}
    assert {row.status for row in graph.invoices} == {invoice_status}
    if expect_payment:
        assert len(graph.payments) == len(graph.orders)
        assert {row.status for row in graph.payments} == {"captured"}
    else:
        assert graph.payments == ()


def test_both_customer_statuses_are_reachable():
    found = set()
    for seed in range(1, 40):
        graph = OrderGraphFactory(seed=seed).build(
            customers=1,
            orders_per_customer=0,
            lines_per_order=1,
        )
        found.add(graph.customers[0].status)
    assert found == {"active", "inactive"}


def test_every_order_status_is_reachable():
    found = set()
    for seed in range(1, 40):
        graph = OrderGraphFactory(seed=seed).build(
            customers=1,
            orders_per_customer=1,
            lines_per_order=1,
            force_customer_status="active",
        )
        found.add(graph.orders[0].status)
    assert found == {"pending", "paid", "shipped", "cancelled"}
