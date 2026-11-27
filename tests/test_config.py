"""YAML config and QADF_* environment variables."""

from decimal import Decimal
from pathlib import Path

import pytest

from qa_data_factory import FactoryConfig


def test_repository_config_loads(monkeypatch):
    monkeypatch.delenv("QADF_CONFIG", raising=False)
    for name in (
        "QADF_SEED",
        "QADF_CUSTOMERS",
        "QADF_ORDERS_PER_CUSTOMER",
        "QADF_LINES_PER_ORDER",
        "QADF_TAX_RATE",
        "QADF_CURRENCY",
    ):
        monkeypatch.delenv(name, raising=False)
    config = FactoryConfig.load(Path("config/factory.yaml"), use_env=False)
    assert config.seed == 42
    assert config.customers == 5
    assert config.orders_per_customer == 2
    assert config.lines_per_order == 2
    assert config.tax_rate == Decimal("0.08")
    assert config.currency == "USD"


def test_environment_overrides_the_file(tmp_path, monkeypatch):
    path = tmp_path / "factory.yaml"
    path.write_text(
        "seed: 42\ncustomers: 5\norders_per_customer: 2\n"
        "lines_per_order: 2\ntax_rate: '0.08'\ncurrency: USD\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("QADF_SEED", "7")
    monkeypatch.setenv("QADF_CUSTOMERS", "3")
    monkeypatch.setenv("QADF_CURRENCY", "eur")
    config = FactoryConfig.load(path)
    assert config.seed == 7
    assert config.customers == 3
    assert config.orders_per_customer == 2
    assert config.currency == "EUR"


def test_qadf_config_points_at_a_file(tmp_path, monkeypatch):
    path = tmp_path / "custom.yaml"
    path.write_text(
        "seed: 9\ncustomers: 1\norders_per_customer: 1\n"
        "lines_per_order: 1\ntax_rate: '0'\ncurrency: GBP\n",
        encoding="utf-8",
    )
    for name in (
        "QADF_SEED",
        "QADF_CUSTOMERS",
        "QADF_ORDERS_PER_CUSTOMER",
        "QADF_LINES_PER_ORDER",
        "QADF_TAX_RATE",
        "QADF_CURRENCY",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("QADF_CONFIG", str(path))
    config = FactoryConfig.load()
    assert config.seed == 9
    assert config.currency == "GBP"
    assert config.tax_rate == Decimal("0")


@pytest.mark.parametrize(
    ("text", "fragment"),
    [
        ("currency: JPY\n", "currency"),
        ("tax_rate: 0.08\n", "float"),
        ("customers: -1\n", "customers"),
        ("lines_per_order: 0\n", "lines_per_order"),
        ("theme: dark\n", "unknown config"),
    ],
)
def test_invalid_config_is_rejected(tmp_path, text, fragment):
    path = tmp_path / "factory.yaml"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError, match=fragment):
        FactoryConfig.load(path, use_env=False)


def test_missing_explicit_file_is_an_error(tmp_path):
    with pytest.raises(FileNotFoundError):
        FactoryConfig.load(tmp_path / "missing.yaml", use_env=False)
