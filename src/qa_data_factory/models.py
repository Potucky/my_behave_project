"""Records produced by the factory.

Money is stored as a two-decimal string so JSON, CSV, and SQL fixtures
round-trip without binary float error. Dates are ISO-8601 strings.
"""

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Customer:
    customer_id: str
    first_name: str
    last_name: str
    email: str | None
    phone: str | None
    created_at: str | None
    city: str
    country: str
    status: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class Order:
    order_id: str
    customer_id: str
    order_date: str
    status: str
    currency: str
    subtotal: str
    tax: str
    total: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class OrderLine:
    line_id: str
    order_id: str
    sku: str
    product_name: str
    quantity: int
    unit_price: str
    line_total: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class Payment:
    payment_id: str
    order_id: str
    amount: str
    method: str
    paid_at: str
    status: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class Invoice:
    invoice_id: str
    order_id: str
    invoice_number: str
    issued_at: str
    due_at: str
    amount: str
    status: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class OrderGraph:
    """One consistent batch: customers and the orders that belong to them."""

    seed: int
    tax_rate: str
    currency: str
    customers: tuple[Customer, ...]
    orders: tuple[Order, ...]
    lines: tuple[OrderLine, ...]
    payments: tuple[Payment, ...]
    invoices: tuple[Invoice, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "seed": self.seed,
            "tax_rate": self.tax_rate,
            "currency": self.currency,
            "customers": [row.to_dict() for row in self.customers],
            "orders": [row.to_dict() for row in self.orders],
            "order_lines": [row.to_dict() for row in self.lines],
            "payments": [row.to_dict() for row in self.payments],
            "invoices": [row.to_dict() for row in self.invoices],
        }
