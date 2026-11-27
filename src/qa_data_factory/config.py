"""Factory settings from a YAML file, with optional environment overrides.

No credentials are read. The variables only size the batch and choose the seed.
"""

import os
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

import yaml

from qa_data_factory.constraints import CURRENCIES

ENV_KEYS = {
    "QADF_SEED": "seed",
    "QADF_CUSTOMERS": "customers",
    "QADF_ORDERS_PER_CUSTOMER": "orders_per_customer",
    "QADF_LINES_PER_ORDER": "lines_per_order",
    "QADF_TAX_RATE": "tax_rate",
    "QADF_CURRENCY": "currency",
}


@dataclass(frozen=True)
class FactoryConfig:
    seed: int = 42
    customers: int = 5
    orders_per_customer: int = 2
    lines_per_order: int = 2
    tax_rate: Decimal = Decimal("0.08")
    currency: str = "USD"

    def validate(self) -> None:
        if self.customers < 0:
            raise ValueError("customers must be >= 0")
        if self.orders_per_customer < 0:
            raise ValueError("orders_per_customer must be >= 0")
        if self.lines_per_order < 1:
            raise ValueError("lines_per_order must be >= 1")
        if self.tax_rate < 0 or self.tax_rate > 1:
            raise ValueError("tax_rate must be between 0 and 1")
        if self.currency not in CURRENCIES:
            raise ValueError(f"currency must be one of {', '.join(sorted(CURRENCIES))}")

    @classmethod
    def from_mapping(cls, data: dict[str, object]) -> "FactoryConfig":
        known = {
            "seed",
            "customers",
            "orders_per_customer",
            "lines_per_order",
            "tax_rate",
            "currency",
        }
        unexpected = sorted(set(data) - known)
        if unexpected:
            raise ValueError(f"unknown config keys: {', '.join(unexpected)}")
        values: dict[str, object] = {}
        for field in ("seed", "customers", "orders_per_customer", "lines_per_order"):
            if field in data:
                values[field] = _as_int(data[field], field)
        if "tax_rate" in data:
            values["tax_rate"] = _as_decimal(data["tax_rate"], "tax_rate")
        if "currency" in data:
            currency = data["currency"]
            if not isinstance(currency, str) or not currency.strip():
                raise ValueError("currency must be a string")
            values["currency"] = currency.strip().upper()
        config = cls(**values)  # type: ignore[arg-type]
        config.validate()
        return config

    @classmethod
    def load(cls, path: str | Path | None = None, *, use_env: bool = True) -> "FactoryConfig":
        """Load YAML, then let QADF_* environment variables replace those keys."""
        if path is None and use_env and os.environ.get("QADF_CONFIG"):
            path = os.environ["QADF_CONFIG"]
        config_path = Path(path) if path is not None else Path("config/factory.yaml")
        raw: dict[str, object] = {}
        if config_path.is_file():
            loaded = yaml.safe_load(config_path.read_text(encoding="utf-8"))
            if loaded is None:
                loaded = {}
            if not isinstance(loaded, dict):
                raise ValueError("config root must be a mapping")
            raw = dict(loaded)
        elif path is not None:
            raise FileNotFoundError(f"config file not found: {config_path}")
        if use_env:
            for env_name, key in ENV_KEYS.items():
                if os.environ.get(env_name, "") != "":
                    raw[key] = os.environ[env_name]
        return cls.from_mapping(raw)


def _as_int(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise ValueError(f"{field} must be an integer")
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"{field} must be an integer") from exc


def _as_decimal(value: object, field: str) -> Decimal:
    if isinstance(value, float) or isinstance(value, bool):
        raise ValueError(f"{field} must be a string or integer, not a float")
    if not isinstance(value, (int, str, Decimal)):
        raise ValueError(f"{field} must be a string or integer")
    try:
        return Decimal(str(value))
    except Exception as exc:
        raise ValueError(f"{field} must be a decimal") from exc
