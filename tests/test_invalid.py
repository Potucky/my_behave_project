"""Each negative fixture breaks one named rule."""

from decimal import Decimal

import pytest

from qa_data_factory import (
    ConstraintError,
    InvalidDataFactory,
    OrderGraphFactory,
    validate_graph,
)
from qa_data_factory.money import format_money, line_total


@pytest.mark.parametrize(
    ("violation", "fragment"),
    [
        ("email_format", "example.com"),
        ("phone_format", "E.164"),
        ("missing_required", "is required"),
        ("bad_date", "real calendar date"),
        ("duplicate_customer_id", "duplicate"),
        ("orphan_foreign_key", "no matching customer"),
        ("quantity_range", "must be from 1 to 20"),
        ("total_mismatch", "must equal the order total"),
    ],
)
def test_single_violation_is_rejected(violation, fragment):
    graph = InvalidDataFactory(seed=3).build(violation)
    with pytest.raises(ConstraintError, match=fragment):
        validate_graph(graph)


def test_the_unmodified_batch_is_accepted():
    graph = OrderGraphFactory(seed=3).build(
        customers=2,
        orders_per_customer=1,
        lines_per_order=1,
        force_customer_status="active",
        force_status="paid",
    )
    validate_graph(graph)


def test_unknown_violation_is_rejected():
    with pytest.raises(ValueError, match="unknown violation"):
        InvalidDataFactory(seed=1).build("drop_table")


def test_quantity_violation_keeps_a_consistent_line_total():
    graph = InvalidDataFactory(seed=3).build("quantity_range")
    line = graph.lines[0]
    assert line.quantity == 21
    assert line.line_total == format_money(line_total(Decimal(line.unit_price), 21))
