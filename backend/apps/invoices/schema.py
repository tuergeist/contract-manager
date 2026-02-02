"""GraphQL schema for invoices."""
from datetime import date
from decimal import Decimal
from typing import List

import strawberry
from strawberry.types import Info

from apps.core.permissions import get_current_user
from apps.invoices.services import InvoiceService
from apps.invoices.types import InvoiceData, InvoiceLineItem


@strawberry.type
class InvoiceLineItemType:
    """A line item in an invoice."""

    item_id: int
    product_name: str
    description: str
    quantity: int
    unit_price: Decimal
    amount: Decimal
    is_prorated: bool
    prorate_factor: Decimal | None
    is_one_off: bool


@strawberry.type
class InvoiceType:
    """Invoice data for preview."""

    contract_id: int
    contract_name: str
    customer_id: int
    customer_name: str
    customer_address: strawberry.scalars.JSON
    billing_date: date
    billing_period_start: date
    billing_period_end: date
    line_items: List[InvoiceLineItemType]
    total_amount: Decimal
    line_item_count: int
    invoice_text: str  # Optional text to show below line items


def _convert_line_item(item: InvoiceLineItem) -> InvoiceLineItemType:
    """Convert InvoiceLineItem dataclass to GraphQL type."""
    return InvoiceLineItemType(
        item_id=item.item_id,
        product_name=item.product_name,
        description=item.description,
        quantity=item.quantity,
        unit_price=item.unit_price,
        amount=item.amount,
        is_prorated=item.is_prorated,
        prorate_factor=item.prorate_factor,
        is_one_off=item.is_one_off,
    )


def _convert_invoice(invoice: InvoiceData) -> InvoiceType:
    """Convert InvoiceData dataclass to GraphQL type."""
    return InvoiceType(
        contract_id=invoice.contract_id,
        contract_name=invoice.contract_name,
        customer_id=invoice.customer_id,
        customer_name=invoice.customer_name,
        customer_address=invoice.customer_address,
        billing_date=invoice.billing_date,
        billing_period_start=invoice.billing_period_start,
        billing_period_end=invoice.billing_period_end,
        line_items=[_convert_line_item(item) for item in invoice.line_items],
        total_amount=invoice.total_amount,
        line_item_count=invoice.line_item_count,
        invoice_text=invoice.invoice_text,
    )


@strawberry.type
class InvoiceQuery:
    """Invoice-related queries."""

    @strawberry.field
    def invoices_for_month(
        self, info: Info, year: int, month: int
    ) -> List[InvoiceType]:
        """Get all invoices due for a specific month.

        Args:
            year: The year (e.g., 2026)
            month: The month (1-12)

        Returns:
            List of invoices with their line items.
        """
        user = get_current_user(info)
        service = InvoiceService(user.tenant)
        invoices = service.get_invoices_for_month(year, month)
        return [_convert_invoice(inv) for inv in invoices]
