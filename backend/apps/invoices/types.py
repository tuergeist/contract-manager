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
    # Item billing period
    item_start_date: Optional[date] = None
    item_billing_start_date: Optional[date] = None
    item_billing_end_date: Optional[date] = None
    # Item order confirmation (AB number)
    order_confirmation_number: Optional[str] = None


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

    # Enhanced fields for NetSuite-style export
    customer_number: str = ""  # e.g., "CUS174"
    sales_order_number: str = ""  # e.g., "SO-VSX-25-039"
    contract_number: str = ""  # e.g., "13634_2025-01-01_2025-12-31"
    po_number: str = ""  # Purchase Order number
    order_confirmation_number: str = ""  # AB Nummer (contract level)
    contract_start_date: Optional[date] = None
    contract_end_date: Optional[date] = None
    billing_interval: str = ""  # e.g., "monthly", "quarterly", "annual"

    @property
    def total_amount(self) -> Decimal:
        """Calculate total invoice amount from line items."""
        return sum(item.amount for item in self.line_items)

    @property
    def line_item_count(self) -> int:
        """Return number of line items."""
        return len(self.line_items)

    @property
    def customer_display_name(self) -> str:
        """Return customer name with number prefix if available."""
        if self.customer_number:
            return f"{self.customer_number} {self.customer_name}"
        return self.customer_name
