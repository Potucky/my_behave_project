"""JSON, CSV, and SQL fixtures contain the same batch the factory built."""

import csv
import json

from qa_data_factory import OrderGraphFactory, export_csv, export_json, export_sql
from qa_data_factory.exporters import sql_literal


def _graph():
    return OrderGraphFactory(seed=15).build(
        customers=3,
        orders_per_customer=1,
        lines_per_order=2,
        force_customer_status="active",
        force_status="paid",
    )


def test_json_export_round_trips_the_graph(tmp_path):
    graph = _graph()
    path = export_json(graph, tmp_path / "order_graph.json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["seed"] == 15
    assert payload["currency"] == "USD"
    assert [row["customer_id"] for row in payload["customers"]] == [
        row.customer_id for row in graph.customers
    ]
    assert payload["orders"][0]["total"] == graph.orders[0].total
    assert payload["order_lines"][0]["sku"] == graph.lines[0].sku
    assert path.read_text(encoding="utf-8").endswith("\n")


def test_csv_export_has_headers_and_one_row_per_record(tmp_path):
    graph = _graph()
    written = export_csv(graph, tmp_path)
    customers = list(csv.DictReader(written["customers"].open(encoding="utf-8")))
    orders = list(csv.DictReader(written["orders"].open(encoding="utf-8")))
    lines = list(csv.DictReader(written["order_lines"].open(encoding="utf-8")))
    payments = list(csv.DictReader(written["payments"].open(encoding="utf-8")))
    invoices = list(csv.DictReader(written["invoices"].open(encoding="utf-8")))
    assert [row["customer_id"] for row in customers] == [
        row.customer_id for row in graph.customers
    ]
    assert len(orders) == len(graph.orders)
    assert len(lines) == len(graph.lines)
    assert len(payments) == len(graph.payments)
    assert len(invoices) == len(graph.invoices)
    assert "email" in customers[0]
    assert customers[0]["email"].endswith("@example.com")


def test_sql_export_inserts_every_customer_and_escapes_quotes(tmp_path):
    graph = _graph()
    path = export_sql(graph, tmp_path / "seed.sql")
    script = path.read_text(encoding="utf-8")
    assert script.startswith("-- Fictional fixture data")
    for customer in graph.customers:
        assert f"INSERT INTO customers (" in script
        assert sql_literal(customer.customer_id) in script
        assert sql_literal(customer.email) in script
    assert "INSERT INTO orders (" in script
    assert "INSERT INTO order_lines (" in script
    assert "INSERT INTO payments (" in script
    assert "INSERT INTO invoices (" in script
    assert sql_literal("O'Brien") == "'O''Brien'"
    assert sql_literal(None) == "NULL"
    assert sql_literal(21) == "21"


def test_empty_csv_still_writes_a_header(tmp_path):
    graph = OrderGraphFactory(seed=1).build(
        customers=0,
        orders_per_customer=0,
        lines_per_order=1,
    )
    written = export_csv(graph, tmp_path)
    header = written["customers"].read_text(encoding="utf-8").splitlines()
    assert header == [
        "customer_id,first_name,last_name,email,phone,created_at,city,country,status"
    ]
