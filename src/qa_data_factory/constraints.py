"""Explicit rules for a generated batch.

The factory calls :func:`validate_graph` before it returns, and the tests
call the same function. A rule that is only described in a docstring would
drift; a rule that lives here cannot pass the suite unless the data obeys it.
"""

import re
from datetime import date, datetime, timedelta
from decimal import Decimal

from qa_data_factory.catalog import PRODUCTS_BY_SKU
from qa_data_factory.models import Customer, Invoice, Order, OrderGraph, OrderLine, Payment
from qa_data_factory.money import format_money, line_total, order_totals

EMAIL_RE = re.compile(r"^[a-z0-9]+(?:[._+-][a-z0-9]+)*@example\.com$")
PHONE_RE = re.compile(r"^\+[1-9]\d{10,14}$")
ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ISO_DATETIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
CUSTOMER_ID_RE = re.compile(r"^CUS-\d{6}$")
ORDER_ID_RE = re.compile(r"^ORD-\d{6}$")
LINE_ID_RE = re.compile(r"^LIN-\d{6}$")
PAYMENT_ID_RE = re.compile(r"^PAY-\d{6}$")
INVOICE_ID_RE = re.compile(r"^INV-\d{6}$")
INVOICE_NUMBER_RE = re.compile(r"^INV-\d{8}-\d{6}$")
MONEY_RE = re.compile(r"^-?\d+\.\d{2}$")

CUSTOMER_STATUSES = frozenset({"active", "inactive"})
ORDER_STATUSES = frozenset({"pending", "paid", "shipped", "cancelled"})
PAID_ORDER_STATUSES = frozenset({"paid", "shipped"})
PAYMENT_METHODS = frozenset({"card", "paypal", "bank_transfer"})
INVOICE_STATUS_BY_ORDER = {
    "pending": "open",
    "paid": "paid",
    "shipped": "paid",
    "cancelled": "void",
}
CURRENCIES = frozenset({"USD", "EUR", "GBP"})

QUANTITY_MIN = 1
QUANTITY_MAX = 20
INVOICE_TERM_DAYS = 30


class ConstraintError(ValueError):
    """One field broke one published rule."""

    def __init__(self, field: str, message: str) -> None:
        self.field = field
        self.message = message
        super().__init__(f"{field}: {message}")


def _require_text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConstraintError(field, "is required")
    if any(ord(char) < 32 for char in value):
        raise ConstraintError(field, "must not contain control characters")
    return value


def parse_iso_date(value: object, field: str) -> date:
    text = _require_text(value, field)
    if not ISO_DATE_RE.fullmatch(text):
        raise ConstraintError(field, "must be an ISO date (YYYY-MM-DD)")
    try:
        return date.fromisoformat(text)
    except ValueError as exc:
        raise ConstraintError(field, "must be a real calendar date") from exc


def parse_iso_datetime(value: object, field: str) -> datetime:
    text = _require_text(value, field)
    if not ISO_DATETIME_RE.fullmatch(text):
        raise ConstraintError(field, "must be an ISO datetime (YYYY-MM-DDTHH:MM:SSZ)")
    try:
        return datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise ConstraintError(field, "must be a real calendar datetime") from exc


def parse_money(value: object, field: str) -> Decimal:
    text = _require_text(value, field)
    if not MONEY_RE.fullmatch(text):
        raise ConstraintError(field, "must be a decimal string with 2 places")
    return Decimal(text)


def validate_customer(customer: Customer) -> None:
    if not isinstance(customer.customer_id, str) or not CUSTOMER_ID_RE.fullmatch(
        customer.customer_id
    ):
        raise ConstraintError("customer_id", "must match CUS-000000")
    _require_text(customer.first_name, "first_name")
    _require_text(customer.last_name, "last_name")
    if customer.email is None or (
        isinstance(customer.email, str) and not customer.email.strip()
    ):
        raise ConstraintError("email", "is required")
    if not isinstance(customer.email, str) or not EMAIL_RE.fullmatch(customer.email):
        raise ConstraintError(
            "email", "must be a lowercase address at example.com"
        )
    if customer.phone is None or (
        isinstance(customer.phone, str) and not customer.phone.strip()
    ):
        raise ConstraintError("phone", "is required")
    if not isinstance(customer.phone, str) or not PHONE_RE.fullmatch(customer.phone):
        raise ConstraintError("phone", "must be E.164")
    parse_iso_date(customer.created_at, "created_at")
    _require_text(customer.city, "city")
    _require_text(customer.country, "country")
    if customer.status not in CUSTOMER_STATUSES:
        raise ConstraintError(
            "status", f"must be one of {', '.join(sorted(CUSTOMER_STATUSES))}"
        )


