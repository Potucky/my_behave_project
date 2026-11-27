"""The sample fixtures committed for the README are a real factory build."""

from pathlib import Path

from qa_data_factory import OrderGraphFactory, export_csv, export_json, export_sql

SAMPLE = Path("examples/sample")


def test_readme_sample_matches_seed_42(tmp_path):
    graph = OrderGraphFactory(seed=42).build(
        customers=2,
        orders_per_customer=1,
        lines_per_order=2,
    )
    export_json(graph, tmp_path / "order_graph.json")
    export_csv(graph, tmp_path)
    export_sql(graph, tmp_path / "seed.sql")

    assert (tmp_path / "order_graph.json").read_text(encoding="utf-8") == (
        SAMPLE / "order_graph.json"
    ).read_text(encoding="utf-8")
    for name in ("customers", "orders", "order_lines", "payments", "invoices"):
        assert (tmp_path / f"{name}.csv").read_text(encoding="utf-8") == (
            SAMPLE / f"{name}.csv"
        ).read_text(encoding="utf-8")
    assert (tmp_path / "seed.sql").read_text(encoding="utf-8") == (
        SAMPLE / "seed.sql"
    ).read_text(encoding="utf-8")
