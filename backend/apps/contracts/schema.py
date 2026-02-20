"""GraphQL schema for contracts."""

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Annotated, List
import base64
import tempfile
import os

import strawberry
from strawberry import auto, UNSET
import strawberry_django
from strawberry.types import Info
from django.db import transaction
from django.db.models import Sum, F, Q

from apps.core.context import Context
from apps.core.permissions import check_perm, get_current_user, require_perm
from apps.core.schema import DeleteResult
from apps.customers.models import Customer
from apps.customers.schema import CustomerType
from apps.products.models import Product
from apps.products.schema import ProductType
from .models import Contract, ContractComment, ContractItem, ContractAmendment, ContractItemPrice, ContractAttachment, ContractLink, ContractGroup, TimeTrackingProjectMapping
from .services import ExcelParser, ImportService, MatchStatus

if TYPE_CHECKING:
    from apps.todos.schema import TodoItemType


# =============================================================================
# Utility Functions for Contract Value Calculation
# =============================================================================


def _months_between(start: date, end: date) -> int:
    """Calculate months between two dates (inclusive of partial months)."""
    if end <= start:
        return 0
    months = (end.year - start.year) * 12 + (end.month - start.month)
    # Add 1 if end date is not the first of the month
    if end.day > 1:
        months += 1
    return max(months, 0)


def _calculate_item_value_over_duration(
    item: "ContractItem", start: date, end: date
) -> Decimal:
    """Calculate total value for a recurring item over the contract duration.

    Considers period-specific pricing by iterating through price periods.

    The algorithm works by iterating month by month through the contract
    and applying the correct price for each month.
    """
    from dateutil.relativedelta import relativedelta

    # Get all price periods for this item, sorted by valid_from
    price_periods = list(item.price_periods.order_by("valid_from"))

    if not price_periods:
        # No specific periods: use base price for entire duration
        monthly_price = item.monthly_unit_price
        months = _months_between(start, end)
        return monthly_price * item.quantity * Decimal(months)

    total_value = Decimal("0")

    # Iterate month by month through the contract duration
    current_month_start = date(start.year, start.month, 1)
    end_month_start = date(end.year, end.month, 1)
    # If end date is the 1st of a month, the last active month is the previous one
    # (matches _months_between logic which doesn't add +1 when end.day == 1)
    if end.day == 1:
        end_month_start = end_month_start - relativedelta(months=1)

    while current_month_start <= end_month_start:
        # Find the price period that applies to this month
        applicable_period = None
        for pp in price_periods:
            pp_end = pp.valid_to if pp.valid_to else end
            if pp.valid_from <= current_month_start and current_month_start <= pp_end:
                applicable_period = pp
                break

        if applicable_period:
            # Use period-specific price
            period_months = item.get_period_months(applicable_period.price_period)
            monthly_price = applicable_period.unit_price / Decimal(period_months)
        else:
            # Use base price
            monthly_price = item.monthly_unit_price

        total_value += monthly_price * item.quantity

        # Move to next month
        current_month_start = current_month_start + relativedelta(months=1)

    return total_value


def calculate_contract_total_value(contract: "Contract") -> Decimal:
    """Calculate total contract value based on duration + one-off items.

    For recurring items with period-specific pricing, calculates value
    for each price period separately and sums them up.

    This is a standalone function that can be called from tests or other code.
    """
    from dateutil.relativedelta import relativedelta

    today = date.today()
    contract_start = contract.start_date
    contract_end = contract.get_effective_end_date()

    if not contract_end:
        # Fallback if no end date determinable
        contract_end = contract_start + relativedelta(months=12)

    # Get items with prefetched price_periods
    items = ContractItem.objects.filter(contract=contract).prefetch_related("price_periods")

    recurring_total = Decimal("0")
    one_off_total = Decimal("0")

    for item in items:
        if item.is_one_off:
            # One-off items use effective price × quantity
            effective_price, period = item.get_effective_price_info(today)
            one_off_total += effective_price * item.quantity
        else:
            # Recurring items: calculate value across all price periods
            item_value = _calculate_item_value_over_duration(
                item, contract_start, contract_end
            )
            recurring_total += item_value

    return recurring_total + one_off_total


@strawberry.type
class ContractAmendmentType:
    """A contract amendment/change record."""

    id: int
    effective_date: date
    type: str
    description: str
    changes: strawberry.scalars.JSON
    created_at: datetime


@strawberry.type
class ContractAttachmentType:
    """A file attachment for a contract."""

    id: int
    original_filename: str
    file_size: int
    content_type: str
    description: str
    uploaded_at: datetime
    uploaded_by_name: str | None
    download_url: str


@strawberry.type
class ContractLinkType:
    """A named link attached to a contract."""

    id: int
    name: str
    url: str
    created_at: datetime
    created_by_name: str | None


@strawberry.type
class ContractGroupType:
    """A group for organizing contracts within a customer."""

    id: int
    name: str
    contract_count: int


@strawberry.type
class ContractItemPriceType:
    """A price period for a contract item."""

    id: int
    valid_from: date
    valid_to: date | None
    unit_price: Decimal
    price_period: str
    source: str


@strawberry.type
class ContractItemType:
    """A line item in a contract."""

    id: int
    quantity: int
    unit_price: Decimal
    price_period: str  # Period the price refers to (monthly, quarterly, annual, etc.)
    price_source: str
    total_price: Decimal
    # Effective price for current date (uses period-specific pricing if available)
    effective_price: Decimal
    effective_price_period: str
    product: ProductType | None = None  # Optional for descriptive items
    description: str = ""  # Additional description or text-only items
    # When item becomes effective
    start_date: date | None = None
    # Billing fields
    billing_start_date: date | None = None
    billing_end_date: date | None = None
    align_to_contract_at: date | None = None
    suggested_alignment_date: date | None = None
    is_one_off: bool = False
    # Order confirmation
    order_confirmation_number: str | None = None
    # Price lock fields
    price_locked: bool = False
    price_locked_until: date | None = None
    sort_order: int | None = None
    # Delivery tracking
    delivery_status: str | None = None
    delivered_at: date | None = None
    estimated_delivery_date: date | None = None
    depends_on: "ContractItemType | None" = None
    dependent_items: List["ContractItemType"] = strawberry.field(default_factory=list)
    # Year-specific pricing
    price_periods: List[ContractItemPriceType] = strawberry.field(default_factory=list)


@strawberry_django.type(Contract)
class ContractType:
    """A contract with a customer."""

    id: auto
    name: auto
    hubspot_deal_id: auto
    start_date: auto
    end_date: auto
    billing_start_date: auto
    billing_interval: auto
    billing_anchor_day: auto
    billing_alignment_date: auto
    min_duration_months: auto
    notice_period_months: auto
    notice_period_anchor: auto
    notice_period_after_min_months: auto
    cancelled_at: auto
    cancellation_effective_date: auto
    created_at: auto
    updated_at: auto
    netsuite_sales_order_number: auto
    netsuite_contract_number: auto
    netsuite_url: auto
    po_number: auto
    order_confirmation_number: auto
    notes: auto
    invoice_text: auto
    customer: CustomerType

    @strawberry.field
    def has_invoices(self) -> bool:
        """Check if contract has any generated or imported invoices."""
        return self.invoice_records.exists() or self.imported_invoices.exists()

    @strawberry.field
    def group(self) -> ContractGroupType | None:
        """Get the contract's group."""
        if not self.group_id:
            return None
        group = ContractGroup.objects.filter(id=self.group_id).first()
        if not group:
            return None
        return ContractGroupType(
            id=group.id,
            name=group.name,
            contract_count=Contract.objects.filter(group=group).count(),
        )

    @strawberry.field
    def status(self) -> str:
        """Get the effective status, accounting for end date in the past."""
        return self.effective_status

    @strawberry.field
    def hubspot_url(self, info: Info[Context, None]) -> str | None:
        """Get the HubSpot deal URL if this contract was synced from HubSpot."""
        if not self.hubspot_deal_id:
            return None
        user = get_current_user(info)
        if not user.tenant:
            return None
        config = user.tenant.hubspot_config or {}
        portal_id = config.get("portal_id")
        if not portal_id:
            return None
        return f"https://app-eu1.hubspot.com/contacts/{portal_id}/deal/{self.hubspot_deal_id}"

    @strawberry.field
    def items(self) -> List[ContractItemType]:
        """Get all contract items."""
        items = ContractItem.objects.filter(contract=self).select_related("product", "contract", "depends_on", "depends_on__product").prefetch_related("price_periods", "dependent_items", "dependent_items__product")
        result = []
        today = date.today()
        for item in items:
            # Get price periods for this item
            price_periods = [
                ContractItemPriceType(
                    id=pp.id,
                    valid_from=pp.valid_from,
                    valid_to=pp.valid_to,
                    unit_price=pp.unit_price,
                    price_period=pp.price_period,
                    source=pp.source,
                )
                for pp in item.price_periods.all()
            ]
            # Get effective price for today (uses period-specific pricing if available)
            effective_price, effective_price_period = item.get_effective_price_info(today)
            result.append(
                ContractItemType(
                    id=item.id,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    price_period=item.price_period,
                    price_source=item.price_source,
                    total_price=item.total_price,
                    effective_price=effective_price,
                    effective_price_period=effective_price_period,
                    product=item.product,
                    description=item.description,
                    start_date=item.start_date,
                    billing_start_date=item.billing_start_date,
                    billing_end_date=item.billing_end_date,
                    align_to_contract_at=item.align_to_contract_at,
                    suggested_alignment_date=item.get_suggested_alignment_date() if item.product else None,
                    is_one_off=item.is_one_off,
                    order_confirmation_number=item.order_confirmation_number,
                    price_locked=item.price_locked,
                    price_locked_until=item.price_locked_until,
                    sort_order=item.sort_order,
                    delivery_status=item.delivery_status,
                    delivered_at=item.delivered_at,
                    estimated_delivery_date=item.estimated_delivery_date,
                    depends_on=ContractItemType(
                        id=item.depends_on.id,
                        quantity=item.depends_on.quantity,
                        unit_price=item.depends_on.unit_price,
                        price_period=item.depends_on.price_period,
                        price_source=item.depends_on.price_source,
                        total_price=item.depends_on.total_price,
                        effective_price=item.depends_on.unit_price,
                        effective_price_period=item.depends_on.price_period,
                        product=item.depends_on.product,
                        description=item.depends_on.description,
                        is_one_off=item.depends_on.is_one_off,
                        delivery_status=item.depends_on.delivery_status,
                        delivered_at=item.depends_on.delivered_at,
                        estimated_delivery_date=item.depends_on.estimated_delivery_date,
                    ) if item.depends_on else None,
                    dependent_items=[
                        ContractItemType(
                            id=dep.id,
                            quantity=dep.quantity,
                            unit_price=dep.unit_price,
                            price_period=dep.price_period,
                            price_source=dep.price_source,
                            total_price=dep.total_price,
                            effective_price=dep.unit_price,
                            effective_price_period=dep.price_period,
                            product=dep.product,
                            description=dep.description,
                            is_one_off=dep.is_one_off,
                            delivery_status=dep.delivery_status,
                            delivered_at=dep.delivered_at,
                            estimated_delivery_date=dep.estimated_delivery_date,
                        )
                        for dep in item.dependent_items.all()
                    ],
                    price_periods=price_periods,
                )
            )
        return result

    @strawberry.field
    def amendments(self) -> List[ContractAmendmentType]:
        """Get all amendments for this contract."""
        amendments = ContractAmendment.objects.filter(contract=self)
        return [
            ContractAmendmentType(
                id=a.id,
                effective_date=a.effective_date,
                type=a.type,
                description=a.description,
                changes=a.changes,
                created_at=a.created_at,
            )
            for a in amendments
        ]

    @strawberry.field
    def attachments(self) -> List[ContractAttachmentType]:
        """Get all file attachments for this contract."""
        attachments = ContractAttachment.objects.filter(contract=self).select_related("uploaded_by")
        return [
            ContractAttachmentType(
                id=a.id,
                original_filename=a.original_filename,
                file_size=a.file_size,
                content_type=a.content_type,
                description=a.description,
                uploaded_at=a.created_at,
                uploaded_by_name=a.uploaded_by.email if a.uploaded_by else None,
                download_url=f"/api/attachments/{a.id}/download/",
            )
            for a in attachments
        ]

    @strawberry.field
    def links(self) -> List[ContractLinkType]:
        """Get all links for this contract."""
        links = ContractLink.objects.filter(contract=self).select_related("created_by")
        return [
            ContractLinkType(
                id=link.id,
                name=link.name,
                url=link.url,
                created_at=link.created_at,
                created_by_name=link.created_by.email if link.created_by else None,
            )
            for link in links
        ]

    @strawberry.field
    def todos(self, info: Info[Context, None]) -> List[Annotated["TodoItemType", strawberry.lazy("apps.todos.schema")]]:
        """Get todos for this contract visible to the current user."""
        from apps.todos.models import TodoItem
        from apps.todos.schema import todo_to_type

        user = get_current_user(info)
        if not user:
            return []

        # Get todos: user's own todos OR public todos from team
        todos = TodoItem.objects.filter(
            contract=self,
        ).filter(
            Q(created_by=user) | Q(is_public=True)
        ).select_related("created_by").order_by("-created_at")

        return [todo_to_type(todo) for todo in todos]

    @strawberry.field
    def time_tracking_mappings_count(self) -> int:
        """Get the number of time tracking project mappings for this contract."""
        return TimeTrackingProjectMapping.objects.filter(contract=self).count()

    @strawberry.field
    def effective_end_date(self) -> date | None:
        """Get the effective end date for total value calculation."""
        return self.get_effective_end_date()

    @strawberry.field
    def duration_months(self) -> int:
        """Get the contract duration in months."""
        return self.get_duration_months()

    @strawberry.field
    def remaining_months(self) -> int:
        """Get the remaining months until contract end."""
        from dateutil.relativedelta import relativedelta

        effective_end = self.get_effective_end_date()
        if not effective_end:
            return 0

        today = date.today()
        if today >= effective_end:
            return 0

        # Calculate months between today and end date
        delta = relativedelta(effective_end, today)
        return delta.years * 12 + delta.months + (1 if delta.days > 0 else 0)

    @strawberry.field
    def total_value(self) -> Decimal:
        """Calculate total contract value based on duration + one-off items.

        For recurring items with period-specific pricing, calculates value
        for each price period separately and sums them up.
        """
        return calculate_contract_total_value(self)

    @strawberry.field
    def monthly_recurring_value(self) -> Decimal:
        """Calculate monthly recurring value (excludes one-off items)."""
        from datetime import date
        today = date.today()

        items = ContractItem.objects.filter(contract=self, is_one_off=False)

        monthly_total = Decimal("0")
        for item in items:
            # Use effective price considering period-specific pricing
            monthly_unit_price = item.get_price_at(today, normalize_to_monthly=True)
            monthly_total += monthly_unit_price * item.quantity

        return monthly_total

    @strawberry.field
    def arr(self) -> Decimal:
        """Calculate Annual Recurring Revenue (monthly × 12), zero if expired."""
        from datetime import date
        today = date.today()

        # Skip expired contracts
        contract_end = self.end_date or self.get_effective_end_date()
        if contract_end and contract_end < today:
            return Decimal("0")

        items = ContractItem.objects.filter(contract=self, is_one_off=False)
        monthly_total = Decimal("0")
        for item in items:
            monthly_unit_price = item.get_price_at(today, normalize_to_monthly=True)
            monthly_total += monthly_unit_price * item.quantity
        return monthly_total * 12


@strawberry.type
class ContractConnection:
    """Paginated contract list."""

    items: List[ContractType]
    total_count: int
    page: int
    page_size: int
    has_next_page: bool
    has_previous_page: bool


# Input types for mutations
@strawberry.input
class CreateContractInput:
    customer_id: strawberry.ID
    name: str | None = None
    sales_order_number: str | None = None
    netsuite_url: str | None = None
    po_number: str | None = None
    order_confirmation_number: str | None = None
    notes: str | None = None
    start_date: date
    end_date: date | None = None
    billing_start_date: date | None = None
    billing_interval: str = "monthly"
    billing_anchor_day: int = 1
    billing_alignment_date: date | None = None
    min_duration_months: int | None = None
    notice_period_months: int = 3
    notice_period_anchor: str = "end_of_duration"
    notice_period_after_min_months: int | None = None
    group_id: strawberry.ID | None = None


@strawberry.input
class UpdateContractInput:
    id: strawberry.ID
    name: str | None = None
    sales_order_number: str | None = None
    netsuite_url: str | None = None
    po_number: str | None = None
    order_confirmation_number: str | None = None
    notes: str | None = None
    invoice_text: str | None = None
    start_date: date | None = None
    end_date: date | None = UNSET
    billing_start_date: date | None = None
    billing_interval: str | None = None
    billing_anchor_day: int | None = None
    billing_alignment_date: date | None = UNSET
    min_duration_months: int | None = None
    notice_period_months: int | None = None
    notice_period_anchor: str | None = None
    notice_period_after_min_months: int | None = None
    group_id: strawberry.ID | None = UNSET