def _unique(values: list[str], field: str) -> dict[str, int]:
    seen: dict[str, int] = {}
    for index, value in enumerate(values):
        if value in seen:
            raise ConstraintError(field, f"duplicate {value}")
        seen[value] = index
    return seen


def _validate_order(order: Order) -> date:
    if not ORDER_ID_RE.fullmatch(order.order_id):
        raise ConstraintError("order_id", "must match ORD-000000")
    if not CUSTOMER_ID_RE.fullmatch(order.customer_id):
        raise ConstraintError("customer_id", "must match CUS-000000")
    order_date = parse_iso_date(order.order_date, "order_date")
    if order.status not in ORDER_STATUSES:
        raise ConstraintError(
            "status", f"must be one of {', '.join(sorted(ORDER_STATUSES))}"
        )
    if order.currency not in CURRENCIES:
        raise ConstraintError(
            "currency", f"must be one of {', '.join(sorted(CURRENCIES))}"
        )
    for field in ("subtotal", "tax", "total"):
        amount = parse_money(getattr(order, field), field)
        if amount < 0:
            raise ConstraintError(field, "must be >= 0")
    return order_date


def _validate_line(line: OrderLine) -> None:
    if not LINE_ID_RE.fullmatch(line.line_id):
        raise ConstraintError("line_id", "must match LIN-000000")
    if not ORDER_ID_RE.fullmatch(line.order_id):
        raise ConstraintError("order_id", "must match ORD-000000")
    product = PRODUCTS_BY_SKU.get(line.sku)
    if product is None:
        raise ConstraintError("sku", "must exist in the product catalog")
    if line.product_name != product.name:
        raise ConstraintError("product_name", "must match the catalog name for sku")
    unit_price = parse_money(line.unit_price, "unit_price")
    if unit_price != product.unit_price:
        raise ConstraintError("unit_price", "must match the catalog price for sku")
    if not isinstance(line.quantity, int) or isinstance(line.quantity, bool):
        raise ConstraintError("quantity", "must be an integer")
    if line.quantity < QUANTITY_MIN or line.quantity > QUANTITY_MAX:
        raise ConstraintError(
            "quantity", f"must be from {QUANTITY_MIN} to {QUANTITY_MAX}"
        )
    expected = format_money(line_total(product.unit_price, line.quantity))
    actual = parse_money(line.line_total, "line_total")
    if format_money(actual) != expected:
        raise ConstraintError("line_total", "must equal quantity times unit_price")


def _validate_payment(payment: Payment) -> datetime:
    if not PAYMENT_ID_RE.fullmatch(payment.payment_id):
        raise ConstraintError("payment_id", "must match PAY-000000")
    if not ORDER_ID_RE.fullmatch(payment.order_id):
        raise ConstraintError("order_id", "must match ORD-000000")
    amount = parse_money(payment.amount, "amount")
    if amount < 0:
        raise ConstraintError("amount", "must be >= 0")
    if payment.method not in PAYMENT_METHODS:
        raise ConstraintError(
            "method", f"must be one of {', '.join(sorted(PAYMENT_METHODS))}"
        )
    paid_at = parse_iso_datetime(payment.paid_at, "paid_at")
    if payment.status != "captured":
        raise ConstraintError("status", "must be captured")
    return paid_at


def _validate_invoice(invoice: Invoice) -> tuple[date, date]:
    if not INVOICE_ID_RE.fullmatch(invoice.invoice_id):
        raise ConstraintError("invoice_id", "must match INV-000000")
    if not ORDER_ID_RE.fullmatch(invoice.order_id):
        raise ConstraintError("order_id", "must match ORD-000000")
    if not INVOICE_NUMBER_RE.fullmatch(invoice.invoice_number):
        raise ConstraintError("invoice_number", "must match INV-YYYYMMDD-000000")
    issued = parse_iso_date(invoice.issued_at, "issued_at")
    due = parse_iso_date(invoice.due_at, "due_at")
    if due != issued + timedelta(days=INVOICE_TERM_DAYS):
        raise ConstraintError("due_at", "must be 30 days after issued_at")
    if not invoice.invoice_number.startswith(f"INV-{issued.strftime('%Y%m%d')}-"):
        raise ConstraintError("invoice_number", "must start with the issued date")
    amount = parse_money(invoice.amount, "amount")
    if amount < 0:
        raise ConstraintError("amount", "must be >= 0")
    if invoice.status not in {"open", "paid", "void"}:
        raise ConstraintError("status", "must be open, paid, or void")
    return issued, due


