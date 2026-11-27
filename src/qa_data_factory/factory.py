"""Build a customer/order/payment/invoice graph from one seed.

The same seed and the same counts always return the same records. Nothing
in this module reads the clock or the network.
"""

import random
import re
from datetime import date, timedelta
from decimal import Decimal

from faker import Faker

from qa_data_factory.catalog import CATALOG
from qa_data_factory.config import FactoryConfig
from qa_data_factory.constraints import (
    INVOICE_STATUS_BY_ORDER,
    ORDER_STATUSES,
    PAID_ORDER_STATUSES,
    QUANTITY_MAX,
    QUANTITY_MIN,
    validate_graph,
)
from qa_data_factory.models import (
    Customer,
    Invoice,
    Order,
    OrderGraph,
    OrderLine,
    Payment,
)
from qa_data_factory.money import format_money, format_rate, line_total, order_totals

# Fixed calendar so a seed does not depend on the day the suite runs.
EPOCH = date(2024, 1, 1)
LOCALE = "en_US"

# NANP area codes paired with the reserved 555-0100 through 555-0199 line
# numbers. Those line numbers are not assigned to real subscribers.
_AREA_CODES: tuple[str, ...] = (
    "202",
    "212",
    "305",
    "312",
    "404",
    "415",
    "503",
    "617",
    "646",
    "702",
    "713",
    "786",
)
MAX_CUSTOMERS = len(_AREA_CODES) * 100

_ORDER_STATUS_CHOICES = ("pending", "paid", "shipped", "cancelled")
_PAYMENT_METHODS = ("card", "paypal", "bank_transfer")


