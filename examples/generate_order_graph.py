"""Generate a fictional order graph and write JSON, CSV, and SQL fixtures.

Run from the repository root:

    PYTHONPATH=src python examples/generate_order_graph.py
"""

import argparse
from pathlib import Path

from qa_data_factory import (
    FactoryConfig,
    OrderGraphFactory,
    export_csv,
    export_json,
    export_sql,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="YAML settings. Defaults to config/factory.yaml, then QADF_* env vars.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("examples/output"),
        help="Directory for order_graph.json, the CSV files, and seed.sql.",
    )
    args = parser.parse_args()
    config = FactoryConfig.load(args.config)
    graph = OrderGraphFactory(config=config).build()
    export_json(graph, args.out / "order_graph.json")
    export_csv(graph, args.out)
    export_sql(graph, args.out / "seed.sql")
    print(
        f"seed={graph.seed} customers={len(graph.customers)} "
        f"orders={len(graph.orders)} lines={len(graph.lines)} "
        f"payments={len(graph.payments)} invoices={len(graph.invoices)}"
    )
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