def validate_graph(graph: OrderGraph) -> None:
    """Raise ConstraintError if any published rule is broken."""
    try:
        tax_rate = Decimal(graph.tax_rate)
    except Exception as exc:
        raise ConstraintError("tax_rate", "must be a decimal string") from exc
    if tax_rate < 0 or tax_rate > 1:
        raise ConstraintError("tax_rate", "must be between 0 and 1")
    if graph.currency not in CURRENCIES:
        raise ConstraintError(
            "currency", f"must be one of {', '.join(sorted(CURRENCIES))}"
        )

    for customer in graph.customers:
        validate_customer(customer)
    _unique([row.customer_id for row in graph.customers], "customer_id")
    _unique([row.email or "" for row in graph.customers], "email")
    _unique([row.phone or "" for row in graph.customers], "phone")
    customers = {row.customer_id: row for row in graph.customers}

    orders: dict[str, Order] = {}
    order_dates: dict[str, date] = {}
    for order in graph.orders:
        order_date = _validate_order(order)
        if order.order_id in orders:
            raise ConstraintError("order_id", f"duplicate {order.order_id}")
        customer = customers.get(order.customer_id)
        if customer is None:
            raise ConstraintError("customer_id", "no matching customer")
        if customer.status != "active":
            raise ConstraintError("customer_id", "orders require an active customer")
        created = parse_iso_date(customer.created_at, "created_at")
        if order_date < created:
            raise ConstraintError(
                "order_date", "must be on or after the customer created_at"
            )
        if order.currency != graph.currency:
            raise ConstraintError("currency", "must match the batch currency")
        orders[order.order_id] = order
        order_dates[order.order_id] = order_date

    lines_by_order: dict[str, list[OrderLine]] = {order_id: [] for order_id in orders}
    for line in graph.lines:
        _validate_line(line)
        if line.order_id not in orders:
            raise ConstraintError("order_id", "no matching order")
        lines_by_order[line.order_id].append(line)
    _unique([row.line_id for row in graph.lines], "line_id")

    for order_id, order in orders.items():
        related = lines_by_order[order_id]
        if not related:
            raise ConstraintError("order_id", "must have at least one order line")
        subtotal, tax, total = order_totals(
            [Decimal(row.line_total) for row in related], tax_rate
        )
        if order.subtotal != format_money(subtotal):
            raise ConstraintError("subtotal", "must equal the sum of line totals")
        if order.tax != format_money(tax):
            raise ConstraintError("tax", "must equal subtotal times the tax rate")
        if order.total != format_money(total):
            raise ConstraintError("total", "must equal subtotal plus tax")

    payments_by_order: dict[str, list[Payment]] = {order_id: [] for order_id in orders}
    for payment in graph.payments:
        paid_at = _validate_payment(payment)
        if payment.order_id not in orders:
            raise ConstraintError("order_id", "no matching order")
        order = orders[payment.order_id]
        if order.status not in PAID_ORDER_STATUSES:
            raise ConstraintError("order_id", "payments belong only on paid or shipped orders")
        if paid_at.date() != order_dates[payment.order_id]:
            raise ConstraintError("paid_at", "must fall on the order date")
        if payment.amount != order.total:
            raise ConstraintError("amount", "must equal the order total")
        payments_by_order[payment.order_id].append(payment)
    _unique([row.payment_id for row in graph.payments], "payment_id")

    for order_id, order in orders.items():
        found = payments_by_order[order_id]
        if order.status in PAID_ORDER_STATUSES and len(found) != 1:
            raise ConstraintError("payment_id", "paid and shipped orders need one payment")
        if order.status not in PAID_ORDER_STATUSES and found:
            raise ConstraintError("payment_id", "pending and cancelled orders have no payment")

    invoices_by_order: dict[str, list[Invoice]] = {order_id: [] for order_id in orders}
    for invoice in graph.invoices:
        issued, _due = _validate_invoice(invoice)
        if invoice.order_id not in orders:
            raise ConstraintError("order_id", "no matching order")
        order = orders[invoice.order_id]
        if issued != order_dates[invoice.order_id]:
            raise ConstraintError("issued_at", "must equal the order date")
        if invoice.amount != order.total:
            raise ConstraintError("amount", "must equal the order total")
        expected_status = INVOICE_STATUS_BY_ORDER[order.status]
        if invoice.status != expected_status:
            raise ConstraintError(
                "status", f"must be {expected_status} when the order is {order.status}"
            )
        invoices_by_order[invoice.order_id].append(invoice)
    _unique([row.invoice_id for row in graph.invoices], "invoice_id")
    _unique([row.invoice_number for row in graph.invoices], "invoice_number")

    for order_id, found in invoices_by_order.items():
        if len(found) != 1:
            raise ConstraintError("invoice_id", "each order needs exactly one invoice")
