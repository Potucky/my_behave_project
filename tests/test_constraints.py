"""The rules accept a hand-written valid customer and reject broken fields."""

from dataclasses import replace

import pytest

from qa_data_factory import ConstraintError, Customer, validate_customer
from qa_data_factory.constraints import parse_iso_date, parse_money


def valid_customer() -> Customer:
    return Customer(
        customer_id="CUS-000001",
        first_name="Ada",
        last_name="Lovelace",
        email="ada.lovelace.1@example.com",
        phone="+13055550100",
        created_at="2024-03-15",
        city="Miami",
        country="United States",
        status="active",
    )


def test_hand_written_customer_is_valid():
    validate_customer(valid_customer())


@pytest.mark.parametrize(
    ("field", "value", "fragment"),
    [
        ("email", "not-an-email", "example.com"),
        ("email", "Ada.Lovelace.1@example.com", "example.com"),
        ("email", "ada.lovelace.1@gmail.com", "example.com"),
        ("email", None, "is required"),
        ("phone", "555-0100", "E.164"),
        ("phone", "+0123", "E.164"),
        ("created_at", "2024-02-31", "real calendar date"),
        ("created_at", "03/15/2024", "ISO date"),
        ("created_at", None, "is required"),
        ("status", "archived", "must be one of"),
        ("customer_id", "CUST-1", "CUS-000000"),
    ],
)
def test_customer_field_rules(field, value, fragment):
    broken = replace(valid_customer(), **{field: value})
    with pytest.raises(ConstraintError, match=fragment) as caught:
        validate_customer(broken)
    assert caught.value.field == field


def test_iso_date_accepts_a_real_calendar_day():
    assert parse_iso_date("2024-02-29", "created_at").isoformat() == "2024-02-29"


def test_money_requires_two_decimal_places():
    assert parse_money("10.01", "amount") == parse_money("10.01", "amount")
    with pytest.raises(ConstraintError, match="2 places"):
        parse_money("10", "amount")
    with pytest.raises(ConstraintError, match="2 places"):
        parse_money("10.1", "amount")
