"""Fixed product catalog. Order lines copy a row from here; they do not invent prices."""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Product:
    sku: str
    name: str
    unit_price: Decimal


# Prices are Decimal strings in spirit: constructed from exact decimal literals.
CATALOG: tuple[Product, ...] = (
    Product("SKU-MUG-001", "Ceramic Mug", Decimal("12.50")),
    Product("SKU-MUG-002", "Travel Mug", Decimal("18.00")),
    Product("SKU-TEE-001", "Cotton Tee", Decimal("19.99")),
    Product("SKU-TEE-002", "Heavyweight Tee", Decimal("24.00")),
    Product("SKU-CAP-001", "Canvas Cap", Decimal("15.00")),
    Product("SKU-BAG-001", "Tote Bag", Decimal("22.50")),
    Product("SKU-NBK-001", "Notebook", Decimal("10.01")),
    Product("SKU-PEN-001", "Gel Pen Set", Decimal("8.75")),
    Product("SKU-BTL-001", "Water Bottle", Decimal("16.40")),
    Product("SKU-STK-001", "Sticker Pack", Decimal("4.50")),
)

PRODUCTS_BY_SKU: dict[str, Product] = {product.sku: product for product in CATALOG}