@strawberry.input
class ContractItemInput:
    product_id: strawberry.ID | None = None  # Optional for descriptive items
    description: str = ""  # Additional description or text-only items
    quantity: int = 1
    unit_price: Decimal = Decimal("0")
    price_period: str = "monthly"  # Period the price refers to (monthly, quarterly, annual, etc.)
    price_source: str = "list"
    start_date: date | None = None
    billing_start_date: date | None = None
    align_to_contract_at: date | None = None
    is_one_off: bool = False
    order_confirmation_number: str | None = None
    delivery_tracking: bool = False
    depends_on_item_id: strawberry.ID | None = None
    estimated_delivery_date: date | None = None


@strawberry.input
class UpdateContractItemInput:
    id: strawberry.ID
    product_id: strawberry.ID | None = None
    description: str | None = None
    quantity: int | None = None
    unit_price: Decimal | None = None
    price_period: str | None = None  # Period the price refers to (monthly, quarterly, annual, etc.)
    price_source: str | None = None
    start_date: date | None = UNSET
    billing_start_date: date | None = UNSET
    billing_end_date: date | None = UNSET
    align_to_contract_at: date | None = UNSET
    is_one_off: bool | None = None
    order_confirmation_number: str | None = None
    price_locked: bool | None = None
    price_locked_until: date | None = UNSET
    delivery_tracking: bool | None = None
    depends_on_item_id: strawberry.ID | None = UNSET
    estimated_delivery_date: date | None = UNSET


@strawberry.input
class ContractItemPriceInput:
    """Input for creating/updating a price period."""
    valid_from: date
    valid_to: date | None = None
    unit_price: Decimal
    price_period: str = "monthly"  # Period the price refers to (monthly, quarterly, annual, etc.)
    source: str = "fixed"


@strawberry.input
class UpdateContractItemPriceInput:
    """Input for updating a price period."""
    id: strawberry.ID
    valid_from: date | None = None
    valid_to: date | None = None
    unit_price: Decimal | None = None
    price_period: str | None = None  # Period the price refers to (monthly, quarterly, annual, etc.)
    source: str | None = None


# Result types for mutations
@strawberry.type
class ContractResult:
    contract: ContractType | None = None
    success: bool = False
    error: str | None = None


@strawberry.type
class ContractItemResult:
    item: ContractItemType | None = None
    success: bool = False
    error: str | None = None


@strawberry.type
class ContractItemPriceResult:
    price_period: ContractItemPriceType | None = None
    success: bool = False
    error: str | None = None


@strawberry.type
class ContractGroupResult:
    group: ContractGroupType | None = None
    success: bool = False
    error: str | None = None


@strawberry.input
class BulkPriceIncreaseInput:
    """Input for bulk price increase across all recurring items."""
    contract_id: strawberry.ID
    percentage: Decimal
    effective_date: date
    mode: str = "period_specific"  # "direct" or "period_specific"


@strawberry.type
class BulkPriceIncreaseItemResult:
    """Result for a single item in a bulk price increase."""
    item_id: int
    item_description: str
    old_price: Decimal
    new_price: Decimal
    skipped: bool = False
    skip_reason: str | None = None


@strawberry.type
class BulkPriceIncreaseResult:
    """Result of a bulk price increase operation."""
    success: bool = False
    error: str | None = None
    items_changed: int = 0
    items_skipped: int = 0
    details: List[BulkPriceIncreaseItemResult] = strawberry.field(default_factory=list)


@strawberry.type
class DependentItemInfo:
    """Info about a dependent item that may need billing_start_date."""
    id: int
    name: str
    has_billing_start_date: bool


@strawberry.type
class DeliverItemResult:
    """Result of marking an item as delivered."""
    success: bool = False
    error: str | None = None
    dependent_items: List[DependentItemInfo] = strawberry.field(default_factory=list)


@strawberry.type
class DeliverableItemType:
    """An item with delivery tracking, for the projects overview."""
    id: int
    product_name: str | None
    description: str
    is_one_off: bool
    delivery_status: str | None
    delivered_at: date | None
    estimated_delivery_date: date | None
    contract_id: int
    contract_name: str
    customer_name: str
    customer_id: int
    dependent_items_count: int


# =============================================================================
# Contract Attachment Types
# =============================================================================


@strawberry.input
class UploadAttachmentInput:
    """Input for uploading a file attachment."""

    contract_id: strawberry.ID
    file_content: str  # Base64-encoded file content
    filename: str
    content_type: str
    description: str = ""


@strawberry.type
class AttachmentResult:
    """Result of attachment operations."""

    attachment: ContractAttachmentType | None = None
    success: bool = False
    error: str | None = None


@strawberry.input
class AddContractLinkInput:
    """Input for adding a link to a contract."""

    contract_id: strawberry.ID
    name: str
    url: str


@strawberry.type
class ContractLinkResult:
    """Result of link operations."""

    link: ContractLinkType | None = None
    success: bool = False
    error: str | None = None


@strawberry.type
class SuggestedAlignmentDateResult:
    """Result for suggested alignment date calculation."""

    suggested_date: date | None = None
    error: str | None = None


@strawberry.type
class BillingScheduleItem:
    """An item in a billing event."""

    item_id: int
    product_name: str
    quantity: int
    unit_price: Decimal
    amount: Decimal
    is_prorated: bool = False
    prorate_factor: Decimal | None = None
    is_one_off: bool = False


@strawberry.type
class MatchedInvoiceType:
    """Invoice matched to a billing event."""

    id: strawberry.ID
    invoice_number: str
    is_paid: bool
    pdf_url: str | None


def find_matching_invoice_for_billing_event(
    contract_id: int,
    billing_date: date,
    invoices: list,
    expected_net: Decimal | None = None,
    tax_rate: Decimal | None = None,
) -> "MatchedInvoiceType | None":
    """
    Find a matching imported invoice for a billing event.

    Matching criteria:
    1. Invoice is linked to the same contract
    2. Invoice date is within 31 days *before* the billing event date
       (an invoice can't be dated after the billing event it covers)
    3. If expected_net is provided, the invoice total_amount must match
       either the net amount or the gross amount (net + tax)

    If multiple invoices match, returns the one with the closest date.

    Args:
        contract_id: The contract ID to match against
        billing_date: The billing event date
        invoices: List of ImportedInvoice objects (pre-filtered by contract)
        expected_net: Expected net amount from the billing schedule
        tax_rate: Default tax rate (%) for gross amount matching

    Returns:
        MatchedInvoiceType if a match is found, None otherwise
    """
    MATCH_WINDOW_DAYS = 31

    # Pre-compute expected gross if we have net + tax rate
    expected_gross = None
    if expected_net is not None and tax_rate is not None:
        tax_amount = (expected_net * tax_rate / Decimal("100")).quantize(Decimal("0.01"))
        expected_gross = expected_net + tax_amount

    # Filter invoices: must be on or before billing date, within window
    matching_invoices = []
    for inv in invoices:
        if inv.invoice_date is None:
            continue
        # Only look back: invoice_date <= billing_date
        days_diff = (billing_date - inv.invoice_date).days
        if days_diff < 0 or days_diff > MATCH_WINDOW_DAYS:
            continue
        # Amount check: invoice total must match net or gross
        if expected_net is not None and inv.total_amount is not None:
            matches_net = inv.total_amount == expected_net
            matches_gross = expected_gross is not None and inv.total_amount == expected_gross
            if not matches_net and not matches_gross:
                continue
        matching_invoices.append((inv, days_diff))

    if not matching_invoices:
        return None

    # Sort by date proximity (closest first)
    matching_invoices.sort(key=lambda x: x[1])
    best_match = matching_invoices[0][0]

    # Build PDF URL if file exists
    pdf_url = None
    if best_match.pdf_file:
        pdf_url = best_match.pdf_file.url

    return MatchedInvoiceType(
        id=strawberry.ID(str(best_match.id)),
        invoice_number=best_match.invoice_number or "",
        is_paid=best_match.is_paid,
        pdf_url=pdf_url,
    )


@strawberry.type
class BillingEvent:
    """A billing event on a specific date."""

    date: date
    items: List[BillingScheduleItem]
    total: Decimal
    matched_invoice: MatchedInvoiceType | None = None


@strawberry.type
class BillingScheduleResult:
    """Result for billing schedule calculation."""

    events: List[BillingEvent]
    total_forecast: Decimal
    period_start: date
    period_end: date
    error: str | None = None


@strawberry.type
class RevenueMonthData:
    """Revenue for a specific month."""

    month: str  # Format: "2026-01"
    amount: Decimal


@strawberry.type
class ContractRevenueRow:
    """Revenue data for a single contract across months."""

    contract_id: int
    contract_name: str
    customer_id: int
    customer_name: str
    months: List[RevenueMonthData]
    total: Decimal


@strawberry.type
class RevenueForecastResult:
    """Result for global revenue forecast."""

    month_columns: List[str]  # Column headers: ["2026-01", "2026-02", ...]
    monthly_totals: List[RevenueMonthData]  # Total for each month
    contracts: List[ContractRevenueRow]
    grand_total: Decimal
    error: str | None = None


# =============================================================================
# Dashboard KPIs
# =============================================================================


def calculate_dashboard_kpis(tenant) -> dict:
    """
    Calculate all dashboard KPIs for a tenant.

    Returns dict with:
    - total_active_contracts: Count of active contracts
    - total_contract_value: TCV for all active contracts
    - annual_recurring_revenue: ARR from recurring items
    - year_to_date_revenue: Revenue recognized from Jan 1 to today
    - current_year_forecast: Projected revenue for current year
    - next_year_forecast: Projected revenue for next year
    """
    from dateutil.relativedelta import relativedelta

    today = date.today()
    current_year_start = date(today.year, 1, 1)
    current_year_end = date(today.year, 12, 31)
    next_year_start = date(today.year + 1, 1, 1)
    next_year_end = date(today.year + 1, 12, 31)

    # Get all active contracts with items, products, and price_periods prefetched
    active_contracts = Contract.objects.filter(
        tenant=tenant,
        status=Contract.Status.ACTIVE,
    ).prefetch_related("items", "items__product", "items__price_periods", "items__depends_on")

    total_active_contracts = active_contracts.count()
    total_contract_value = Decimal("0")
    annual_recurring_revenue = Decimal("0")
    year_to_date_revenue = Decimal("0")
    current_year_forecast = Decimal("0")
    current_year_one_off = Decimal("0")
    current_year_discounts = Decimal("0")
    next_year_forecast = Decimal("0")
    next_year_one_off = Decimal("0")
    next_year_discounts = Decimal("0")

    for contract in active_contracts:
        # Use prefetched items (avoids re-querying)
        items = list(contract.items.all())
        monthly_value = Decimal("0")
        for item in items:
            if not item.is_one_off:
                # Use cached price lookup to avoid N+1 queries
                item_price_periods = list(item.price_periods.all())
                monthly_unit_price = item.get_price_at_cached(
                    today, item_price_periods, normalize_to_monthly=True
                )
                monthly_value += monthly_unit_price * item.quantity

        duration_months = contract.get_duration_months()
        total_contract_value += monthly_value * duration_months

        # Add one-off items to TCV
        for item in items:
            if item.is_one_off:
                effective_price, _ = item.get_effective_price_info(today)
                total_contract_value += effective_price * item.quantity

        # ARR: annualized run rate (monthly × 12), only for non-expired contracts
        contract_end = contract.end_date or contract.get_effective_end_date()
        if not contract_end or contract_end >= today:
            annual_recurring_revenue += monthly_value * 12

        # Recognition schedule spanning current year start to next year end,
        # split events into YTD, current year, and next year buckets
        include_next_year = not contract_end or contract_end >= next_year_start
        schedule_end = next_year_end if include_next_year else current_year_end

        # Track one-off item IDs for splitting one-off vs recurring
        one_off_item_ids = {item.id for item in items if item.is_one_off}

        full_schedule = contract.get_recognition_schedule(
            from_date=current_year_start,
            to_date=schedule_end,
            include_history=True,
            items=items,
            include_eta_items=True,
        )

        for event in full_schedule:
            event_date = event["date"]
            event_total = event["total"]

            # YTD: events from current year start up to today
            if event_date <= today:
                year_to_date_revenue += event_total

            # Current year: events within current year
            if event_date <= current_year_end:
                current_year_forecast += event_total

            # Next year: events in next year (only if contract spans into next year)
            if include_next_year and event_date >= next_year_start:
                next_year_forecast += event_total

            # Split per-item amounts into one-off and discounts
            for ei in event["items"]:
                amount = ei["amount"]
                is_one_off = ei["item_id"] in one_off_item_ids
                if event_date <= current_year_end:
                    if amount >= 0 and is_one_off:
                        current_year_one_off += amount
                    elif amount < 0:
                        current_year_discounts += amount
                if include_next_year and event_date >= next_year_start:
                    if amount >= 0 and is_one_off:
                        next_year_one_off += amount
                    elif amount < 0:
                        next_year_discounts += amount

    return {
        "total_active_contracts": total_active_contracts,
        "total_contract_value": total_contract_value,
        "annual_recurring_revenue": annual_recurring_revenue,
        "year_to_date_revenue": year_to_date_revenue,
        "current_year_forecast": current_year_forecast,
        "current_year_one_off": current_year_one_off,
        "current_year_discounts": current_year_discounts,
        "next_year_forecast": next_year_forecast,
        "next_year_one_off": next_year_one_off,
        "next_year_discounts": next_year_discounts,
    }


@strawberry.type
class DashboardKPIsType:
    """Dashboard KPI metrics for contract portfolio."""

    total_active_contracts: int
    total_contract_value: Decimal
    annual_recurring_revenue: Decimal
    year_to_date_revenue: Decimal
    current_year_forecast: Decimal
    current_year_one_off: Decimal
    current_year_discounts: Decimal
    next_year_forecast: Decimal
    next_year_one_off: Decimal
    next_year_discounts: Decimal


@strawberry.type
class TimeTrackingExternalProject:
    """A project from the external time tracking system."""
    id: str
    name: str
    customer_name: str
    active: bool


@strawberry.type
class TimeTrackingMappingType:
    """A mapping between an external project and a contract."""
    id: int
    external_project_id: str
    external_project_name: str
    external_customer_name: str
    contract_item_id: int | None
    contract_item_name: str | None = None
    cached_total_hours: float = 0


@strawberry.type
class ServiceBreakdown:
    """Time breakdown by service."""
    service_name: str
    hours: float
    revenue: float


@strawberry.type
class MonthlyBreakdown:
    """Time breakdown by month."""
    month: str
    hours: float
    revenue: float


@strawberry.type
class TimeTrackingSummaryType:
    """Aggregated time tracking data for a contract."""
    total_hours: float
    total_revenue: float
    by_service: list[ServiceBreakdown]
    by_month: list[MonthlyBreakdown]
    mappings: list[TimeTrackingMappingType]
    last_synced: datetime | None = None


@strawberry.type
class TimeTrackingMappingResult:
    """Result of a mapping mutation."""
    success: bool
    error: str | None = None
    mapping: TimeTrackingMappingType | None = None


# --- PDF Analysis Types ---


@strawberry.type
class PdfProductMatchType:
    """A product match result from fuzzy matching."""

    product_id: int
    product_name: str
    confidence: float


@strawberry.type
class PdfExtractedItemType:
    """A line item extracted from a PDF."""

    description: str
    quantity: int
    unit_price: Decimal
    price_period: str
    is_one_off: bool


@strawberry.type
class PdfComparisonItemType:
    """An extracted item compared against existing contract items."""

    extracted: PdfExtractedItemType
    product_match: PdfProductMatchType | None
    status: str  # "new" or "existing"
    existing_item_id: int | None
    price_differs: bool


@strawberry.type
class PdfMetadataComparisonType:
    """Comparison of a single metadata field."""

    field_name: str
    extracted_value: str | None
    current_value: str | None
    differs: bool


@strawberry.type
class PdfExtractedMetadataType:
    """Contract metadata extracted from a PDF."""

    po_number: str | None
    order_confirmation_number: str | None
    min_duration_months: int | None


@strawberry.type
class PdfAnalysisResultType:
    """Full result of analyzing a PDF attachment."""

    items: list[PdfComparisonItemType]
    metadata: PdfExtractedMetadataType
    metadata_comparisons: list[PdfMetadataComparisonType]
    error: str | None = None


@strawberry.input
class PdfImportItemInput:
    """Input for a single item to import from PDF analysis."""

    description: str
    quantity: int
    unit_price: Decimal
    price_period: str
    is_one_off: bool = False
    product_id: strawberry.ID | None = None
    existing_item_id: strawberry.ID | None = None


@strawberry.input
class PdfImportMetadataInput:
    """Input for metadata to import from PDF analysis."""

    po_number: str | None = UNSET
    order_confirmation_number: str | None = UNSET
    min_duration_months: int | None = UNSET


