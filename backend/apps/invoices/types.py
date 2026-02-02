"""Invoice data classes for structured return values."""
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Optional


@dataclass
class InvoiceLineItem:
    """A line item in an invoice."""

    item_id: int
    product_name: str
    description: str
    quantity: int
    unit_price: Decimal
    amount: Decimal
    is_prorated: bool = False
    prorate_factor: Optional[Decimal] = None
    is_one_off: bool = False


@dataclass
class InvoiceData:
    """Invoice data for a single contract billing event."""

    contract_id: int
    contract_name: str
    customer_id: int
    customer_name: str
    customer_address: dict
    billing_date: date
    billing_period_start: date
    billing_period_end: date
    line_items: list[InvoiceLineItem] = field(default_factory=list)
    invoice_text: str = ""  # Optional text to show on invoice below line items

    @property
    def total_amount(self) -> Decimal:
        """Calculate total invoice amount from line items."""
        return sum(item.amount for item in self.line_items)

    @property
    def line_item_count(self) -> int:
        """Return number of line items."""
        return len(self.line_items)
