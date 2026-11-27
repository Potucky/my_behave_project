"""Seeded factories for referentially consistent QA test data.

This is a portfolio demo. Every person, email, phone, and payment it
builds is fictional and is meant to be loaded as a test fixture.
"""

from qa_data_factory.config import FactoryConfig
from qa_data_factory.constraints import ConstraintError, validate_customer, validate_graph
from qa_data_factory.exporters import export_csv, export_json, export_sql
from qa_data_factory.factory import OrderGraphFactory
from qa_data_factory.invalid import VIOLATIONS, InvalidDataFactory
from qa_data_factory.models import (
    Customer,
    Invoice,
    Order,
    OrderGraph,
    OrderLine,
    Payment,
)

__all__ = [
    "VIOLATIONS",
    "ConstraintError",
    "Customer",
    "FactoryConfig",
    "InvalidDataFactory",
    "Invoice",
    "Order",
    "OrderGraph",
    "OrderGraphFactory",
    "OrderLine",
    "Payment",
    "export_csv",
    "export_json",
    "export_sql",
    "validate_customer",
    "validate_graph",
]