@strawberry.input
class ReorderContractItemsInput:
    """Input for reordering contract items."""
    contract_id: strawberry.ID
    item_ids: List[strawberry.ID]
    is_one_off: bool = False


@strawberry.input
class ImportPdfAnalysisInput:
    """Input for importing PDF analysis results."""

    contract_id: strawberry.ID
    items: list[PdfImportItemInput]
    metadata: PdfImportMetadataInput | None = None


@strawberry.type
class PdfImportResultType:
    """Result of importing PDF analysis data."""

    success: bool
    error: str | None = None
    created_items_count: int = 0
    updated_items_count: int = 0


# =============================================================================
# Comment Types
# =============================================================================


@strawberry.type
class CommentAuthorType:
    id: strawberry.ID
    first_name: str
    last_name: str


@strawberry.type
class ContractCommentType:
    id: strawberry.ID
    text: str
    author: CommentAuthorType
    created_at: datetime
    updated_at: datetime
    can_edit: bool
    can_delete: bool


@strawberry.type
class ContractCommentResult:
    comment: ContractCommentType | None = None
    success: bool = False
    error: str | None = None


def _build_contract_comment(comment: ContractComment, user) -> ContractCommentType:
    """Build a ContractCommentType from a model instance."""
    from django.utils import timezone

    is_author = comment.author_id == user.id
    is_latest = not ContractComment.objects.filter(
        contract=comment.contract,
        author=comment.author,
        created_at__gt=comment.created_at,
    ).exists()
    within_24h = (timezone.now() - comment.created_at).total_seconds() < 86400

    return ContractCommentType(
        id=strawberry.ID(str(comment.id)),
        text=comment.text,
        author=CommentAuthorType(
            id=strawberry.ID(str(comment.author_id)),
            first_name=comment.author.first_name,
            last_name=comment.author.last_name,
        ),
        created_at=comment.created_at,
        updated_at=comment.updated_at,
        can_edit=is_author and is_latest and within_24h,
        can_delete=is_author,
    )


