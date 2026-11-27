"""Write a graph to JSON, CSV, or SQL INSERT statements.

The SQL is a local fixture script: identifiers are fixed table names and
string values are single-quoted. It is not a general SQL builder.
"""

import csv
import json
from dataclasses import fields
from pathlib import Path

from qa_data_factory.models import (
    Customer,
    Invoice,
    Order,
    OrderGraph,
    OrderLine,
    Payment,
)

_TABLES: tuple[tuple[str, str, type], ...] = (
    ("customers", "customers", Customer),
    ("orders", "orders", Order),
    ("order_lines", "lines", OrderLine),
    ("payments", "payments", Payment),
    ("invoices", "invoices", Invoice),
)


def export_json(graph: OrderGraph, path: str | Path) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(graph.to_dict(), indent=2) + "\n"
    destination.write_text(payload, encoding="utf-8")
    return destination


def export_csv(graph: OrderGraph, directory: str | Path) -> dict[str, Path]:
    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=True)
    written: dict[str, Path] = {}
    for table, attr, row_type in _TABLES:
        path = folder / f"{table}.csv"
        rows = getattr(graph, attr)
        _write_csv(path, rows, row_type)
        written[table] = path
    return written


def export_sql(graph: OrderGraph, path: str | Path) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    chunks = [
        "-- Fictional fixture data from qa_data_factory.",
        "-- Local test fixtures only.",
        f"-- seed={graph.seed}",
        "",
    ]
    for table, attr, _row_type in _TABLES:
        for row in getattr(graph, attr):
            data = row.to_dict()
            columns = ", ".join(data)
            values = ", ".join(sql_literal(value) for value in data.values())
            chunks.append(f"INSERT INTO {table} ({columns}) VALUES ({values});")
        chunks.append("")
    destination.write_text("\n".join(chunks).rstrip() + "\n", encoding="utf-8")
    return destination


def sql_literal(value: object) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, int):
        return str(value)
    text = str(value).replace("'", "''")
    return f"'{text}'"


def _write_csv(path: Path, rows: tuple, row_type: type) -> None:
    fieldnames = [field.name for field in fields(row_type)]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            record = row.to_dict()
            writer.writerow(
                {key: "" if record[key] is None else record[key] for key in fieldnames}
            )