def fictional_us_phone(sequence: int) -> str:
    """Return a unique E.164 phone in the fictional 555-01xx range."""
    if sequence < 1:
        raise ValueError("phone sequence starts at 1")
    index = sequence - 1
    if index >= MAX_CUSTOMERS:
        raise ValueError(f"at most {MAX_CUSTOMERS} customers per batch")
    area = _AREA_CODES[index // 100]
    line = 100 + (index % 100)
    return f"+1{area}555{line:04d}"


def _slug(value: str) -> str:
    cleaned = re.sub(r"[^a-z]", "", value.lower())
    return cleaned or "user"


def _email(first_name: str, last_name: str, sequence: int) -> str:
    return f"{_slug(first_name)}.{_slug(last_name)}.{sequence}@example.com"


def _identifier(prefix: str, sequence: int) -> str:
    return f"{prefix}-{sequence:06d}"


class OrderGraphFactory:
    """Create one referentially consistent order graph.

    ``force_customer_status`` and ``force_status`` pin every row to one
    status. Tests use them when they need a known state. The seed still
    draws the unused status so the rest of the batch stays put.
    """

    def __init__(
        self, seed: int | None = None, config: FactoryConfig | None = None
    ) -> None:
        self.config = config or FactoryConfig()
        self.seed = self.config.seed if seed is None else seed

    def build(
        self,
        *,
        customers: int | None = None,
        orders_per_customer: int | None = None,
        lines_per_order: int | None = None,
        force_customer_status: str | None = None,
        force_status: str | None = None,
    ) -> OrderGraph:
        self.config.validate()
        customer_count = self.config.customers if customers is None else customers
        order_count = (
            self.config.orders_per_customer
            if orders_per_customer is None
            else orders_per_customer
        )
        line_count = (
            self.config.lines_per_order if lines_per_order is None else lines_per_order
        )
        _check_counts(customer_count, order_count, line_count)
        if force_customer_status not in (None, "active", "inactive"):
            raise ValueError("force_customer_status must be active or inactive")
        if force_status is not None and force_status not in ORDER_STATUSES:
            raise ValueError("force_status is not an order status")

        rng = random.Random(self.seed)
        faker = Faker(LOCALE)
        faker.seed_instance(self.seed)

        built_customers = tuple(
            _build_customer(sequence, rng, faker, force_customer_status)
            for sequence in range(1, customer_count + 1)
        )
        orders, lines, payments, invoices = _build_orders(
            built_customers,
            orders_per_customer=order_count,
            lines_per_order=line_count,
            tax_rate=self.config.tax_rate,
            currency=self.config.currency,
            rng=rng,
            force_status=force_status,
        )
        graph = OrderGraph(
            seed=self.seed,
            tax_rate=format_rate(self.config.tax_rate),
            currency=self.config.currency,
            customers=built_customers,
            orders=tuple(orders),
            lines=tuple(lines),
            payments=tuple(payments),
            invoices=tuple(invoices),
        )
        validate_graph(graph)
        return graph


def _check_counts(customers: int, orders_per_customer: int, lines_per_order: int) -> None:
    if customers < 0 or customers > MAX_CUSTOMERS:
        raise ValueError(f"customers must be from 0 to {MAX_CUSTOMERS}")
    if orders_per_customer < 0:
        raise ValueError("orders_per_customer must be >= 0")
    if lines_per_order < 1:
        raise ValueError("lines_per_order must be >= 1")


def _build_customer(
    sequence: int,
    rng: random.Random,
    faker: Faker,
    force_customer_status: str | None,
) -> Customer:
    first_name = faker.first_name()
    last_name = faker.last_name()
    created = EPOCH + timedelta(days=rng.randint(0, 500))
    rolled = rng.randrange(5)
    status = force_customer_status or ("inactive" if rolled == 0 else "active")
    return Customer(
        customer_id=_identifier("CUS", sequence),
        first_name=first_name,
        last_name=last_name,
        email=_email(first_name, last_name, sequence),
        phone=fictional_us_phone(sequence),
        created_at=created.isoformat(),
        city=faker.city(),
        country="United States",
        status=status,
    )


def _build_orders(
    customers: tuple[Customer, ...],
    *,
    orders_per_customer: int,
    lines_per_order: int,
    tax_rate: Decimal,
    currency: str,
    rng: random.Random,
    force_status: str | None,
) -> tuple[list[Order], list[OrderLine], list[Payment], list[Invoice]]:
    orders: list[Order] = []
    lines: list[OrderLine] = []
    payments: list[Payment] = []
    invoices: list[Invoice] = []
    order_sequence = 0
    line_sequence = 0
    payment_sequence = 0
    invoice_sequence = 0

    for customer in customers:
        if customer.status != "active":
            continue
        created_at = customer.created_at
        if created_at is None:
            raise ValueError("customer created_at is required")
        created = date.fromisoformat(created_at)
        for _ in range(orders_per_customer):
            order_sequence += 1
            order_id = _identifier("ORD", order_sequence)
            order_date = created + timedelta(days=rng.randint(0, 60))
            drawn_status = rng.choice(_ORDER_STATUS_CHOICES)
            status = force_status or drawn_status
            order_lines: list[OrderLine] = []
            for _line_index in range(lines_per_order):
                line_sequence += 1
                product = CATALOG[rng.randrange(len(CATALOG))]
                quantity = rng.randint(QUANTITY_MIN, QUANTITY_MAX)
                order_lines.append(
                    OrderLine(
                        line_id=_identifier("LIN", line_sequence),
                        order_id=order_id,
                        sku=product.sku,
                        product_name=product.name,
                        quantity=quantity,
                        unit_price=format_money(product.unit_price),
                        line_total=format_money(
                            line_total(product.unit_price, quantity)
                        ),
                    )
                )
            subtotal, tax, total = order_totals(
                [Decimal(row.line_total) for row in order_lines], tax_rate
            )
            order = Order(
                order_id=order_id,
                customer_id=customer.customer_id,
                order_date=order_date.isoformat(),
                status=status,
                currency=currency,
                subtotal=format_money(subtotal),
                tax=format_money(tax),
                total=format_money(total),
            )
            orders.append(order)
            lines.extend(order_lines)
            if status in PAID_ORDER_STATUSES:
                payment_sequence += 1
                hour = rng.randint(8, 18)
                minute = rng.randint(0, 59)
                second = rng.randint(0, 59)
                payments.append(
                    Payment(
                        payment_id=_identifier("PAY", payment_sequence),
                        order_id=order_id,
                        amount=format_money(total),
                        method=rng.choice(_PAYMENT_METHODS),
                        paid_at=(
                            f"{order_date.isoformat()}T"
                            f"{hour:02d}:{minute:02d}:{second:02d}Z"
                        ),
                        status="captured",
                    )
                )
            invoice_sequence += 1
            due = order_date + timedelta(days=30)
            invoices.append(
                Invoice(
                    invoice_id=_identifier("INV", invoice_sequence),
                    order_id=order_id,
                    invoice_number=(
                        f"INV-{order_date.strftime('%Y%m%d')}-{invoice_sequence:06d}"
                    ),
                    issued_at=order_date.isoformat(),
                    due_at=due.isoformat(),
                    amount=format_money(total),
                    status=INVOICE_STATUS_BY_ORDER[status],
                )
            )
    return orders, lines, payments, invoices