@strawberry.type
class ContractQuery:
    @strawberry.field
    def dashboard_kpis(
        self,
        info: Info[Context, None],
    ) -> DashboardKPIsType:
        """
        Get dashboard KPI metrics for the current tenant's contract portfolio.

        Returns:
        - totalActiveContracts: Count of contracts with status=active
        - totalContractValue: Sum of all contract values over their duration
        - annualRecurringRevenue: Annualized value of recurring items
        - yearToDateRevenue: Revenue recognized from Jan 1 to today
        - currentYearForecast: Projected revenue for current year
        - nextYearForecast: Projected revenue for next year
        """
        user = require_perm(info, "contracts", "read")
        if not user.tenant:
            # Return zeros if no tenant
            return DashboardKPIsType(
                total_active_contracts=0,
                total_contract_value=Decimal("0"),
                annual_recurring_revenue=Decimal("0"),
                year_to_date_revenue=Decimal("0"),
                current_year_forecast=Decimal("0"),
                current_year_one_off=Decimal("0"),
                current_year_discounts=Decimal("0"),
                next_year_forecast=Decimal("0"),
                next_year_one_off=Decimal("0"),
                next_year_discounts=Decimal("0"),
            )

        kpis = calculate_dashboard_kpis(user.tenant)
        return DashboardKPIsType(
            total_active_contracts=kpis["total_active_contracts"],
            total_contract_value=kpis["total_contract_value"],
            annual_recurring_revenue=kpis["annual_recurring_revenue"],
            year_to_date_revenue=kpis["year_to_date_revenue"],
            current_year_forecast=kpis["current_year_forecast"],
            current_year_one_off=kpis["current_year_one_off"],
            current_year_discounts=kpis["current_year_discounts"],
            next_year_forecast=kpis["next_year_forecast"],
            next_year_one_off=kpis["next_year_one_off"],
            next_year_discounts=kpis["next_year_discounts"],
        )

    @strawberry.field
    def suggested_alignment_date(
        self,
        info: Info[Context, None],
        contract_id: strawberry.ID,
        billing_start_date: date,
    ) -> SuggestedAlignmentDateResult:
        """
        Calculate the suggested alignment date for a new contract item.

        Given a contract and the item's billing start date, returns the next
        contract billing cycle date for alignment.
        """
        user = require_perm(info, "contracts", "read")
        if not user.tenant:
            return SuggestedAlignmentDateResult(error="No tenant assigned")

        contract = Contract.objects.filter(
            tenant=user.tenant, id=contract_id
        ).first()
        if not contract:
            return SuggestedAlignmentDateResult(error="Contract not found")

        # Create a temporary item to calculate the suggestion
        temp_item = ContractItem(
            contract=contract,
            billing_start_date=billing_start_date,
        )
        suggested = temp_item.get_suggested_alignment_date()

        return SuggestedAlignmentDateResult(suggested_date=suggested)

    @strawberry.field
    def billing_schedule(
        self,
        info: Info[Context, None],
        contract_id: strawberry.ID,
        months: int = 13,
        include_history: bool = False,
        history_periods: int = 2,
    ) -> BillingScheduleResult:
        """
        Calculate the billing schedule for a contract.

        Args:
            contract_id: The contract to calculate for
            months: Number of months to forecast (default: 13)
            include_history: Include ALL past billing periods (default: False)
            history_periods: Number of past periods to always show (default: 2)
        """
        from dateutil.relativedelta import relativedelta

        user = require_perm(info, "contracts", "read")
        if not user.tenant:
            return BillingScheduleResult(
                events=[],
                total_forecast=Decimal("0"),
                period_start=date.today(),
                period_end=date.today(),
                error="No tenant assigned",
            )

        contract = Contract.objects.filter(
            tenant=user.tenant, id=contract_id
        ).first()
        if not contract:
            return BillingScheduleResult(
                events=[],
                total_forecast=Decimal("0"),
                period_start=date.today(),
                period_end=date.today(),
                error="Contract not found",
            )

        today = date.today()
        if include_history:
            # Show ALL history from billing start
            from_date = contract.billing_start_date
        else:
            # Show last N billing periods
            interval_months = contract.get_interval_months()
            from_date = today - relativedelta(months=interval_months * history_periods)
            # Don't go before contract billing start
            if from_date < contract.billing_start_date:
                from_date = contract.billing_start_date
        to_date = today + relativedelta(months=months)

        schedule = contract.get_billing_schedule(
            from_date=from_date,
            to_date=to_date,
            include_history=include_history,
            include_eta_items=True,
        )

        # Fetch invoices linked to this contract for matching
        from apps.invoices.models import CompanyLegalData, ImportedInvoice, InvoiceRecord

        # Get default tax rate for gross amount matching
        default_tax_rate = None
        try:
            default_tax_rate = user.tenant.legal_data.default_tax_rate
        except CompanyLegalData.DoesNotExist:
            pass

        contract_invoices = list(
            ImportedInvoice.objects.filter(
                tenant=user.tenant,
                contract_id=contract_id,
                invoice_date__isnull=False,
            ).select_related()
        )

        # Fetch generated invoice records (exact match by billing_date)
        invoice_records = {
            r.billing_date: r
            for r in InvoiceRecord.objects.filter(
                tenant=user.tenant,
                contract_id=contract_id,
            ).exclude(status=InvoiceRecord.Status.VOIDED)
        }

        # Convert to GraphQL types with invoice matching
        events = []
        for event in schedule:
            # First try exact match from generated InvoiceRecord
            record = invoice_records.get(event["date"])
            if record:
                pdf_url = record.pdf_file.url if record.pdf_file else None
                matched_invoice = MatchedInvoiceType(
                    id=strawberry.ID(str(record.id)),
                    invoice_number=record.invoice_number,
                    is_paid=record.is_paid,
                    pdf_url=pdf_url,
                )
            else:
                # Fall back to imported invoice heuristic
                matched_invoice = find_matching_invoice_for_billing_event(
                    contract_id=int(contract_id),
                    billing_date=event["date"],
                    invoices=contract_invoices,
                    expected_net=event["total"],
                    tax_rate=default_tax_rate,
                )
            events.append(
                BillingEvent(
                    date=event["date"],
                    items=[
                        BillingScheduleItem(
                            item_id=item["item_id"],
                            product_name=item["product_name"],
                            quantity=item["quantity"],
                            unit_price=item["unit_price"],
                            amount=item["amount"],
                            is_prorated=item["is_prorated"],
                            prorate_factor=item["prorate_factor"],
                            is_one_off=item.get("is_one_off", False),
                        )
                        for item in event["items"]
                    ],
                    total=event["total"],
                    matched_invoice=matched_invoice,
                )
            )

        total_forecast = sum(event.total for event in events)

        return BillingScheduleResult(
            events=events,
            total_forecast=total_forecast,
            period_start=from_date,
            period_end=to_date,
        )

    @strawberry.field
    def revenue_forecast(
        self,
        info: Info[Context, None],
        months: int | None = None,
        quarters: int | None = None,
        view: str = "monthly",
        pro_rata: bool = False,
        exclude_one_off: bool = False,
    ) -> RevenueForecastResult:
        """
        Calculate revenue forecast for all active contracts.

        Args:
            months: Number of months to forecast (for monthly view, default: 13)
            quarters: Number of quarters to forecast (for quarterly view, default: 6)
            view: "monthly" or "quarterly"
            pro_rata: If True, distribute billing amounts evenly across periods

        Returns a matrix with:
        - Rows: contracts (name, customer, revenue per period)
        - Columns: months or quarters
        - First data row: period totals
        """
        from collections import defaultdict
        from dateutil.relativedelta import relativedelta

        user = require_perm(info, "contracts", "read")
        if not user.tenant:
            return RevenueForecastResult(
                month_columns=[],
                monthly_totals=[],
                contracts=[],
                grand_total=Decimal("0"),
                error="No tenant assigned",
            )

        today = date.today()
        is_quarterly = view == "quarterly"

        # Always start from January 1st of the current year
        from_date = date(today.year, 1, 1)

        if is_quarterly:
            num_quarters = quarters if quarters is not None else 6
            to_date = from_date + relativedelta(months=num_quarters * 3)
        else:
            num_months = months if months is not None else 13
            to_date = from_date + relativedelta(months=num_months)

        # Generate period columns starting from January
        period_columns = []
        period_column_set = set()
        if is_quarterly:
            # Start from Q1
            current_quarter = 1
            current_year = today.year
            for _ in range(num_quarters):
                key = f"{current_year}-Q{current_quarter}"
                period_columns.append(key)
                period_column_set.add(key)
                current_quarter += 1
                if current_quarter > 4:
                    current_quarter = 1
                    current_year += 1
        else:
            # Start from January
            current = date(today.year, 1, 1)
            while current < to_date:
                key = current.strftime("%Y-%m")
                period_columns.append(key)
                period_column_set.add(key)
                current += relativedelta(months=1)

        # Get all active/paused contracts (exclude drafts - they're not committed yet)
        # Prefetch items with products and price_periods to avoid N+1 queries
        contracts = Contract.objects.filter(
            tenant=user.tenant,
            status__in=[Contract.Status.ACTIVE, Contract.Status.PAUSED],
        ).select_related("customer").prefetch_related("items__product", "items__price_periods", "items__depends_on")

        # Calculate revenue per contract per period
        contract_rows = []
        period_totals = defaultdict(Decimal)

        def get_period_key(event_date: date) -> str:
            if is_quarterly:
                quarter = (event_date.month - 1) // 3 + 1
                return f"{event_date.year}-Q{quarter}"
            return event_date.strftime("%Y-%m")

        # Billing interval to months mapping
        interval_months = {
            "monthly": 1,
            "quarterly": 3,
            "semi_annual": 6,
            "annual": 12,
            "biennial": 24,
            "triennial": 36,
            "quadrennial": 48,
            "quinquennial": 60,
        }

        for contract in contracts:
            # Optionally filter out one-off items for ARR-only view
            items_arg = None
            if exclude_one_off:
                items = list(
                    contract.items.select_related("product", "depends_on")
                    .prefetch_related("price_periods")
                    .filter(is_one_off=False)
                )
                if not items:
                    continue
                items_arg = items

            schedule = contract.get_billing_schedule(
                from_date=from_date,
                to_date=to_date,
                include_history=False,
                items=items_arg,
                include_eta_items=True,
            )

            # Group by period
            period_amounts = defaultdict(Decimal)

            if pro_rata:
                # Pro-rata: distribute each billing event across the months it covers
                billing_months = interval_months.get(contract.billing_interval, 1)

                for event in schedule:
                    event_total = event["total"]
                    event_date = event["date"]

                    if is_quarterly:
                        # For quarterly view, distribute across quarters
                        quarters_covered = max(1, billing_months // 3)
                        amount_per_quarter = event_total / quarters_covered

                        # Start from the billing quarter and go forward
                        q = (event_date.month - 1) // 3 + 1
                        y = event_date.year
                        for _ in range(quarters_covered):
                            period_key = f"{y}-Q{q}"
                            if period_key in period_column_set:
                                period_amounts[period_key] += amount_per_quarter
                            q += 1
                            if q > 4:
                                q = 1
                                y += 1
                    else:
                        # For monthly view, distribute across months
                        amount_per_month = event_total / billing_months

                        # Start from the billing month and go forward
                        dist_date = date(event_date.year, event_date.month, 1)
                        for _ in range(billing_months):
                            period_key = dist_date.strftime("%Y-%m")
                            if period_key in period_column_set:
                                period_amounts[period_key] += amount_per_month
                            dist_date += relativedelta(months=1)
            else:
                # Standard: show full amount in billing period
                for event in schedule:
                    period_key = get_period_key(event["date"])
                    period_amounts[period_key] += event["total"]

            # Build period data for this contract
            contract_periods = []
            contract_total = Decimal("0")
            for period in period_columns:
                amount = period_amounts.get(period, Decimal("0"))
                contract_periods.append(RevenueMonthData(month=period, amount=amount))
                contract_total += amount
                period_totals[period] += amount

            # Only include contracts with non-zero revenue
            if contract_total != 0:
                contract_name = contract.name or f"Vertrag {contract.id}"
                contract_rows.append(
                    ContractRevenueRow(
                        contract_id=contract.id,
                        contract_name=contract_name,
                        customer_id=contract.customer.id,
                        customer_name=contract.customer.name,
                        months=contract_periods,
                        total=contract_total,
                    )
                )

        # Build period totals list
        totals_list = [
            RevenueMonthData(month=period, amount=period_totals[period])
            for period in period_columns
        ]

        grand_total = sum(t.amount for t in totals_list)

        return RevenueForecastResult(
            month_columns=period_columns,
            monthly_totals=totals_list,
            contracts=contract_rows,
            grand_total=grand_total,
        )

    @strawberry.field
    def recognition_forecast(
        self,
        info: Info[Context, None],
        months: int | None = None,
        quarters: int | None = None,
        view: str = "monthly",
        pro_rata: bool = False,
        exclude_one_off: bool = False,
    ) -> RevenueForecastResult:
        """
        Calculate recognition forecast for all active contracts.

        This is similar to revenue_forecast but uses item.start_date (recognition date)
        instead of item.billing_start_date for timing.

        Args:
            months: Number of months to forecast (for monthly view, default: 13)
            quarters: Number of quarters to forecast (for quarterly view, default: 6)
            view: "monthly" or "quarterly"
            pro_rata: If True, distribute amounts evenly across periods

        Returns a matrix with:
        - Rows: contracts (name, customer, revenue per period)
        - Columns: months or quarters
        - First data row: period totals
        """
        from collections import defaultdict
        from dateutil.relativedelta import relativedelta

        user = require_perm(info, "contracts", "read")
        if not user.tenant:
            return RevenueForecastResult(
                month_columns=[],
                monthly_totals=[],
                contracts=[],
                grand_total=Decimal("0"),
                error="No tenant assigned",
            )

        today = date.today()
        is_quarterly = view == "quarterly"

        # Always start from January 1st of the current year
        from_date = date(today.year, 1, 1)

        if is_quarterly:
            num_quarters = quarters if quarters is not None else 6
            to_date = from_date + relativedelta(months=num_quarters * 3)
        else:
            num_months = months if months is not None else 13
            to_date = from_date + relativedelta(months=num_months)

        # Generate period columns starting from January
        period_columns = []
        period_column_set = set()
        if is_quarterly:
            # Start from Q1
            current_quarter = 1
            current_year = today.year
            for _ in range(num_quarters):
                key = f"{current_year}-Q{current_quarter}"
                period_columns.append(key)
                period_column_set.add(key)
                current_quarter += 1
                if current_quarter > 4:
                    current_quarter = 1
                    current_year += 1
        else:
            # Start from January
            current = date(today.year, 1, 1)
            while current < to_date:
                key = current.strftime("%Y-%m")
                period_columns.append(key)
                period_column_set.add(key)
                current += relativedelta(months=1)

        # Get all active/paused contracts (exclude drafts - they're not committed yet)
        # Prefetch items with products and price_periods to avoid N+1 queries
        contracts = Contract.objects.filter(
            tenant=user.tenant,
            status__in=[Contract.Status.ACTIVE, Contract.Status.PAUSED],
        ).select_related("customer").prefetch_related("items__product", "items__price_periods", "items__depends_on")

        # Calculate recognition per contract per period
        contract_rows = []
        period_totals = defaultdict(Decimal)

        def get_period_key(event_date: date) -> str:
            if is_quarterly:
                quarter = (event_date.month - 1) // 3 + 1
                return f"{event_date.year}-Q{quarter}"
            return event_date.strftime("%Y-%m")

        # Billing interval to months mapping
        interval_months = {
            "monthly": 1,
            "quarterly": 3,
            "semi_annual": 6,
            "annual": 12,
            "biennial": 24,
            "triennial": 36,
            "quadrennial": 48,
            "quinquennial": 60,
        }

        for contract in contracts:
            # Optionally filter out one-off items for ARR-only view
            items_arg = None
            if exclude_one_off:
                items = list(
                    contract.items.select_related("product", "depends_on")
                    .prefetch_related("price_periods")
                    .filter(is_one_off=False)
                )
                if not items:
                    continue
                items_arg = items

            # Use get_recognition_schedule instead of get_billing_schedule
            schedule = contract.get_recognition_schedule(
                from_date=from_date,
                to_date=to_date,
                include_history=False,
                items=items_arg,
                include_eta_items=True,
            )

            # Group by period
            period_amounts = defaultdict(Decimal)

            if pro_rata:
                # Pro-rata: distribute each recognition event across the months it covers
                billing_months = interval_months.get(contract.billing_interval, 1)

                for event in schedule:
                    event_total = event["total"]
                    event_date = event["date"]

                    if is_quarterly:
                        # For quarterly view, distribute across quarters
                        quarters_covered = max(1, billing_months // 3)
                        amount_per_quarter = event_total / quarters_covered

                        # Start from the recognition quarter and go forward
                        q = (event_date.month - 1) // 3 + 1
                        y = event_date.year
                        for _ in range(quarters_covered):
                            period_key = f"{y}-Q{q}"
                            if period_key in period_column_set:
                                period_amounts[period_key] += amount_per_quarter
                            q += 1
                            if q > 4:
                                q = 1
                                y += 1
                    else:
                        # For monthly view, distribute across months
                        amount_per_month = event_total / billing_months

                        # Start from the recognition month and go forward
                        dist_date = date(event_date.year, event_date.month, 1)
                        for _ in range(billing_months):
                            period_key = dist_date.strftime("%Y-%m")
                            if period_key in period_column_set:
                                period_amounts[period_key] += amount_per_month
                            dist_date += relativedelta(months=1)
            else:
                # Standard: show full amount in recognition period
                for event in schedule:
                    period_key = get_period_key(event["date"])
                    period_amounts[period_key] += event["total"]

            # Build period data for this contract
            contract_periods = []
            contract_total = Decimal("0")
            for period in period_columns:
                amount = period_amounts.get(period, Decimal("0"))
                contract_periods.append(RevenueMonthData(month=period, amount=amount))
                contract_total += amount
                period_totals[period] += amount

            # Only include contracts with non-zero revenue
            if contract_total != 0:
                contract_name = contract.name or f"Vertrag {contract.id}"
                contract_rows.append(
                    ContractRevenueRow(
                        contract_id=contract.id,
                        contract_name=contract_name,
                        customer_id=contract.customer.id,
                        customer_name=contract.customer.name,
                        months=contract_periods,
                        total=contract_total,
                    )
                )

        # Build period totals list
        totals_list = [
            RevenueMonthData(month=period, amount=period_totals[period])
            for period in period_columns
        ]

        grand_total = sum(t.amount for t in totals_list)

        return RevenueForecastResult(
            month_columns=period_columns,
            monthly_totals=totals_list,
            contracts=contract_rows,
            grand_total=grand_total,
        )

    @strawberry.field
    def contracts(
        self,
        info: Info[Context, None],
        search: str | None = None,
        status: str | None = None,
        include_deleted: bool = False,
        page: int = 1,
        page_size: int = 20,
        sort_by: str | None = "updated_at",
        sort_order: str | None = "desc",
    ) -> ContractConnection:
        """Get paginated list of contracts with filtering and sorting."""
        user = require_perm(info, "contracts", "read")
        if not user.tenant:
            return ContractConnection(
                items=[],
                total_count=0,
                page=page,
                page_size=page_size,
                has_next_page=False,
                has_previous_page=False,
            )

        queryset = Contract.objects.filter(tenant=user.tenant).select_related("customer")

        # Exclude deleted by default unless specifically requested or filtering by deleted status
        if not include_deleted and status != "deleted":
            queryset = queryset.exclude(status=Contract.Status.DELETED)

        # Search filter (by customer name, contract name, or NetSuite IDs)
        if search:
            queryset = queryset.filter(
                Q(customer__name__icontains=search) |
                Q(name__icontains=search) |
                Q(netsuite_sales_order_number__icontains=search) |
                Q(netsuite_contract_number__icontains=search) |
                Q(po_number__icontains=search)
            )

        # Status filter (accounts for effective_status: active contracts
        # with end_date in the past are effectively "ended")
        if status:
            if status == "active":
                queryset = queryset.filter(status="active").filter(
                    Q(end_date__isnull=True) | Q(end_date__gte=date.today())
                )
            elif status == "ended":
                queryset = queryset.filter(
                    Q(status="ended") |
                    Q(status="active", end_date__lt=date.today())
                )
            else:
                queryset = queryset.filter(status=status)

        # Sorting
        allowed_sort_fields = {
            "created_at",
            "updated_at",
            "start_date",
            "end_date",
            "status",
            "customer_name",
            "name",
            "arr",
        }
        if sort_by == "customer_name":
            order_field = "-customer__name" if sort_order == "desc" else "customer__name"
        elif sort_by == "arr":
            # Sort by ARR in Python (monthly_recurring * 12)
            all_contracts = list(queryset.prefetch_related("items"))

            def get_arr(contract):
                from decimal import Decimal
                from datetime import date as date_type
                today = date_type.today()

                monthly_total = Decimal("0")
                for item in contract.items.all():
                    if not item.is_one_off:
                        monthly_unit_price = item.get_price_at(today, normalize_to_monthly=True)
                        monthly_total += monthly_unit_price * item.quantity
                return monthly_total * 12

            reverse = sort_order == "desc"
            all_contracts.sort(key=get_arr, reverse=reverse)

            total_count = len(all_contracts)
            offset = (page - 1) * page_size
            items = all_contracts[offset : offset + page_size]

            return ContractConnection(
                items=items,
                total_count=total_count,
                page=page,
                page_size=page_size,
                has_next_page=offset + page_size < total_count,
                has_previous_page=page > 1,
            )
        elif sort_by and sort_by in allowed_sort_fields:
            order_field = f"-{sort_by}" if sort_order == "desc" else sort_by
        else:
            order_field = "-updated_at"
        queryset = queryset.order_by(order_field)

        total_count = queryset.count()

        # Pagination
        offset = (page - 1) * page_size
        items = list(queryset[offset : offset + page_size])

        return ContractConnection(
            items=items,
            total_count=total_count,
            page=page,
            page_size=page_size,
            has_next_page=offset + page_size < total_count,
            has_previous_page=page > 1,
        )

    @strawberry.field
    def contract(
        self, info: Info[Context, None], id: strawberry.ID
    ) -> ContractType | None:
        """Get a single contract by ID."""
        user = require_perm(info, "contracts", "read")
        if user.tenant:
            return Contract.objects.filter(tenant=user.tenant, id=id).first()
        return None

    @strawberry.field
    def contract_groups(
        self, info: Info[Context, None], customer_id: strawberry.ID
    ) -> list[ContractGroupType]:
        """Get all contract groups for a customer."""
        user = require_perm(info, "contracts", "read")
        if not user.tenant:
            return []

        # Verify customer belongs to tenant
        customer = Customer.objects.filter(tenant=user.tenant, id=customer_id).first()
        if not customer:
            return []

        groups = ContractGroup.objects.filter(customer=customer).order_by("name")
        return [
            ContractGroupType(
                id=g.id,
                name=g.name,
                contract_count=Contract.objects.filter(group=g).count(),
            )
            for g in groups
        ]

    @strawberry.field
    def time_tracking_projects(
        self, info: Info[Context, None], search: str = ""
    ) -> list[TimeTrackingExternalProject]:
        """Fetch projects from the configured time tracking provider."""
        from apps.contracts.services.time_tracking import get_provider

        user = require_perm(info, "contracts", "read")
        if not user.tenant:
            return []

        provider = get_provider(user.tenant)
        if not provider:
            return []

        projects = provider.get_projects()
        if search:
            search_lower = search.lower()
            projects = [
                p for p in projects
                if search_lower in p.name.lower()
                or search_lower in p.customer_name.lower()
            ]

        return [
            TimeTrackingExternalProject(
                id=p.id,
                name=p.name,
                customer_name=p.customer_name,
                active=p.active,
            )
            for p in projects
        ]

    @strawberry.field
    def time_tracking_summary(
        self, info: Info[Context, None], contract_id: strawberry.ID
    ) -> TimeTrackingSummaryType | None:
        """Get time tracking summary for a contract's mapped projects (from DB cache)."""
        from apps.contracts.services.time_tracking import get_cached_summary

        user = require_perm(info, "contracts", "read")
        if not user.tenant:
            return None

        contract = Contract.objects.filter(
            tenant=user.tenant, id=contract_id
        ).first()
        if not contract:
            return None

        mappings = TimeTrackingProjectMapping.objects.filter(
            tenant=user.tenant, contract=contract
        ).select_related("contract_item", "contract_item__product")
        mapping_types = [
            TimeTrackingMappingType(
                id=m.id,
                external_project_id=m.external_project_id,
                external_project_name=m.external_project_name,
                external_customer_name=m.external_customer_name,
                contract_item_id=m.contract_item_id,
                contract_item_name=(
                    m.contract_item.product.name if m.contract_item and m.contract_item.product
                    else m.contract_item.description[:50] if m.contract_item
                    else None
                ),
                cached_total_hours=m.cached_total_hours,
            )
            for m in mappings
        ]

        if not mappings.exists():
            return TimeTrackingSummaryType(
                total_hours=0,
                total_revenue=0,
                by_service=[],
                by_month=[],
                mappings=mapping_types,
            )

        cached = get_cached_summary(mappings)
        return TimeTrackingSummaryType(
            total_hours=cached["total_hours"],
            total_revenue=cached["total_revenue"],
            by_service=[
                ServiceBreakdown(
                    service_name=s["service_name"],
                    hours=s["hours"],
                    revenue=s["revenue"],
                )
                for s in cached["by_service"]
            ],
            by_month=[
                MonthlyBreakdown(
                    month=m["month"],
                    hours=m["hours"],
                    revenue=m["revenue"],
                )
                for m in cached["by_month"]
            ],
            mappings=mapping_types,
            last_synced=cached["last_synced"],
        )

    @strawberry.field
    def analyze_pdf_attachment(
        self,
        info: Info[Context, None],
        attachment_id: strawberry.ID,
    ) -> PdfAnalysisResultType:
        """Analyze a PDF attachment and extract structured contract data."""
        from apps.contracts.services.pdf_analysis import analyze_pdf_attachment as do_analyze

        user, err = check_perm(info, "contracts", "read")
        if err:
            return PdfAnalysisResultType(
                items=[],
                metadata=PdfExtractedMetadataType(
                    po_number=None, order_confirmation_number=None,
                    min_duration_months=None,
                ),
                metadata_comparisons=[],
                error=err,
            )
        if not user.tenant:
            return PdfAnalysisResultType(
                items=[],
                metadata=PdfExtractedMetadataType(
                    po_number=None, order_confirmation_number=None,
                    min_duration_months=None,
                ),
                metadata_comparisons=[],
                error="No tenant assigned",
            )

        attachment = ContractAttachment.objects.filter(
            tenant=user.tenant, id=attachment_id
        ).first()
        if not attachment:
            return PdfAnalysisResultType(
                items=[],
                metadata=PdfExtractedMetadataType(
                    po_number=None, order_confirmation_number=None,
                    min_duration_months=None,
                ),
                metadata_comparisons=[],
                error="Attachment not found",
            )

        result = do_analyze(attachment, user.tenant)
        return _build_pdf_analysis_result(result)

    @strawberry.field
    def deliverable_items(
        self,
        info: Info[Context, None],
        status: str | None = None,
        customer_id: strawberry.ID | None = None,
    ) -> List[DeliverableItemType]:
        """List all items with delivery tracking for the projects overview."""
        user = require_perm(info, "contracts", "read")
        if not user.tenant:
            return []

        qs = ContractItem.objects.filter(
            tenant=user.tenant,
            delivery_status__isnull=False,
        ).select_related("contract", "contract__customer", "product")

        if status:
            qs = qs.filter(delivery_status=status)

        if customer_id:
            qs = qs.filter(contract__customer_id=customer_id)

        from django.db.models import Count
        qs = qs.annotate(dep_count=Count("dependent_items"))

        return [
            DeliverableItemType(
                id=item.id,
                product_name=item.product.name if item.product else None,
                description=item.description,
                is_one_off=item.is_one_off,
                delivery_status=item.delivery_status,
                delivered_at=item.delivered_at,
                estimated_delivery_date=item.estimated_delivery_date,
                contract_id=item.contract_id,
                contract_name=item.contract.name or "",
                customer_name=item.contract.customer.name,
                customer_id=item.contract.customer_id,
                dependent_items_count=item.dep_count,
            )
            for item in qs.order_by("-contract__created_at")
        ]

    @strawberry.field
    def contract_comments(
        self,
        info: Info[Context, None],
        contract_id: strawberry.ID,
    ) -> List[ContractCommentType]:
        """Get all comments for a contract, newest first."""
        user = require_perm(info, "contracts", "read")
        if not user.tenant:
            return []

        comments = ContractComment.objects.filter(
            tenant=user.tenant, contract_id=contract_id
        ).select_related("author")
        return [_build_contract_comment(c, user) for c in comments]


def _check_price_period_overlap(
    item: ContractItem,
    valid_from: date,
    valid_to: date | None,
    exclude_id: int | None = None,
) -> str | None:
    """Check if a price period overlaps with existing periods.

    Returns an error message if overlap exists, None otherwise.
    """
    existing_periods = ContractItemPrice.objects.filter(item=item)
    if exclude_id:
        existing_periods = existing_periods.exclude(id=exclude_id)

    for period in existing_periods:
        # Two ranges [A_start, A_end] and [B_start, B_end] overlap if:
        # A_start <= B_end AND B_start <= A_end
        # For open-ended (None), treat as infinity
        a_start, a_end = period.valid_from, period.valid_to
        b_start, b_end = valid_from, valid_to

        # Check if ranges overlap
        # a_start <= b_end (if b_end is None, always true)
        # b_start <= a_end (if a_end is None, always true)
        a_before_b_ends = b_end is None or a_start <= b_end
        b_before_a_ends = a_end is None or b_start <= a_end

        if a_before_b_ends and b_before_a_ends:
            period_end = period.valid_to.isoformat() if period.valid_to else "ongoing"
            return f"Price period overlaps with existing period ({period.valid_from.isoformat()} to {period_end})"

    return None


def _build_pdf_analysis_result(result):
    """Convert pdf_analysis dataclass result to GraphQL types."""
    from apps.contracts.services.pdf_analysis import PdfAnalysisResult as ServiceResult

    if result.error:
        return PdfAnalysisResultType(
            items=[],
            metadata=PdfExtractedMetadataType(
                po_number=None,
                order_confirmation_number=None,
                min_duration_months=None,
            ),
            metadata_comparisons=[],
            error=result.error,
        )

    items = []
    for comp in result.items:
        product_match = None
        if comp.product_match:
            product_match = PdfProductMatchType(
                product_id=comp.product_match.product_id,
                product_name=comp.product_match.product_name,
                confidence=comp.product_match.confidence,
            )
        items.append(
            PdfComparisonItemType(
                extracted=PdfExtractedItemType(
                    description=comp.extracted.description,
                    quantity=comp.extracted.quantity,
                    unit_price=comp.extracted.unit_price,
                    price_period=comp.extracted.price_period,
                    is_one_off=comp.extracted.is_one_off,
                ),
                product_match=product_match,
                status=comp.status,
                existing_item_id=comp.existing_item_id,
                price_differs=comp.price_differs,
            )
        )

    metadata = PdfExtractedMetadataType(
        po_number=result.metadata.po_number,
        order_confirmation_number=result.metadata.order_confirmation_number,
        min_duration_months=result.metadata.min_duration_months,
    )

    metadata_comparisons = [
        PdfMetadataComparisonType(
            field_name=mc.field_name,
            extracted_value=mc.extracted_value,
            current_value=mc.current_value,
            differs=mc.differs,
        )
        for mc in result.metadata_comparisons
    ]

    return PdfAnalysisResultType(
        items=items,
        metadata=metadata,
        metadata_comparisons=metadata_comparisons,
    )


@strawberry.type
class ContractMutation:
    @strawberry.mutation
    def create_contract(
        self, info: Info[Context, None], input: CreateContractInput
    ) -> ContractResult:
        """Create a new contract."""
        user, err = check_perm(info, "contracts", "write")
        if err:
            return ContractResult(error=err)
        if not user.tenant:
            return ContractResult(error="No tenant assigned")

        # Verify customer belongs to tenant
        customer = Customer.objects.filter(
            tenant=user.tenant, id=input.customer_id
        ).first()
        if not customer:
            return ContractResult(error="Customer not found")

        # Validate group belongs to same customer
        group = None
        if input.group_id:
            group = ContractGroup.objects.filter(
                tenant=user.tenant, id=input.group_id, customer=customer
            ).first()
            if not group:
                return ContractResult(error="Group not found or belongs to a different customer")

        try:
            contract = Contract.objects.create(
                tenant=user.tenant,
                customer=customer,
                name=input.name or "",
                netsuite_sales_order_number=input.sales_order_number or "",
                netsuite_url=input.netsuite_url or "",
                po_number=input.po_number,
                order_confirmation_number=input.order_confirmation_number,
                notes=input.notes or "",
                status=Contract.Status.DRAFT,
                start_date=input.start_date,
                end_date=input.end_date,
                billing_start_date=input.billing_start_date or input.start_date,
                billing_interval=input.billing_interval,
                billing_anchor_day=input.billing_anchor_day,
                billing_alignment_date=input.billing_alignment_date,
                min_duration_months=input.min_duration_months,
                notice_period_months=input.notice_period_months,
                notice_period_anchor=input.notice_period_anchor,
                notice_period_after_min_months=input.notice_period_after_min_months,
                group=group,
            )
            return ContractResult(contract=contract, success=True)
        except Exception as e:
            return ContractResult(error=str(e))

    @strawberry.mutation
    def update_contract(
        self, info: Info[Context, None], input: UpdateContractInput
    ) -> ContractResult:
        """Update an existing contract."""
        user, err = check_perm(info, "contracts", "write")
        if err:
            return ContractResult(error=err)
        if not user.tenant:
            return ContractResult(error="No tenant assigned")

        contract = Contract.objects.filter(
            tenant=user.tenant, id=input.id
        ).first()
        if not contract:
            return ContractResult(error="Contract not found")

        try:
            if input.name is not None:
                contract.name = input.name
            if input.sales_order_number is not None:
                contract.netsuite_sales_order_number = input.sales_order_number
            if input.netsuite_url is not None:
                contract.netsuite_url = input.netsuite_url
            if input.po_number is not None:
                contract.po_number = input.po_number
            if input.order_confirmation_number is not None:
                contract.order_confirmation_number = input.order_confirmation_number
            if input.notes is not None:
                contract.notes = input.notes
            if input.invoice_text is not None:
                contract.invoice_text = input.invoice_text
            if input.start_date is not None:
                contract.start_date = input.start_date
            if input.billing_start_date is not None:
                contract.billing_start_date = input.billing_start_date
            if input.end_date is not UNSET:
                contract.end_date = input.end_date
            if input.billing_interval is not None:
                contract.billing_interval = input.billing_interval
            if input.billing_anchor_day is not None:
                contract.billing_anchor_day = input.billing_anchor_day
            if input.billing_alignment_date is not UNSET:
                contract.billing_alignment_date = input.billing_alignment_date
            if input.min_duration_months is not None:
                contract.min_duration_months = input.min_duration_months
            if input.notice_period_months is not None:
                contract.notice_period_months = input.notice_period_months
            if input.notice_period_anchor is not None:
                contract.notice_period_anchor = input.notice_period_anchor
            if input.notice_period_after_min_months is not None:
                contract.notice_period_after_min_months = input.notice_period_after_min_months
            if input.group_id is not UNSET:
                if input.group_id is None:
                    contract.group = None
                else:
                    group = ContractGroup.objects.filter(
                        tenant=user.tenant, id=input.group_id, customer=contract.customer
                    ).first()
                    if not group:
                        return ContractResult(error="Group not found or belongs to a different customer")
                    contract.group = group

            contract.save()
            return ContractResult(contract=contract, success=True)
        except Exception as e:
            return ContractResult(error=str(e))

    @strawberry.mutation
    def add_contract_item(
        self,
        info: Info[Context, None],
        contract_id: strawberry.ID,
        input: ContractItemInput,
    ) -> ContractItemResult:
        """Add an item to a contract."""
        user, err = check_perm(info, "contracts", "write")
        if err:
            return ContractItemResult(error=err)
        if not user.tenant:
            return ContractItemResult(error="No tenant assigned")

        contract = Contract.objects.filter(
            tenant=user.tenant, id=contract_id
        ).first()
        if not contract:
            return ContractItemResult(error="Contract not found")

        # Product is optional - either product or description is required
        product = None
        if input.product_id:
            product = Product.objects.filter(
                tenant=user.tenant, id=input.product_id
            ).first()
            if not product:
                return ContractItemResult(error="Product not found")
        elif not input.description:
            return ContractItemResult(error="Either product or description is required")

        # Validate depends_on if provided
        depends_on_item = None
        if input.depends_on_item_id:
            depends_on_item = ContractItem.objects.filter(
                contract=contract, id=input.depends_on_item_id
            ).first()
            if not depends_on_item:
                return ContractItemResult(error="Dependency item not found in this contract")
            if not depends_on_item.delivery_status:
                return ContractItemResult(error="Dependency target must have delivery tracking enabled")

        try:
            with transaction.atomic():
                item = ContractItem.objects.create(
                    tenant=user.tenant,
                    contract=contract,
                    product=product,
                    description=input.description,
                    quantity=input.quantity,
                    unit_price=input.unit_price,
                    price_period=input.price_period,
                    price_source=input.price_source,
                    start_date=input.start_date,
                    billing_start_date=input.billing_start_date,
                    align_to_contract_at=input.align_to_contract_at,
                    is_one_off=input.is_one_off,
                    order_confirmation_number=input.order_confirmation_number,
                    delivery_status="pending" if input.delivery_tracking else None,
                    estimated_delivery_date=input.estimated_delivery_date if input.delivery_tracking else None,
                    depends_on=depends_on_item,
                )

                # Create amendment record only for non-draft contracts
                if contract.status != Contract.Status.DRAFT:
                    item_name = product.name if product else input.description[:50]
                    ContractAmendment.objects.create(
                        tenant=user.tenant,
                        contract=contract,
                        effective_date=date.today(),
                        type=ContractAmendment.AmendmentType.PRODUCT_ADDED,
                        description=f"Added {item_name} x{input.quantity}",
                        changes={
                            "product_id": str(product.id) if product else None,
                            "product_name": product.name if product else None,
                            "description": input.description,
                            "quantity": input.quantity,
                            "unit_price": str(input.unit_price),
                        },
                    )

            # Get effective price for today (for new items, this is just the item price)
            effective_price, effective_price_period = item.get_effective_price_info(date.today())
            return ContractItemResult(
                item=ContractItemType(
                    id=item.id,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    price_period=item.price_period,
                    price_source=item.price_source,
                    total_price=item.total_price,
                    effective_price=effective_price,
                    effective_price_period=effective_price_period,
                    product=product,
                    description=item.description,
                    start_date=item.start_date,
                    billing_start_date=item.billing_start_date,
                    billing_end_date=item.billing_end_date,
                    align_to_contract_at=item.align_to_contract_at,
                    suggested_alignment_date=item.get_suggested_alignment_date() if product else None,
                    is_one_off=item.is_one_off,
                    order_confirmation_number=item.order_confirmation_number,
                    price_locked=item.price_locked,
                    price_locked_until=item.price_locked_until,
                    sort_order=item.sort_order,
                    delivery_status=item.delivery_status,
                    delivered_at=item.delivered_at,
                    estimated_delivery_date=item.estimated_delivery_date,
                    depends_on=None,
                    dependent_items=[],
                    price_periods=[],  # Newly created items have no price periods
                ),
                success=True,
            )
        except Exception as e:
            return ContractItemResult(error=str(e))

    @strawberry.mutation
    def update_contract_item(
        self, info: Info[Context, None], input: UpdateContractItemInput
    ) -> ContractItemResult:
        """Update a contract item."""
        user, err = check_perm(info, "contracts", "write")
        if err:
            return ContractItemResult(error=err)
        if not user.tenant:
            return ContractItemResult(error="No tenant assigned")

        item = ContractItem.objects.filter(
            tenant=user.tenant, id=input.id
        ).select_related("contract", "product").first()
        if not item:
            return ContractItemResult(error="Item not found")

        try:
            with transaction.atomic():
                old_values = {
                    "quantity": item.quantity,
                    "unit_price": str(item.unit_price),
                    "price_source": item.price_source,
                    "description": item.description,
                    "product_id": str(item.product_id) if item.product_id else None,
                    "product_name": item.product.name if item.product else None,
                }

                # Check if price is locked
                is_price_locked = item.price_locked and (
                    item.price_locked_until is None or item.price_locked_until >= date.today()
                )

                # Handle product change
                if input.product_id is not None:
                    product = Product.objects.filter(
                        tenant=user.tenant, id=input.product_id
                    ).first()
                    if not product:
                        return ContractItemResult(error="Product not found")
                    item.product = product

                if input.description is not None:
                    item.description = input.description
                if input.quantity is not None:
                    item.quantity = input.quantity
                if input.unit_price is not None:
                    if is_price_locked:
                        return ContractItemResult(error="Price is locked and cannot be changed")
                    item.unit_price = input.unit_price
                if input.price_period is not None:
                    item.price_period = input.price_period
                if input.price_source is not None:
                    item.price_source = input.price_source
                if input.start_date is not UNSET:
                    item.start_date = input.start_date
                if input.billing_start_date is not UNSET:
                    item.billing_start_date = input.billing_start_date
                if input.billing_end_date is not UNSET:
                    item.billing_end_date = input.billing_end_date
                if input.align_to_contract_at is not UNSET:
                    item.align_to_contract_at = input.align_to_contract_at
                if input.is_one_off is not None:
                    item.is_one_off = input.is_one_off
                if input.order_confirmation_number is not None:
                    item.order_confirmation_number = input.order_confirmation_number
                if input.price_locked is not None:
                    item.price_locked = input.price_locked
                if input.price_locked_until is not UNSET:
                    item.price_locked_until = input.price_locked_until
                if input.delivery_tracking is not None:
                    if input.delivery_tracking:
                        if not item.delivery_status:
                            item.delivery_status = "pending"
                    else:
                        item.delivery_status = None
                        item.delivered_at = None
                        item.estimated_delivery_date = None
                if input.estimated_delivery_date is not UNSET:
                    # Only set ETA on pending deliverable items
                    if item.delivery_status == "pending":
                        item.estimated_delivery_date = input.estimated_delivery_date
                if input.depends_on_item_id is not UNSET:
                    if input.depends_on_item_id is None:
                        item.depends_on = None
                    else:
                        if str(input.depends_on_item_id) == str(item.id):
                            return ContractItemResult(error="An item cannot depend on itself")
                        dep_item = ContractItem.objects.filter(
                            contract=item.contract, id=input.depends_on_item_id
                        ).first()
                        if not dep_item:
                            return ContractItemResult(error="Dependency item not found in this contract")
                        if not dep_item.delivery_status:
                            return ContractItemResult(error="Dependency target must have delivery tracking enabled")
                        item.depends_on = dep_item

                item.save()

                # Create amendment record only for non-draft contracts
                if item.contract.status != Contract.Status.DRAFT:
                    new_values = {
                        "quantity": item.quantity,
                        "unit_price": str(item.unit_price),
                        "price_source": item.price_source,
                        "description": item.description,
                        "product_id": str(item.product_id) if item.product_id else None,
                    }

                    # Only create amendment if something actually changed
                    has_changes = any(
                        new_values.get(k) != old_values.get(k)
                        for k in ("quantity", "unit_price", "price_source", "description", "product_id")
                    )

                    if has_changes:
                        # Determine amendment type
                        item_name = item.product.name if item.product else (item.description or "")[:50]
                        if input.product_id is not None and old_values["product_id"] != str(input.product_id):
                            amendment_type = ContractAmendment.AmendmentType.TERMS_CHANGED
                            description = f"Changed product from {old_values['product_name'] or 'none'} to {item_name}"
                        elif input.quantity is not None and old_values["quantity"] != input.quantity:
                            amendment_type = ContractAmendment.AmendmentType.QUANTITY_CHANGED
                            description = f"Changed {item_name} quantity from {old_values['quantity']} to {input.quantity}"
                        elif input.unit_price is not None and old_values["unit_price"] != str(input.unit_price):
                            amendment_type = ContractAmendment.AmendmentType.PRICE_CHANGED
                            description = f"Changed {item_name} price from {old_values['unit_price']} to {input.unit_price}"
                        else:
                            amendment_type = ContractAmendment.AmendmentType.TERMS_CHANGED
                            description = f"Updated {item_name}"

                        ContractAmendment.objects.create(
                            tenant=user.tenant,
                            contract=item.contract,
                            effective_date=date.today(),
                            type=amendment_type,
                            description=description,
                            changes={
                                "item_id": str(item.id),
                                "product_name": item.product.name if item.product else None,
                                "description": item.description,
                                "old_values": old_values,
                                "new_values": new_values,
                            },
                        )

            # Get price periods
            price_periods = [
                ContractItemPriceType(
                    id=pp.id,
                    valid_from=pp.valid_from,
                    valid_to=pp.valid_to,
                    unit_price=pp.unit_price,
                    price_period=pp.price_period,
                    source=pp.source,
                )
                for pp in item.price_periods.all()
            ]

            # Get effective price for today
            effective_price, effective_price_period = item.get_effective_price_info(date.today())
            return ContractItemResult(
                item=ContractItemType(
                    id=item.id,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    price_period=item.price_period,
                    price_source=item.price_source,
                    total_price=item.total_price,
                    effective_price=effective_price,
                    effective_price_period=effective_price_period,
                    product=item.product,
                    description=item.description,
                    start_date=item.start_date,
                    billing_start_date=item.billing_start_date,
                    billing_end_date=item.billing_end_date,
                    align_to_contract_at=item.align_to_contract_at,
                    suggested_alignment_date=item.get_suggested_alignment_date() if item.product else None,
                    is_one_off=item.is_one_off,
                    order_confirmation_number=item.order_confirmation_number,
                    price_locked=item.price_locked,
                    price_locked_until=item.price_locked_until,
                    sort_order=item.sort_order,
                    delivery_status=item.delivery_status,
                    delivered_at=item.delivered_at,
                    estimated_delivery_date=item.estimated_delivery_date,
                    depends_on=None,
                    dependent_items=[],
                    price_periods=price_periods,
                ),
                success=True,
            )
        except Exception as e:
            return ContractItemResult(error=str(e))

    @strawberry.mutation
    def remove_contract_item(
        self, info: Info[Context, None], item_id: strawberry.ID
    ) -> DeleteResult:
        """Remove an item from a contract."""
        user, err = check_perm(info, "contracts", "write")
        if err:
            return DeleteResult(error=err)
        if not user.tenant:
            return DeleteResult(error="No tenant assigned")

        item = ContractItem.objects.filter(
            tenant=user.tenant, id=item_id
        ).select_related("contract", "product").first()
        if not item:
            return DeleteResult(error="Item not found")

        try:
            with transaction.atomic():
                # Create amendment record only for non-draft contracts
                if item.contract.status != Contract.Status.DRAFT:
                    item_name = item.product.name if item.product else (item.description or "")[:50]
                    ContractAmendment.objects.create(
                        tenant=user.tenant,
                        contract=item.contract,
                        effective_date=date.today(),
                        type=ContractAmendment.AmendmentType.PRODUCT_REMOVED,
                        description=f"Removed {item_name}",
                        changes={
                            "product_id": str(item.product.id) if item.product else None,
                            "product_name": item.product.name if item.product else None,
                            "description": item.description,
                            "quantity": item.quantity,
                            "unit_price": str(item.unit_price),
                        },
                    )

                item.delete()

            return DeleteResult(success=True)
        except Exception as e:
            return DeleteResult(error=str(e))

    @strawberry.mutation
    def cancel_contract(
        self,
        info: Info[Context, None],
        contract_id: strawberry.ID,
        effective_date: date,
    ) -> ContractResult:
        """Cancel a contract."""
        user, err = check_perm(info, "contracts", "write")
        if err:
            return ContractResult(error=err)
        if not user.tenant:
            return ContractResult(error="No tenant assigned")

        contract = Contract.objects.filter(
            tenant=user.tenant, id=contract_id
        ).first()
        if not contract:
            return ContractResult(error="Contract not found")

        if contract.status == Contract.Status.CANCELLED:
            return ContractResult(error="Contract is already cancelled")

        try:
            with transaction.atomic():
                contract.status = Contract.Status.CANCELLED
                contract.cancelled_at = datetime.now()
                contract.cancellation_effective_date = effective_date
                contract.save()

                ContractAmendment.objects.create(
                    tenant=user.tenant,
                    contract=contract,
                    effective_date=effective_date,
                    type=ContractAmendment.AmendmentType.TERMS_CHANGED,
                    description=f"Contract cancelled, effective {effective_date}",
                    changes={
                        "action": "cancellation",
                        "effective_date": str(effective_date),
                    },
                )

            return ContractResult(contract=contract, success=True)
        except Exception as e:
            return ContractResult(error=str(e))

    @strawberry.mutation
    def delete_contract(
        self,
        info: Info[Context, None],
        contract_id: strawberry.ID,
    ) -> ContractResult:
        """Soft delete a contract (set status to deleted)."""
        user, err = check_perm(info, "contracts", "write")
        if err:
            return ContractResult(error=err)
        if not user.tenant:
            return ContractResult(error="No tenant assigned")

        contract = Contract.objects.filter(
            tenant=user.tenant, id=contract_id
        ).first()
        if not contract:
            return ContractResult(error="Contract not found")

        if contract.status == Contract.Status.DELETED:
            return ContractResult(error="Contract is already deleted")

        try:
            with transaction.atomic():
                old_status = contract.status
                contract.status = Contract.Status.DELETED
                contract.save()

                ContractAmendment.objects.create(
                    tenant=user.tenant,
                    contract=contract,
                    effective_date=date.today(),
                    type=ContractAmendment.AmendmentType.TERMS_CHANGED,
                    description=f"Contract deleted (was: {old_status})",
                    changes={
                        "action": "deletion",
                        "previous_status": old_status,
                    },
                )

            return ContractResult(contract=contract, success=True)
        except Exception as e:
            return ContractResult(error=str(e))

    @strawberry.mutation
    def transition_contract_status(
        self,
        info: Info[Context, None],
        contract_id: strawberry.ID,
        new_status: str,
    ) -> ContractResult:
        """
        Transition a contract to a new status.

        Allowed transitions:
        - draft -> active
        - active -> paused, cancelled, draft (if no invoices)
        - paused -> active, cancelled
        - cancelled -> ended
        - ended -> draft (if no invoices)
        """
        user, err = check_perm(info, "contracts", "write")
        if err:
            return ContractResult(error=err)
        if not user.tenant:
            return ContractResult(error="No tenant assigned")

        contract = Contract.objects.filter(
            tenant=user.tenant, id=contract_id
        ).first()
        if not contract:
            return ContractResult(error="Contract not found")

        # Define allowed transitions
        allowed_transitions = {
            Contract.Status.DRAFT: [Contract.Status.ACTIVE],
            Contract.Status.ACTIVE: [Contract.Status.PAUSED, Contract.Status.CANCELLED, Contract.Status.DRAFT],
            Contract.Status.PAUSED: [Contract.Status.ACTIVE, Contract.Status.CANCELLED],
            Contract.Status.CANCELLED: [Contract.Status.ENDED],
            Contract.Status.ENDED: [Contract.Status.DRAFT],
        }

        current_status = contract.status
        allowed = allowed_transitions.get(current_status, [])

        if new_status not in allowed:
            return ContractResult(
                error=f"Cannot transition from {current_status} to {new_status}"
            )

        # Guard: reset to draft blocked if invoices exist
        if new_status == Contract.Status.DRAFT:
            if contract.invoice_records.exists():
                return ContractResult(
                    error="Cannot reset to draft: contract has invoices"
                )

        # Guard: activation checklist (only for draft → active)
        if (
            new_status == Contract.Status.ACTIVE
            and current_status == Contract.Status.DRAFT
        ):
            tenant_settings = user.tenant.settings or {}
            required_fields = tenant_settings.get("activation_required_fields", [])
            missing = []
            for field_name in required_fields:
                if hasattr(contract, field_name):
                    value = getattr(contract, field_name)
                    if not value:
                        missing.append(field_name)
            if missing:
                return ContractResult(
                    error=f"Missing required fields: {', '.join(missing)}"
                )

        try:
            with transaction.atomic():
                # Re-fetch with lock for reset to draft (prevents race with invoice generation)
                if new_status == Contract.Status.DRAFT:
                    contract = Contract.objects.select_for_update().get(
                        tenant=user.tenant, id=contract_id
                    )
                    # Re-check invoices under lock
                    if contract.invoice_records.exists():
                        return ContractResult(
                            error="Cannot reset to draft: contract has invoices"
                        )

                old_status = contract.status
                contract.status = new_status

                # Set timestamps for specific transitions
                if new_status == Contract.Status.CANCELLED:
                    contract.cancelled_at = datetime.now()
                    contract.cancellation_effective_date = date.today()

                contract.save()

                # Reset to draft: delete all amendments
                if new_status == Contract.Status.DRAFT:
                    contract.amendments.all().delete()

                # Create amendment for status change (not for drafts, not for reset to draft)
                if old_status != Contract.Status.DRAFT and new_status != Contract.Status.DRAFT:
                    ContractAmendment.objects.create(
                        tenant=user.tenant,
                        contract=contract,
                        effective_date=date.today(),
                        type=ContractAmendment.AmendmentType.TERMS_CHANGED,
                        description=f"Status changed from {old_status} to {new_status}",
                        changes={
                            "action": "status_change",
                            "old_status": old_status,
                            "new_status": new_status,
                        },
                    )

            return ContractResult(contract=contract, success=True)
        except Exception as e:
            return ContractResult(error=str(e))

    @strawberry.mutation
    def change_contract_customer(
        self,
        info: Info[Context, None],
        contract_id: strawberry.ID,
        customer_id: strawberry.ID,
    ) -> ContractResult:
        """Change the customer of a draft contract."""
        user, err = check_perm(info, "contracts", "write")
        if err:
            return ContractResult(error=err)
        if not user.tenant:
            return ContractResult(error="No tenant assigned")

        contract = Contract.objects.filter(
            tenant=user.tenant, id=contract_id
        ).first()
        if not contract:
            return ContractResult(error="Contract not found")

        if contract.status != Contract.Status.DRAFT:
            return ContractResult(error="Can only change customer on draft contracts")

        customer = Customer.objects.filter(
            tenant=user.tenant, id=customer_id
        ).first()
        if not customer:
            return ContractResult(error="Customer not found")

        contract.customer = customer
        contract.group = None
        contract.save()

        return ContractResult(contract=contract, success=True)

    @strawberry.mutation
    def add_contract_item_price(
        self,
        info: Info[Context, None],
        item_id: strawberry.ID,
        input: ContractItemPriceInput,
    ) -> ContractItemPriceResult:
        """Add a price period to a contract item."""
        user, err = check_perm(info, "contracts", "write")
        if err:
            return ContractItemPriceResult(error=err)
        if not user.tenant:
            return ContractItemPriceResult(error="No tenant assigned")

        item = ContractItem.objects.filter(
            tenant=user.tenant, id=item_id
        ).first()
        if not item:
            return ContractItemPriceResult(error="Item not found")

        # Check if price is locked
        is_price_locked = item.price_locked and (
            item.price_locked_until is None or item.price_locked_until >= date.today()
        )
        if is_price_locked:
            return ContractItemPriceResult(error="Price is locked and cannot be changed")

        # Check for overlapping periods
        overlap_error = _check_price_period_overlap(
            item, input.valid_from, input.valid_to
        )
        if overlap_error:
            return ContractItemPriceResult(error=overlap_error)

        try:
            price_period_record = ContractItemPrice.objects.create(
                tenant=user.tenant,
                item=item,
                valid_from=input.valid_from,
                valid_to=input.valid_to,
                unit_price=input.unit_price,
                price_period=input.price_period,
                source=input.source,
            )
            return ContractItemPriceResult(
                price_period=ContractItemPriceType(
                    id=price_period_record.id,
                    valid_from=price_period_record.valid_from,
                    valid_to=price_period_record.valid_to,
                    unit_price=price_period_record.unit_price,
                    price_period=price_period_record.price_period,
                    source=price_period_record.source,
                ),
                success=True,
            )
        except Exception as e:
            return ContractItemPriceResult(error=str(e))

    @strawberry.mutation
    def update_contract_item_price(
        self,
        info: Info[Context, None],
        input: UpdateContractItemPriceInput,
    ) -> ContractItemPriceResult:
        """Update a price period."""
        user, err = check_perm(info, "contracts", "write")
        if err:
            return ContractItemPriceResult(error=err)
        if not user.tenant:
            return ContractItemPriceResult(error="No tenant assigned")

        price_period = ContractItemPrice.objects.filter(
            tenant=user.tenant, id=input.id
        ).select_related("item").first()
        if not price_period:
            return ContractItemPriceResult(error="Price period not found")

        # Check if price is locked
        item = price_period.item
        is_price_locked = item.price_locked and (
            item.price_locked_until is None or item.price_locked_until >= date.today()
        )
        if is_price_locked:
            return ContractItemPriceResult(error="Price is locked and cannot be changed")

        # Determine the new date range (use existing values if not provided)
        new_valid_from = input.valid_from if input.valid_from is not None else price_period.valid_from
        new_valid_to = input.valid_to if input.valid_to is not None else price_period.valid_to

        # Check for overlapping periods (excluding this one)
        overlap_error = _check_price_period_overlap(
            item, new_valid_from, new_valid_to, exclude_id=price_period.id
        )
        if overlap_error:
            return ContractItemPriceResult(error=overlap_error)

        try:
            if input.valid_from is not None:
                price_period.valid_from = input.valid_from
            if input.valid_to is not None:
                price_period.valid_to = input.valid_to
            if input.unit_price is not None:
                price_period.unit_price = input.unit_price
            if input.price_period is not None:
                price_period.price_period = input.price_period
            if input.source is not None:
                price_period.source = input.source
            price_period.save()

            return ContractItemPriceResult(
                price_period=ContractItemPriceType(
                    id=price_period.id,
                    valid_from=price_period.valid_from,
                    valid_to=price_period.valid_to,
                    unit_price=price_period.unit_price,
                    price_period=price_period.price_period,
                    source=price_period.source,
                ),
                success=True,
            )
        except Exception as e:
            return ContractItemPriceResult(error=str(e))

    @strawberry.mutation
    def remove_contract_item_price(
        self, info: Info[Context, None], price_id: strawberry.ID
    ) -> DeleteResult:
        """Remove a price period."""
        user, err = check_perm(info, "contracts", "write")
        if err:
            return DeleteResult(error=err)
        if not user.tenant:
            return DeleteResult(error="No tenant assigned")

        price_period = ContractItemPrice.objects.filter(
            tenant=user.tenant, id=price_id
        ).select_related("item").first()
        if not price_period:
            return DeleteResult(error="Price period not found")

        # Check if price is locked
        item = price_period.item
        is_price_locked = item.price_locked and (
            item.price_locked_until is None or item.price_locked_until >= date.today()
        )
        if is_price_locked:
            return DeleteResult(error="Price is locked and cannot be changed")

        try:
            price_period.delete()
            return DeleteResult(success=True)
        except Exception as e:
            return DeleteResult(error=str(e))

    # =========================================================================
    # Contract Attachment Mutations
    # =========================================================================

    @strawberry.mutation
    def upload_contract_attachment(
        self,
        info: Info[Context, None],
        input: UploadAttachmentInput,
    ) -> AttachmentResult:
        """Upload a file attachment to a contract."""
        from django.conf import settings
        from django.core.files.base import ContentFile

        user, err = check_perm(info, "contracts", "write")
        if err:
            return AttachmentResult(error=err)
        if not user.tenant:
            return AttachmentResult(error="No tenant assigned")

        # Verify contract belongs to tenant
        contract = Contract.objects.filter(
            tenant=user.tenant, id=input.contract_id
        ).first()
        if not contract:
            return AttachmentResult(error="Contract not found")

        # Validate filename extension
        ext = os.path.splitext(input.filename)[1].lower()
        if ext not in settings.ALLOWED_ATTACHMENT_EXTENSIONS:
            return AttachmentResult(error=f"File type {ext} not allowed")

        # Decode and validate file size
        try:
            file_bytes = base64.b64decode(input.file_content)
        except Exception:
            return AttachmentResult(error="Invalid base64 file content")

        file_size = len(file_bytes)
        if file_size > settings.MAX_UPLOAD_SIZE:
            max_mb = settings.MAX_UPLOAD_SIZE / (1024 * 1024)
            return AttachmentResult(error=f"File too large. Maximum size is {max_mb:.0f}MB")

        try:
            # Create attachment
            attachment = ContractAttachment.objects.create(
                tenant=user.tenant,
                contract=contract,
                original_filename=input.filename,
                file_size=file_size,
                content_type=input.content_type,
                description=input.description,
                uploaded_by=user,
            )

            # Save file
            content_file = ContentFile(file_bytes, name=input.filename)
            attachment.file.save(input.filename, content_file, save=True)

            return AttachmentResult(
                attachment=ContractAttachmentType(
                    id=attachment.id,
                    original_filename=attachment.original_filename,
                    file_size=attachment.file_size,
                    content_type=attachment.content_type,
                    description=attachment.description,
                    uploaded_at=attachment.created_at,
                    uploaded_by_name=user.email,
                    download_url=f"/api/attachments/{attachment.id}/download/",
                ),
                success=True,
            )
        except Exception as e:
            return AttachmentResult(error=str(e))

    @strawberry.mutation
    def delete_contract_attachment(
        self,
        info: Info[Context, None],
        attachment_id: strawberry.ID,
    ) -> DeleteResult:
        """Delete a file attachment."""
        user, err = check_perm(info, "contracts", "write")
        if err:
            return DeleteResult(error=err)
        if not user.tenant:
            return DeleteResult(error="No tenant assigned")

        attachment = ContractAttachment.objects.filter(
            tenant=user.tenant, id=attachment_id
        ).first()
        if not attachment:
            return DeleteResult(error="Attachment not found")

        try:
            attachment.delete()  # Will also delete the file from storage
            return DeleteResult(success=True)
        except Exception as e:
            return DeleteResult(error=str(e))

    # =========================================================================
    # Contract Link Mutations
    # =========================================================================

    @strawberry.mutation
    def add_contract_link(
        self,
        info: Info[Context, None],
        input: AddContractLinkInput,
    ) -> ContractLinkResult:
        """Add a link to a contract."""
        user, err = check_perm(info, "contracts", "write")
        if err:
            return ContractLinkResult(error=err)
        if not user.tenant:
            return ContractLinkResult(error="No tenant assigned")

        # Verify contract belongs to tenant
        contract = Contract.objects.filter(
            tenant=user.tenant, id=input.contract_id
        ).first()
        if not contract:
            return ContractLinkResult(error="Contract not found")

        try:
            link = ContractLink.objects.create(
                tenant=user.tenant,
                contract=contract,
                name=input.name,
                url=input.url,
                created_by=user,
            )

            return ContractLinkResult(
                link=ContractLinkType(
                    id=link.id,
                    name=link.name,
                    url=link.url,
                    created_at=link.created_at,
                    created_by_name=user.email,
                ),
                success=True,
            )
        except Exception as e:
            return ContractLinkResult(error=str(e))

    @strawberry.mutation
    def delete_contract_link(
        self,
        info: Info[Context, None],
        link_id: strawberry.ID,
    ) -> DeleteResult:
        """Delete a contract link."""
        user, err = check_perm(info, "contracts", "write")
        if err:
            return DeleteResult(error=err)
        if not user.tenant:
            return DeleteResult(error="No tenant assigned")

        link = ContractLink.objects.filter(
            tenant=user.tenant, id=link_id
        ).first()
        if not link:
            return DeleteResult(error="Link not found")

        try:
            link.delete()
            return DeleteResult(success=True)
        except Exception as e:
            return DeleteResult(error=str(e))

    @strawberry.mutation
    def map_time_tracking_project(
        self,
        info: Info[Context, None],
        contract_id: strawberry.ID,
        external_project_id: str,
        external_project_name: str,
        external_customer_name: str = "",
        contract_item_id: strawberry.ID | None = None,
    ) -> TimeTrackingMappingResult:
        """Map an external time tracking project to a contract."""
        user, err = check_perm(info, "contracts", "write")
        if err:
            return TimeTrackingMappingResult(success=False, error=err)
        if not user.tenant:
            return TimeTrackingMappingResult(success=False, error="No tenant assigned")

        contract = Contract.objects.filter(
            tenant=user.tenant, id=contract_id
        ).first()
        if not contract:
            return TimeTrackingMappingResult(success=False, error="Contract not found")

        # Check if already mapped
        if TimeTrackingProjectMapping.objects.filter(
            tenant=user.tenant, external_project_id=external_project_id
        ).exists():
            return TimeTrackingMappingResult(
                success=False, error="Project is already mapped"
            )

        # Validate contract_item belongs to this contract
        contract_item = None
        if contract_item_id:
            contract_item = ContractItem.objects.filter(
                contract=contract, id=contract_item_id
            ).first()
            if not contract_item:
                return TimeTrackingMappingResult(
                    success=False, error="Item not found in this contract"
                )

        mapping = TimeTrackingProjectMapping.objects.create(
            tenant=user.tenant,
            contract=contract,
            contract_item=contract_item,
            external_project_id=external_project_id,
            external_project_name=external_project_name,
            external_customer_name=external_customer_name,
        )

        # Trigger async sync so cached data is available quickly
        from apps.contracts.tasks import sync_time_tracking_mapping_task
        sync_time_tracking_mapping_task.delay(mapping.id)

        return TimeTrackingMappingResult(
            success=True,
            mapping=TimeTrackingMappingType(
                id=mapping.id,
                external_project_id=mapping.external_project_id,
                external_project_name=mapping.external_project_name,
                external_customer_name=mapping.external_customer_name,
                contract_item_id=mapping.contract_item_id,
                contract_item_name=(
                    contract_item.product.name if contract_item and contract_item.product
                    else contract_item.description[:50] if contract_item
                    else None
                ),
                cached_total_hours=mapping.cached_total_hours,
            ),
        )

    @strawberry.mutation
    def unmap_time_tracking_project(
        self,
        info: Info[Context, None],
        mapping_id: strawberry.ID,
    ) -> DeleteResult:
        """Remove a time tracking project mapping."""
        user, err = check_perm(info, "contracts", "write")
        if err:
            return DeleteResult(error=err)
        if not user.tenant:
            return DeleteResult(error="No tenant assigned")

        mapping = TimeTrackingProjectMapping.objects.filter(
            tenant=user.tenant, id=mapping_id
        ).first()
        if not mapping:
            return DeleteResult(error="Mapping not found")

        mapping.delete()
        return DeleteResult(success=True)

    @strawberry.mutation
    def create_contract_group(
        self,
        info: Info[Context, None],
        customer_id: strawberry.ID,
        name: str,
    ) -> ContractGroupResult:
        """Create a new contract group for a customer."""
        user, err = check_perm(info, "contracts", "write")
        if err:
            return ContractGroupResult(error=err)
        if not user.tenant:
            return ContractGroupResult(error="No tenant assigned")

        # Verify customer belongs to tenant
        customer = Customer.objects.filter(tenant=user.tenant, id=customer_id).first()
        if not customer:
            return ContractGroupResult(error="Customer not found")

        # Check for duplicate name
        if ContractGroup.objects.filter(customer=customer, name=name).exists():
            return ContractGroupResult(error="A group with this name already exists for this customer")

        try:
            group = ContractGroup.objects.create(
                tenant=user.tenant,
                customer=customer,
                name=name,
            )
            return ContractGroupResult(
                success=True,
                group=ContractGroupType(
                    id=group.id,
                    name=group.name,
                    contract_count=0,
                ),
            )
        except Exception as e:
            return ContractGroupResult(error=str(e))

    @strawberry.mutation
    def update_contract_group(
        self,
        info: Info[Context, None],
        group_id: strawberry.ID,
        name: str,
    ) -> ContractGroupResult:
        """Rename a contract group."""
        user, err = check_perm(info, "contracts", "write")
        if err:
            return ContractGroupResult(error=err)
        if not user.tenant:
            return ContractGroupResult(error="No tenant assigned")

        group = ContractGroup.objects.filter(tenant=user.tenant, id=group_id).first()
        if not group:
            return ContractGroupResult(error="Group not found")

        # Check for duplicate name (excluding current group)
        if ContractGroup.objects.filter(customer=group.customer, name=name).exclude(id=group.id).exists():
            return ContractGroupResult(error="A group with this name already exists for this customer")

        try:
            group.name = name
            group.save()
            return ContractGroupResult(
                success=True,
                group=ContractGroupType(
                    id=group.id,
                    name=group.name,
                    contract_count=Contract.objects.filter(group=group).count(),
                ),
            )
        except Exception as e:
            return ContractGroupResult(error=str(e))

    @strawberry.mutation
    def delete_contract_group(
        self,
        info: Info[Context, None],
        group_id: strawberry.ID,
    ) -> DeleteResult:
        """Delete a contract group. Contracts in the group will be ungrouped."""
        user, err = check_perm(info, "contracts", "write")
        if err:
            return DeleteResult(error=err)
        if not user.tenant:
            return DeleteResult(error="No tenant assigned")

        group = ContractGroup.objects.filter(tenant=user.tenant, id=group_id).first()
        if not group:
            return DeleteResult(error="Group not found")

        # Contracts will have group set to null via on_delete=SET_NULL
        group.delete()
        return DeleteResult(success=True)

    @strawberry.mutation
    def assign_contract_to_group(
        self,
        info: Info[Context, None],
        contract_id: strawberry.ID,
        group_id: strawberry.ID | None,
    ) -> ContractResult:
        """Assign a contract to a group, or unassign if group_id is null."""
        user, err = check_perm(info, "contracts", "write")
        if err:
            return ContractResult(error=err)
        if not user.tenant:
            return ContractResult(error="No tenant assigned")

        contract = Contract.objects.filter(tenant=user.tenant, id=contract_id).first()
        if not contract:
            return ContractResult(error="Contract not found")

        if group_id is None:
            # Unassign from group
            contract.group = None
            contract.save()
            return ContractResult(success=True, contract=contract)

        group = ContractGroup.objects.filter(tenant=user.tenant, id=group_id).first()
        if not group:
            return ContractResult(error="Group not found")

        # Verify group belongs to same customer as contract
        if group.customer_id != contract.customer_id:
            return ContractResult(error="Group must belong to the same customer as the contract")

        contract.group = group
        contract.save()
        return ContractResult(success=True, contract=contract)


# =============================================================================
# Contract Import Types and Mutations
# =============================================================================


@strawberry.type
class ImportMatchAlternative:
    """An alternative customer match option."""
    customer_id: int
    customer_name: str
    customer_city: str | None
    confidence: float


@strawberry.type
class ImportMatchResult:
    """Result of customer matching."""
    status: str  # "matched", "review", "not_found"
    customer_id: int | None
    customer_name: str | None
    customer_city: str | None
    confidence: float
    alternatives: List[ImportMatchAlternative]
    original_name: str
    netsuite_customer_number: str


@strawberry.type
class ImportLineItem:
    """A line item in an import proposal."""
    item_name: str
    monthly_rate: float
    product_id: int | None
    product_name: str | None


@strawberry.type
class ImportProposalType:
    """A proposal for importing a contract."""
    id: str
    customer_number: str
    customer_name: str
    sales_order_number: str
    contract_number: str
    start_date: date | None
    end_date: date | None
    invoicing_instructions: str
    match_result: ImportMatchResult | None
    selected_customer_id: int | None
    items: List[ImportLineItem]
    total_monthly_rate: float
    approved: bool
    rejected: bool
    error: str | None
    needs_review: bool
    existing_contract_id: int | None  # If set, contract already exists


@strawberry.type
class ImportSummary:
    """Summary of import proposals."""
    total_proposals: int
    auto_matched: int
    needs_review: int
    not_found: int
    total_items: int
    already_imported: int  # Contracts that already exist


@strawberry.type
class ImportSessionType:
    """An import session with proposals."""
    id: str
    proposals: List[ImportProposalType]
    summary: ImportSummary
    parser_errors: List[str]


@strawberry.type
class ImportUploadResult:
    """Result of uploading an Excel file for import."""
    session: ImportSessionType | None = None
    success: bool = False
    error: str | None = None


@strawberry.type
class ImportApplyResult:
    """Result of applying import proposals."""
    created_contracts: List[ContractType]
    success: bool = False
    error: str | None = None
    errors_by_proposal: List[str] | None = None


# Store import sessions in memory (in production, use Redis or database)
_import_sessions: dict[str, dict] = {}


def _get_customer_city(customer) -> str | None:
    """Extract city from customer address."""
    if not customer or not customer.address:
        return None
    address = customer.address
    if isinstance(address, dict):
        return address.get("city") or address.get("City")
    return None


def _convert_proposal_to_type(proposal) -> ImportProposalType:
    """Convert an ImportProposal to ImportProposalType."""
    match_result = None
    if proposal.match_result:
        mr = proposal.match_result
        alternatives = []
        for alt in mr.alternatives:
            alternatives.append(ImportMatchAlternative(
                customer_id=alt.customer.id,
                customer_name=alt.customer.name,
                customer_city=_get_customer_city(alt.customer),
                confidence=alt.confidence,
            ))
        match_result = ImportMatchResult(
            status=mr.status.value,
            customer_id=mr.customer.id if mr.customer else None,
            customer_name=mr.customer.name if mr.customer else None,
            customer_city=_get_customer_city(mr.customer),
            confidence=mr.confidence,
            alternatives=alternatives,
            original_name=mr.original_name,
            netsuite_customer_number=mr.netsuite_customer_number,
        )

    items = []
    for item in proposal.items:
        items.append(ImportLineItem(
            item_name=item.item_name,
            monthly_rate=float(item.monthly_rate),
            product_id=item.product.id if item.product else None,
            product_name=item.product.name if item.product else None,
        ))

    return ImportProposalType(
        id=proposal.id,
        customer_number=proposal.customer_number,
        customer_name=proposal.customer_name,
        sales_order_number=proposal.sales_order_number,
        contract_number=proposal.contract_number,
        start_date=proposal.start_date,
        end_date=proposal.end_date,
        invoicing_instructions=proposal.invoicing_instructions,
        match_result=match_result,
        selected_customer_id=proposal.selected_customer.id if proposal.selected_customer else None,
        items=items,
        total_monthly_rate=float(proposal.total_monthly_rate),
        approved=proposal.approved,
        rejected=proposal.rejected,
        error=proposal.error,
        needs_review=proposal.needs_review,
        existing_contract_id=proposal.existing_contract_id,
    )


@strawberry.input
class ReviewProposalInput:
    """Input for reviewing a proposal."""
    proposal_id: str
    approved: bool
    selected_customer_id: strawberry.ID | None = None


@strawberry.type
class ContractImportQuery:
    @strawberry.field
    def import_session(
        self,
        info: Info[Context, None],
        session_id: str,
    ) -> ImportSessionType | None:
        """Get an import session by ID."""
        user = require_perm(info, "contracts", "read")
        if not user.tenant:
            return None

        session_key = f"{user.tenant.id}:{session_id}"
        session_data = _import_sessions.get(session_key)
        if not session_data:
            return None

        service = session_data["service"]
        parser_errors = session_data.get("parser_errors", [])

        proposals = [_convert_proposal_to_type(p) for p in service.proposals]
        summary_data = service.get_summary()

        # Count already imported
        already_imported = sum(1 for p in service.proposals if p.existing_contract_id is not None)

        return ImportSessionType(
            id=session_id,
            proposals=proposals,
            summary=ImportSummary(
                total_proposals=summary_data["total_proposals"],
                auto_matched=summary_data["auto_matched"],
                needs_review=summary_data["needs_review"],
                not_found=summary_data["not_found"],
                total_items=summary_data["total_items"],
                already_imported=already_imported,
            ),
            parser_errors=parser_errors,
        )


@strawberry.type
class ContractImportMutation:
    @strawberry.mutation
    def upload_contract_import(
        self,
        info: Info[Context, None],
        file_content: str,
        filename: str,
        auto_approve_threshold: float = 0.9,
    ) -> ImportUploadResult:
        """
        Upload an Excel file and generate import proposals.

        Args:
            file_content: Base64-encoded Excel file content
            filename: Original filename (must end with .xlsx)
            auto_approve_threshold: Confidence threshold for auto-approval (default: 0.9)
        """
        import uuid

        user, err = check_perm(info, "contracts", "write")
        if err:
            return ImportUploadResult(error=err)
        if not user.tenant:
            return ImportUploadResult(error="No tenant assigned")

        if not filename.endswith(".xlsx"):
            return ImportUploadResult(error="File must be an Excel file (.xlsx)")

        try:
            # Decode base64 content
            try:
                file_bytes = base64.b64decode(file_content)
            except Exception:
                return ImportUploadResult(error="Invalid base64 file content")

            # Save to temp location
            with tempfile.NamedTemporaryFile(
                suffix=".xlsx", delete=False
            ) as tmp_file:
                tmp_file.write(file_bytes)
                tmp_path = tmp_file.name

            try:
                # Parse Excel file
                parser = ExcelParser()
                rows = parser.parse(tmp_path)

                if not rows and parser.errors:
                    return ImportUploadResult(
                        error=f"Failed to parse file: {'; '.join(parser.errors)}"
                    )

                # Generate proposals
                service = ImportService(user.tenant)
                service.AUTO_APPROVE_THRESHOLD = auto_approve_threshold
                service.generate_proposals(rows)

                # Store session
                session_id = str(uuid.uuid4())
                session_key = f"{user.tenant.id}:{session_id}"
                _import_sessions[session_key] = {
                    "service": service,
                    "parser_errors": parser.errors,
                }

                # Build response
                proposals = [_convert_proposal_to_type(p) for p in service.proposals]
                summary_data = service.get_summary()

                # Count already imported
                already_imported = sum(1 for p in service.proposals if p.existing_contract_id is not None)

                return ImportUploadResult(
                    session=ImportSessionType(
                        id=session_id,
                        proposals=proposals,
                        summary=ImportSummary(
                            total_proposals=summary_data["total_proposals"],
                            auto_matched=summary_data["auto_matched"],
                            needs_review=summary_data["needs_review"],
                            not_found=summary_data["not_found"],
                            total_items=summary_data["total_items"],
                            already_imported=already_imported,
                        ),
                        parser_errors=parser.errors,
                    ),
                    success=True,
                )
            finally:
                # Clean up temp file
                os.unlink(tmp_path)

        except Exception as e:
            return ImportUploadResult(error=str(e))

    @strawberry.mutation
    def review_import_proposals(
        self,
        info: Info[Context, None],
        session_id: str,
        reviews: List[ReviewProposalInput],
    ) -> ImportUploadResult:
        """Review and approve/reject import proposals."""
        user, err = check_perm(info, "contracts", "write")
        if err:
            return ImportUploadResult(error=err)
        if not user.tenant:
            return ImportUploadResult(error="No tenant assigned")

        session_key = f"{user.tenant.id}:{session_id}"
        session_data = _import_sessions.get(session_key)
        if not session_data:
            return ImportUploadResult(error="Session not found")

        service = session_data["service"]

        # Apply reviews
        proposals_by_id = {p.id: p for p in service.proposals}
        for review in reviews:
            proposal = proposals_by_id.get(review.proposal_id)
            if not proposal:
                continue

            proposal.approved = review.approved
            proposal.rejected = not review.approved

            if review.selected_customer_id:
                customer = Customer.objects.filter(
                    tenant=user.tenant, id=review.selected_customer_id
                ).first()
                if customer:
                    proposal.selected_customer = customer

        # Build response
        proposals = [_convert_proposal_to_type(p) for p in service.proposals]
        summary_data = service.get_summary()
        already_imported = sum(1 for p in service.proposals if p.existing_contract_id is not None)

        return ImportUploadResult(
            session=ImportSessionType(
                id=session_id,
                proposals=proposals,
                summary=ImportSummary(
                    total_proposals=summary_data["total_proposals"],
                    auto_matched=summary_data["auto_matched"],
                    needs_review=summary_data["needs_review"],
                    not_found=summary_data["not_found"],
                    total_items=summary_data["total_items"],
                    already_imported=already_imported,
                ),
                parser_errors=session_data.get("parser_errors", []),
            ),
            success=True,
        )

    @strawberry.mutation
    def apply_import_proposals(
        self,
        info: Info[Context, None],
        session_id: str,
        auto_create_products: bool = True,
    ) -> ImportApplyResult:
        """Apply approved import proposals and create contracts."""
        user, err = check_perm(info, "contracts", "write")
        if err:
            return ImportApplyResult(error=err)
        if not user.tenant:
            return ImportApplyResult(error="No tenant assigned")

        session_key = f"{user.tenant.id}:{session_id}"
        session_data = _import_sessions.get(session_key)
        if not session_data:
            return ImportApplyResult(error="Session not found")

        service = session_data["service"]

        try:
            created = service.apply_proposals(
                auto_create_products=auto_create_products
            )

            # Collect errors
            errors = [
                f"{p.sales_order_number}: {p.error}"
                for p in service.proposals
                if p.error
            ]

            # Clean up session after successful apply
            del _import_sessions[session_key]

            return ImportApplyResult(
                created_contracts=created,
                success=True,
                errors_by_proposal=errors if errors else None,
            )
        except Exception as e:
            return ImportApplyResult(error=str(e))

    @strawberry.mutation
    def cancel_import_session(
        self,
        info: Info[Context, None],
        session_id: str,
    ) -> DeleteResult:
        """Cancel an import session and clean up."""
        user, err = check_perm(info, "contracts", "write")
        if err:
            return DeleteResult(error=err)
        if not user.tenant:
            return DeleteResult(error="No tenant assigned")

        session_key = f"{user.tenant.id}:{session_id}"
        if session_key in _import_sessions:
            del _import_sessions[session_key]
            return DeleteResult(success=True)
        return DeleteResult(error="Session not found")

    @strawberry.mutation
    def import_pdf_analysis(
        self,
        info: Info[Context, None],
        input: ImportPdfAnalysisInput,
    ) -> PdfImportResultType:
        """Import selected items and metadata from PDF analysis into a contract."""
        user, err = check_perm(info, "contracts", "write")
        if err:
            return PdfImportResultType(success=False, error=err)
        if not user.tenant:
            return PdfImportResultType(success=False, error="No tenant assigned")

        contract = Contract.objects.filter(
            tenant=user.tenant, id=input.contract_id
        ).first()
        if not contract:
            return PdfImportResultType(success=False, error="Contract not found")

        try:
            with transaction.atomic():
                created_count = 0
                updated_count = 0

                for item_input in input.items:
                    product = None
                    if item_input.product_id:
                        product = Product.objects.filter(
                            tenant=user.tenant, id=item_input.product_id
                        ).first()
                        if not product:
                            return PdfImportResultType(
                                success=False,
                                error=f"Product not found: {item_input.product_id}",
                            )

                    # Update existing item
                    if item_input.existing_item_id:
                        existing_item = ContractItem.objects.filter(
                            tenant=user.tenant,
                            contract=contract,
                            id=item_input.existing_item_id,
                        ).first()
                        if not existing_item:
                            return PdfImportResultType(
                                success=False,
                                error=f"Existing item not found: {item_input.existing_item_id}",
                            )

                        # Capture old values before update
                        old_item_values = {
                            "product_id": str(existing_item.product_id) if existing_item.product_id else None,
                            "description": existing_item.description,
                            "quantity": existing_item.quantity,
                            "unit_price": str(existing_item.unit_price),
                            "price_period": existing_item.price_period,
                            "is_one_off": existing_item.is_one_off,
                        }

                        existing_item.product = product
                        existing_item.description = item_input.description
                        existing_item.quantity = item_input.quantity
                        existing_item.unit_price = item_input.unit_price
                        existing_item.price_period = item_input.price_period
                        existing_item.price_source = ContractItem.PriceSource.CUSTOM
                        existing_item.is_one_off = item_input.is_one_off
                        existing_item.save()

                        new_item_values = {
                            "product_id": str(product.id) if product else None,
                            "description": item_input.description,
                            "quantity": item_input.quantity,
                            "unit_price": str(item_input.unit_price),
                            "price_period": item_input.price_period,
                            "is_one_off": item_input.is_one_off,
                        }

                        if contract.status != Contract.Status.DRAFT and old_item_values != new_item_values:
                            item_name = product.name if product else item_input.description[:50]
                            ContractAmendment.objects.create(
                                tenant=user.tenant,
                                contract=contract,
                                effective_date=date.today(),
                                type=ContractAmendment.AmendmentType.PRICE_CHANGED,
                                description=f"Updated {item_name} (PDF import)",
                                changes={
                                    "item_id": str(existing_item.id),
                                    "product_id": str(product.id) if product else None,
                                    "product_name": product.name if product else None,
                                    "description": item_input.description,
                                    "quantity": item_input.quantity,
                                    "unit_price": str(item_input.unit_price),
                                    "price_period": item_input.price_period,
                                    "is_one_off": item_input.is_one_off,
                                    "source": "pdf_import",
                                },
                            )

                        updated_count += 1
                    else:
                        # Create new item
                        ContractItem.objects.create(
                            tenant=user.tenant,
                            contract=contract,
                            product=product,
                            description=item_input.description,
                            quantity=item_input.quantity,
                            unit_price=item_input.unit_price,
                            price_period=item_input.price_period,
                            price_source=ContractItem.PriceSource.CUSTOM,
                            is_one_off=item_input.is_one_off,
                        )

                        if contract.status != Contract.Status.DRAFT:
                            item_name = product.name if product else item_input.description[:50]
                            ContractAmendment.objects.create(
                                tenant=user.tenant,
                                contract=contract,
                                effective_date=date.today(),
                                type=ContractAmendment.AmendmentType.PRODUCT_ADDED,
                                description=f"Added {item_name} x{item_input.quantity} (PDF import)",
                                changes={
                                    "product_id": str(product.id) if product else None,
                                    "product_name": product.name if product else None,
                                    "description": item_input.description,
                                    "quantity": item_input.quantity,
                                    "unit_price": str(item_input.unit_price),
                                    "price_period": item_input.price_period,
                                    "is_one_off": item_input.is_one_off,
                                    "source": "pdf_import",
                                },
                            )

                        created_count += 1

                # Update contract metadata
                if input.metadata:
                    if input.metadata.po_number is not UNSET:
                        contract.po_number = input.metadata.po_number
                    if input.metadata.order_confirmation_number is not UNSET:
                        contract.order_confirmation_number = input.metadata.order_confirmation_number
                    if input.metadata.min_duration_months is not UNSET:
                        contract.min_duration_months = input.metadata.min_duration_months
                    contract.save()

                return PdfImportResultType(
                    success=True,
                    created_items_count=created_count,
                    updated_items_count=updated_count,
                )
        except Exception as e:
            return PdfImportResultType(success=False, error=str(e))

    @strawberry.mutation
    def reorder_contract_items(
        self, info: Info[Context, None], input: ReorderContractItemsInput
    ) -> DeleteResult:
        """Reorder contract items by setting sort_order based on position in item_ids list."""
        user, err = check_perm(info, "contracts", "write")
        if err:
            return DeleteResult(error=err)
        if not user.tenant:
            return DeleteResult(error="No tenant assigned")

        contract = Contract.objects.filter(
            tenant=user.tenant, id=input.contract_id
        ).first()
        if not contract:
            return DeleteResult(error="Contract not found")

        try:
            with transaction.atomic():
                items = ContractItem.objects.filter(
                    tenant=user.tenant,
                    contract=contract,
                    is_one_off=input.is_one_off,
                )
                item_map = {str(item.id): item for item in items}

                for position, item_id in enumerate(input.item_ids):
                    item = item_map.get(str(item_id))
                    if not item:
                        return DeleteResult(error=f"Item {item_id} not found in contract")
                    item.sort_order = position
                    item.save(update_fields=["sort_order"])

            return DeleteResult(success=True)
        except Exception as e:
            return DeleteResult(error=str(e))

    @strawberry.mutation
    def bulk_price_increase(
        self, info: Info[Context, None], input: BulkPriceIncreaseInput
    ) -> BulkPriceIncreaseResult:
        """Apply a percentage price increase to all recurring items of a contract."""
        user, err = check_perm(info, "contracts", "write")
        if err:
            return BulkPriceIncreaseResult(error=err)
        if not user.tenant:
            return BulkPriceIncreaseResult(error="No tenant assigned")

        if input.percentage <= 0:
            return BulkPriceIncreaseResult(error="Percentage must be greater than 0")

        if input.mode not in ("direct", "period_specific"):
            return BulkPriceIncreaseResult(error="Mode must be 'direct' or 'period_specific'")

        contract = Contract.objects.filter(
            tenant=user.tenant, id=input.contract_id
        ).first()
        if not contract:
            return BulkPriceIncreaseResult(error="Contract not found")

        items = list(ContractItem.objects.filter(
            contract=contract, is_one_off=False
        ).select_related("product"))

        if not items:
            return BulkPriceIncreaseResult(error="No recurring items found")

        details = []
        items_changed = 0
        items_skipped = 0
        multiplier = 1 + input.percentage / Decimal("100")

        try:
            with transaction.atomic():
                for item in items:
                    # Skip descriptive-only items (discounts, text lines)
                    if not item.product and not item.unit_price:
                        continue

                    item_name = item.product.name if item.product else (item.description or "")[:50]

                    # Check price lock
                    is_price_locked = item.price_locked and (
                        item.price_locked_until is None
                        or item.price_locked_until >= input.effective_date
                    )
                    if is_price_locked:
                        details.append(BulkPriceIncreaseItemResult(
                            item_id=item.id,
                            item_description=item_name,
                            old_price=item.unit_price,
                            new_price=item.unit_price,
                            skipped=True,
                            skip_reason="Price locked",
                        ))
                        items_skipped += 1
                        continue

                    if input.mode == "direct":
                        old_price = item.unit_price
                        new_price = (old_price * multiplier).quantize(Decimal("0.01"))
                        item.unit_price = new_price
                        item.save(update_fields=["unit_price"])
                    else:
                        # period_specific: use effective price at the date
                        effective_price, effective_period = item.get_effective_price_info(
                            input.effective_date
                        )
                        old_price = effective_price
                        new_price = (old_price * multiplier).quantize(Decimal("0.01"))

                        # Close any existing ongoing period that covers effective_date
                        from datetime import timedelta
                        overlapping = item.price_periods.filter(
                            valid_from__lte=input.effective_date,
                        ).filter(
                            Q(valid_to__gte=input.effective_date)
                            | Q(valid_to__isnull=True)
                        )
                        for period in overlapping:
                            day_before = input.effective_date - timedelta(days=1)
                            if period.valid_from <= day_before:
                                period.valid_to = day_before
                                period.save(update_fields=["valid_to"])
                            else:
                                # Period starts on effective_date itself — remove it
                                period.delete()

                        ContractItemPrice.objects.create(
                            tenant=user.tenant,
                            item=item,
                            valid_from=input.effective_date,
                            valid_to=None,
                            unit_price=new_price,
                            price_period=item.price_period,
                            source=ContractItemPrice.PriceSource.FIXED,
                        )

                    details.append(BulkPriceIncreaseItemResult(
                        item_id=item.id,
                        item_description=item_name,
                        old_price=old_price,
                        new_price=new_price,
                    ))
                    items_changed += 1

                # Create amendment for non-draft contracts
                if contract.status != Contract.Status.DRAFT and items_changed > 0:
                    ContractAmendment.objects.create(
                        tenant=user.tenant,
                        contract=contract,
                        effective_date=input.effective_date,
                        type=ContractAmendment.AmendmentType.PRICE_CHANGED,
                        description=(
                            f"Bulk price increase: {input.percentage}% "
                            f"effective {input.effective_date.isoformat()} "
                            f"({input.mode}), {items_changed} items"
                        ),
                        changes={
                            "type": "bulk_price_increase",
                            "percentage": str(input.percentage),
                            "effective_date": input.effective_date.isoformat(),
                            "mode": input.mode,
                            "items_changed": [
                                {
                                    "item_id": d.item_id,
                                    "description": d.item_description,
                                    "old_price": str(d.old_price),
                                    "new_price": str(d.new_price),
                                }
                                for d in details
                                if not d.skipped
                            ],
                            "items_skipped": [
                                {
                                    "item_id": d.item_id,
                                    "description": d.item_description,
                                    "reason": d.skip_reason,
                                }
                                for d in details
                                if d.skipped
                            ],
                        },
                    )

            return BulkPriceIncreaseResult(
                success=True,
                items_changed=items_changed,
                items_skipped=items_skipped,
                details=details,
            )
        except Exception as e:
            return BulkPriceIncreaseResult(error=str(e))

    @strawberry.mutation
    def mark_item_delivered(
        self,
        info: Info[Context, None],
        item_id: strawberry.ID,
        delivered_at: date,
    ) -> DeliverItemResult:
        """Mark a contract item as delivered."""
        user, err = check_perm(info, "contracts", "write")
        if err:
            return DeliverItemResult(error=err)
        if not user.tenant:
            return DeliverItemResult(error="No tenant assigned")

        item = ContractItem.objects.filter(
            tenant=user.tenant, id=item_id
        ).select_related("product").first()
        if not item:
            return DeliverItemResult(error="Item not found")

        if item.delivery_status != "pending":
            return DeliverItemResult(error="Item is not pending delivery")

        item.delivery_status = "delivered"
        item.delivered_at = delivered_at
        item.estimated_delivery_date = None
        item.save(update_fields=["delivery_status", "delivered_at", "estimated_delivery_date"])

        # Find dependent items that need billing_start_date
        dependents = ContractItem.objects.filter(
            depends_on=item
        ).select_related("product")
        dependent_infos = [
            DependentItemInfo(
                id=dep.id,
                name=dep.product.name if dep.product else dep.description[:50],
                has_billing_start_date=dep.billing_start_date is not None,
            )
            for dep in dependents
        ]

        return DeliverItemResult(success=True, dependent_items=dependent_infos)

    @strawberry.mutation
    def revert_item_delivery(
        self,
        info: Info[Context, None],
        item_id: strawberry.ID,
    ) -> DeliverItemResult:
        """Revert a delivered item back to pending."""
        user, err = check_perm(info, "contracts", "write")
        if err:
            return DeliverItemResult(error=err)
        if not user.tenant:
            return DeliverItemResult(error="No tenant assigned")

        item = ContractItem.objects.filter(
            tenant=user.tenant, id=item_id
        ).first()
        if not item:
            return DeliverItemResult(error="Item not found")

        if item.delivery_status != "delivered":
            return DeliverItemResult(error="Item is not delivered")

        item.delivery_status = "pending"
        item.delivered_at = None
        item.save(update_fields=["delivery_status", "delivered_at"])

        return DeliverItemResult(success=True)

    @strawberry.mutation
    def set_deliverable_eta(
        self,
        info: Info[Context, None],
        item_id: strawberry.ID,
        estimated_delivery_date: date | None = None,
    ) -> DeleteResult:
        """Set or clear the estimated delivery date for a deliverable item."""
        user, err = check_perm(info, "contracts", "write")
        if err:
            return DeleteResult(success=False, error=err)
        if not user.tenant:
            return DeleteResult(success=False, error="No tenant assigned")

        item = ContractItem.objects.filter(
            tenant=user.tenant, id=item_id
        ).first()
        if not item:
            return DeleteResult(success=False, error="Item not found")

        if not item.delivery_status:
            return DeleteResult(success=False, error="Item does not have delivery tracking enabled")

        if item.delivery_status != "pending":
            return DeleteResult(success=False, error="Item is not pending delivery")

        item.estimated_delivery_date = estimated_delivery_date
        item.save(update_fields=["estimated_delivery_date"])

        return DeleteResult(success=True)

    # =========================================================================
    # Contract Comment Mutations
    # =========================================================================

    @strawberry.mutation
    def add_contract_comment(
        self,
        info: Info[Context, None],
        contract_id: strawberry.ID,
        text: str,
    ) -> ContractCommentResult:
        """Add a comment to a contract."""
        user, err = check_perm(info, "contracts", "write")
        if err:
            return ContractCommentResult(error=err)
        if not user.tenant:
            return ContractCommentResult(error="No tenant assigned")
        if not text.strip():
            return ContractCommentResult(error="Comment text cannot be empty")

        contract = Contract.objects.filter(
            tenant=user.tenant, id=contract_id
        ).first()
        if not contract:
            return ContractCommentResult(error="Contract not found")

        comment = ContractComment.objects.create(
            tenant=user.tenant,
            contract=contract,
            text=text.strip(),
            author=user,
        )
        return ContractCommentResult(
            comment=_build_contract_comment(comment, user),
            success=True,
        )

    @strawberry.mutation
    def update_contract_comment(
        self,
        info: Info[Context, None],
        comment_id: strawberry.ID,
        text: str,
    ) -> ContractCommentResult:
        """Update own most recent comment within 24h."""
        from django.utils import timezone

        user, err = check_perm(info, "contracts", "write")
        if err:
            return ContractCommentResult(error=err)
        if not user.tenant:
            return ContractCommentResult(error="No tenant assigned")
        if not text.strip():
            return ContractCommentResult(error="Comment text cannot be empty")

        comment = ContractComment.objects.filter(
            tenant=user.tenant, id=comment_id
        ).select_related("author").first()
        if not comment:
            return ContractCommentResult(error="Comment not found")
        if comment.author_id != user.id:
            return ContractCommentResult(error="You can only edit your own comments")

        # Must be the most recent comment by this author on this contract
        newer_exists = ContractComment.objects.filter(
            contract=comment.contract,
            author=user,
            created_at__gt=comment.created_at,
        ).exists()
        if newer_exists:
            return ContractCommentResult(error="You can only edit your most recent comment")

        if (timezone.now() - comment.created_at).total_seconds() >= 86400:
            return ContractCommentResult(error="Comments can only be edited within 24 hours")

        comment.text = text.strip()
        comment.save(update_fields=["text", "updated_at"])

        return ContractCommentResult(
            comment=_build_contract_comment(comment, user),
            success=True,
        )

    @strawberry.mutation
    def delete_contract_comment(
        self,
        info: Info[Context, None],
        comment_id: strawberry.ID,
    ) -> DeleteResult:
        """Delete own comment."""
        user, err = check_perm(info, "contracts", "write")
        if err:
            return DeleteResult(error=err)
        if not user.tenant:
            return DeleteResult(error="No tenant assigned")

        comment = ContractComment.objects.filter(
            tenant=user.tenant, id=comment_id
        ).first()
        if not comment:
            return DeleteResult(error="Comment not found")
        if comment.author_id != user.id:
            return DeleteResult(error="You can only delete your own comments")

        comment.delete()
        return DeleteResult(success=True)
