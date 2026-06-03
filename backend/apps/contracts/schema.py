"""GraphQL schema for contracts."""

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, Annotated, List, Optional
import base64
import tempfile
import os

import strawberry
from strawberry import auto, UNSET
import strawberry_django
from strawberry.types import Info
from django.db import transaction
from django.db.models import Count, Sum, F, Q, Subquery, OuterRef

from apps.core.context import Context
from apps.core.permissions import check_perm, get_current_user, require_perm
from apps.core.schema import DeleteResult, OperationResult
from apps.customers.models import Customer
from apps.customers.schema import CustomerType
from apps.products.models import Product
from apps.products.schema import ProductType
from .models import Contract, ContractComment, ContractItem, ContractAmendment, ContractItemPrice, ContractAttachment, ContractLink, ContractGroup, RevenueGoal, NewBusinessGoal, TimeTrackingProjectMapping, AutoLinkRule, Department, DepartmentServiceMapping, UserCostProfile, OrderConfirmation, calculate_arr_value
from .order_confirmation_schema import OrderConfirmationType
from .forecast_cache import (
    dict_to_forecast_result,
    forecast_result_to_dict,
    get_cached_forecast,
    set_cached_forecast,
)
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
    category: str
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
    increase_type: str | None = None


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
    invoice_independent: bool = False
    depends_on: "ContractItemType | None" = None
    dependent_items: List["ContractItemType"] = strawberry.field(default_factory=list)
    # Year-specific pricing
    price_periods: List[ContractItemPriceType] = strawberry.field(default_factory=list)
    # Revenue type classification
    revenue_type: str | None = None
    effective_revenue_type: str | None = None
    # Merge traceability
    source_hubspot_deal_id: str | None = None
    # Item-level deal won date (overrides contract deal_won_date for bookings reporting)
    deal_won_date: date | None = None
    # Move traceability
    moved_to_item_id: int | None = None
    moved_to_contract_id: int | None = None
    moved_to_contract_name: str | None = None
    moved_from_item_id: int | None = None
    moved_from_contract_id: int | None = None
    moved_from_contract_name: str | None = None


def _moved_fields(item) -> dict:
    """Extract moved_to / moved_from fields for ContractItemType construction."""
    fields: dict = {}
    mt = getattr(item, "moved_to", None)
    if mt:
        fields["moved_to_item_id"] = mt.id
        fields["moved_to_contract_id"] = mt.contract_id
        fields["moved_to_contract_name"] = mt.contract.name if mt.contract else None
    mf = None
    try:
        mf = item.moved_from
    except ContractItem.moved_from.RelatedObjectDoesNotExist:
        pass
    if mf:
        fields["moved_from_item_id"] = mf.id
        fields["moved_from_contract_id"] = mf.contract_id
        fields["moved_from_contract_name"] = mf.contract.name if mf.contract else None
    return fields


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
    offer_number: auto
    notes: auto
    payment_term_days: auto

    @strawberry.field
    def payment_reminders(
        self,
    ) -> list[
        Annotated[
            "PaymentReminderType",
            strawberry.lazy("apps.invoices.dunning_schema"),
        ]
    ]:
        """Payment reminders sent for this contract's invoices."""
        from apps.invoices.dunning_schema import _convert_reminder
        from apps.invoices.models import PaymentReminder

        qs = (
            PaymentReminder.objects.filter(invoice_record__contract=self)
            .select_related("invoice_record")
            .order_by("-created_at")
        )
        return [_convert_reminder(r) for r in qs]

    @strawberry.field(name="orderConfirmations")
    def get_order_confirmations(self) -> list[OrderConfirmationType]:
        """All order confirmations for this contract."""
        return list(OrderConfirmation.objects.filter(contract=self))

    @strawberry.field(name="orderConfirmationSentAt")
    def get_order_confirmation_sent_at(self) -> datetime | None:
        """The sent date of the latest sent order confirmation, if any."""
        ab = OrderConfirmation.objects.filter(
            contract=self, status=OrderConfirmation.Status.SENT
        ).order_by("-sent_at").first()
        return ab.sent_at if ab else None
    invoice_text: auto
    deal_won_date: auto
    customer: CustomerType

    @strawberry.field
    def is_new_business(self) -> bool:
        """True if this contract was imported from HubSpot (new business)."""
        return bool(self.hubspot_deal_id)

    @strawberry.field
    def has_invoices(self) -> bool:
        """Check if contract has any generated or imported invoices."""
        return self.invoice_records.exists() or self.imported_invoices.exists()

    @strawberry.field
    def invoiced_item_ids(self) -> list[int]:
        """Return IDs of contract items that appear in non-voided invoices."""
        from apps.invoices.models import InvoiceRecord

        item_ids: set[int] = set()
        for record in self.invoice_records.exclude(
            status=InvoiceRecord.Status.VOIDED
        ).only("line_items_snapshot"):
            for line in record.line_items_snapshot or []:
                if line.get("item_id"):
                    item_ids.add(line["item_id"])
        return sorted(item_ids)

    @strawberry.field
    def item_invoiced_until(self) -> strawberry.scalars.JSON:
        """Return {item_id: "YYYY-MM-DD"} mapping the latest invoiced period end per item."""
        from apps.invoices.models import InvoiceRecord

        result: dict[int, "date"] = {}
        for record in self.invoice_records.exclude(
            status=InvoiceRecord.Status.VOIDED
        ).only("line_items_snapshot", "period_end"):
            for line in record.line_items_snapshot or []:
                item_id = line.get("item_id")
                if item_id:
                    existing = result.get(item_id)
                    if existing is None or record.period_end > existing:
                        result[item_id] = record.period_end
        return {str(k): v.isoformat() for k, v in result.items()}

    @strawberry.field
    def group(self) -> ContractGroupType | None:
        """Get the contract's group."""
        if not self.group_id:
            return None
        # Use select_related cache if available
        group = self.group
        if not group:
            return None
        # Use annotated count if available (from prefetch), otherwise query
        contract_count = getattr(self, "_group_contract_count", None)
        if contract_count is None:
            contract_count = Contract.objects.filter(group=group).count()
        return ContractGroupType(
            id=group.id,
            name=group.name,
            contract_count=contract_count,
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
        items = ContractItem.objects.filter(contract=self).select_related(
            "product", "contract", "depends_on", "depends_on__product",
            "moved_to", "moved_to__contract",
        ).prefetch_related("price_periods", "dependent_items", "dependent_items__product")
        # Reverse moved_from is a OneToOne — use select_related via prefetch
        # We'll handle it by catching DoesNotExist below
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
                    increase_type=pp.increase_type,
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
                    invoice_independent=item.invoice_independent,
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
                        invoice_independent=item.depends_on.invoice_independent,
                        revenue_type=item.depends_on.revenue_type,
                        effective_revenue_type=item.depends_on.get_effective_revenue_type(),
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
                            revenue_type=dep.revenue_type,
                            effective_revenue_type=dep.get_effective_revenue_type(),
                        )
                        for dep in item.dependent_items.all()
                    ],
                    price_periods=price_periods,
                    revenue_type=item.revenue_type,
                    effective_revenue_type=item.get_effective_revenue_type(),
                    source_hubspot_deal_id=item.source_hubspot_deal_id,
                    deal_won_date=item.deal_won_date,
                    **_moved_fields(item),
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
        """Get all file attachments for this contract.

        Includes uploaded attachments AND generated order-confirmation PDFs
        as virtual attachments (category 'order_confirmation'), so users see
        everything in one list.
        """
        result: list[ContractAttachmentType] = []
        attachments = ContractAttachment.objects.filter(contract=self).select_related("uploaded_by")
        for a in attachments:
            result.append(ContractAttachmentType(
                id=a.id,
                original_filename=a.original_filename,
                file_size=a.file_size,
                content_type=a.content_type,
                description=a.description,
                category=a.category,
                uploaded_at=a.created_at,
                uploaded_by_name=a.uploaded_by.email if a.uploaded_by else None,
                download_url=f"/api/attachments/{a.id}/download/",
            ))
        # Surface order confirmations as virtual attachments (negative id = synthetic)
        ocs = OrderConfirmation.objects.filter(contract=self).select_related("created_by")
        for oc in ocs:
            if not oc.pdf_file:
                continue
            filename = f"{oc.order_confirmation_number or f'AB-{oc.id}'}.pdf"
            try:
                file_size = oc.pdf_file.size
            except Exception:
                file_size = 0
            result.append(ContractAttachmentType(
                id=-int(oc.id),  # negative ID so it can't collide with real attachments
                original_filename=filename,
                file_size=file_size,
                content_type="application/pdf",
                description=f"Auftragsbestätigung {oc.order_confirmation_number} ({oc.status})",
                category="order_confirmation",
                uploaded_at=oc.created_at,
                uploaded_by_name=oc.created_by.email if oc.created_by else None,
                download_url=oc.pdf_file.url,
            ))
        return result

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
    def order_confirmation(self) -> OrderConfirmationType | None:
        """Get the order confirmation for this contract, if one exists."""
        ab = OrderConfirmation.objects.filter(contract=self).first()
        return ab

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

        monthly_total = Decimal("0")
        for item in self.items.all():
            if item.is_one_off:
                continue
            price_periods = list(item.price_periods.all())
            monthly_unit_price = item.get_price_at_cached(today, price_periods, normalize_to_monthly=True)
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

        monthly_total = Decimal("0")
        for item in self.items.all():
            if item.is_one_off:
                continue
            price_periods = list(item.price_periods.all())
            monthly_unit_price = item.get_price_at_cached(today, price_periods, normalize_to_monthly=True)
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
    offer_number: str | None = None
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
    payment_term_days: int | None = None
    group_id: strawberry.ID | None = None


@strawberry.input
class UpdateContractInput:
    id: strawberry.ID
    name: str | None = None
    sales_order_number: str | None = None
    netsuite_url: str | None = None
    po_number: str | None = None
    order_confirmation_number: str | None = None
    offer_number: str | None = None
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
    payment_term_days: int | None = UNSET
    group_id: strawberry.ID | None = UNSET
    deal_won_date: date | None = UNSET


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
    invoice_independent: bool = False
    revenue_type: str | None = None
    deal_won_date: date | None = None


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
    invoice_independent: bool | None = None
    revenue_type: str | None = UNSET
    deal_won_date: date | None = UNSET


@strawberry.input
class ContractItemPriceInput:
    """Input for creating/updating a price period."""
    valid_from: date
    valid_to: date | None = None
    unit_price: Decimal
    price_period: str = "monthly"  # Period the price refers to (monthly, quarterly, annual, etc.)
    source: str = "fixed"
    increase_type: str | None = None


@strawberry.input
class UpdateContractItemPriceInput:
    """Input for updating a price period."""
    id: strawberry.ID
    valid_from: date | None = None
    valid_to: date | None = None
    unit_price: Decimal | None = None
    price_period: str | None = None  # Period the price refers to (monthly, quarterly, annual, etc.)
    source: str | None = None
    increase_type: str | None = None


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


@strawberry.input
class MoveContractItemInput:
    item_id: strawberry.ID
    target_contract_id: strawberry.ID
    effective_date: date


@strawberry.type
class MoveContractItemResult:
    success: bool = False
    error: str | None = None
    source_item: ContractItemType | None = None
    new_item: ContractItemType | None = None


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
class ActivationOptionsInput:
    """Options for the draft → active transition."""
    send_order_confirmation: bool = True
    create_order_confirmation_only: bool = False


@strawberry.input
class BulkPriceIncreaseInput:
    """Input for bulk price increase across all recurring items."""
    contract_id: strawberry.ID
    percentage: Decimal
    effective_date: date
    mode: str = "period_specific"  # "direct" or "period_specific"
    increase_type: str = "inflation"


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
    invoice_independent: bool = False
    contract_id: int
    contract_name: str
    customer_name: str
    customer_id: int
    dependent_items_count: int
    hours_booked: float = 0
    order_value: float = 0
    order_confirmation_number: str | None = None
    ps_ratio: float | None = None


@strawberry.type
class PriceIncreaseImpactType:
    """YoY ARR impact from price increases."""
    year: int
    total_arr_impact: Decimal
    inflation_arr_impact: Decimal
    negotiated_arr_impact: Decimal
    untagged_arr_impact: Decimal
    item_count: int


@strawberry.type
class ContractPriceIncreaseDetailType:
    """Per-contract price increase detail."""
    contract_id: strawberry.ID
    contract_name: str
    customer_name: str
    current_arr: Decimal
    previous_arr: Decimal
    arr_diff: Decimal
    item_count: int


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
    category: str = ""


@strawberry.input
class UpdateAttachmentMetaInput:
    attachment_id: strawberry.ID
    category: str | None = None
    description: str | None = None


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
    description: str = ""
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
    invoice_status: str | None = None  # null | "actionable" | "sent" | "paid" | "overdue"


@strawberry.type
class ContractRevenueRow:
    """Revenue data for a single contract across months."""

    contract_id: int
    contract_name: str
    customer_id: int
    customer_name: str
    months: List[RevenueMonthData]
    total: Decimal
    customer_number: str | None = None


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
    # Exclude contracts with end_date in the past (effectively ended)
    active_contracts = Contract.objects.filter(
        tenant=tenant,
        status=Contract.Status.ACTIVE,
    ).filter(
        Q(end_date__isnull=True) | Q(end_date__gte=today)
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


def calculate_price_increase_impact(tenant, year: int) -> PriceIncreaseImpactType:
    """
    Calculate YoY ARR delta from price increases for a given year.

    Compares price of recurring items at Jan 1 of `year` vs Jan 1 of `year-1`.
    Only considers contracts that existed before Jan 1 of `year` (not new business).
    """
    jan1_current = date(year, 1, 1)
    jan1_previous = date(year - 1, 1, 1)

    # Active contracts that existed before the target year
    contracts = Contract.objects.filter(
        tenant=tenant,
        status__in=[Contract.Status.ACTIVE, Contract.Status.PAUSED],
        start_date__lt=jan1_current,  # Must have started before target year
    ).filter(
        Q(end_date__isnull=True) | Q(end_date__gte=jan1_current)
    ).prefetch_related("items", "items__product", "items__price_periods")

    total_arr_impact = Decimal("0")
    inflation_arr_impact = Decimal("0")
    negotiated_arr_impact = Decimal("0")
    untagged_arr_impact = Decimal("0")
    item_count = 0

    dec31_current = date(year, 12, 31)

    for contract in contracts:
        items = list(contract.items.all())
        for item in items:
            if item.is_one_off:
                continue

            price_periods_list = list(item.price_periods.all())

            # Find all price periods that start in the target year
            # Each one represents a price change — compute delta vs previous price
            year_periods = sorted(
                [pp for pp in price_periods_list if pp.valid_from.year == year],
                key=lambda pp: pp.valid_from,
            )

            if year_periods:
                # For each price period starting this year, compute delta
                for pp in year_periods:
                    # Price just before this period kicked in
                    day_before = pp.valid_from - timedelta(days=1)
                    previous_monthly = item.get_price_at_cached(
                        day_before, price_periods_list, normalize_to_monthly=True
                    )
                    new_monthly = item.get_price_at_cached(
                        pp.valid_from, price_periods_list, normalize_to_monthly=True
                    )

                    if new_monthly <= previous_monthly:
                        continue

                    delta_arr = (new_monthly - previous_monthly) * item.quantity * 12
                    total_arr_impact += delta_arr
                    item_count += 1

                    increase_type = pp.increase_type
                    if increase_type == "inflation":
                        inflation_arr_impact += delta_arr
                    elif increase_type == "negotiated":
                        negotiated_arr_impact += delta_arr
                    else:
                        untagged_arr_impact += delta_arr
            else:
                # No period-specific pricing starting this year —
                # still check Jan 1 vs Jan 1 for base price changes
                current_monthly = item.get_price_at_cached(
                    jan1_current, price_periods_list, normalize_to_monthly=True
                )
                previous_monthly = item.get_price_at_cached(
                    jan1_previous, price_periods_list, normalize_to_monthly=True
                )

                if current_monthly <= previous_monthly:
                    continue

                delta_arr = (current_monthly - previous_monthly) * item.quantity * 12
                total_arr_impact += delta_arr
                item_count += 1
                untagged_arr_impact += delta_arr

    return PriceIncreaseImpactType(
        year=year,
        total_arr_impact=total_arr_impact,
        inflation_arr_impact=inflation_arr_impact,
        negotiated_arr_impact=negotiated_arr_impact,
        untagged_arr_impact=untagged_arr_impact,
        item_count=item_count,
    )


def calculate_contract_price_increases(tenant, year: int) -> list[ContractPriceIncreaseDetailType]:
    """
    Per-contract price increase details for a given year.

    Same logic as calculate_price_increase_impact but returns per-contract
    ARR breakdown instead of global aggregates.
    """
    jan1_current = date(year, 1, 1)
    jan1_previous = date(year - 1, 1, 1)

    contracts = Contract.objects.filter(
        tenant=tenant,
        status__in=[Contract.Status.ACTIVE, Contract.Status.PAUSED],
        start_date__lt=jan1_current,
    ).filter(
        Q(end_date__isnull=True) | Q(end_date__gte=jan1_current)
    ).prefetch_related("items", "items__product", "items__price_periods").select_related("customer")

    results = []
    dec31_current = date(year, 12, 31)

    for contract in contracts:
        items = list(contract.items.all())
        contract_current_arr = Decimal("0")
        contract_previous_arr = Decimal("0")
        increase_impact = Decimal("0")
        increase_item_count = 0

        for item in items:
            if item.is_one_off:
                continue

            price_periods_list = list(item.price_periods.all())

            # Current ARR = price at end of year, previous = price at start of year
            current_monthly = item.get_price_at_cached(
                dec31_current, price_periods_list, normalize_to_monthly=True
            )
            previous_monthly = item.get_price_at_cached(
                jan1_previous, price_periods_list, normalize_to_monthly=True
            )

            contract_current_arr += current_monthly * item.quantity * 12
            contract_previous_arr += previous_monthly * item.quantity * 12

            # Check for price periods starting this year
            year_periods = [pp for pp in price_periods_list if pp.valid_from.year == year]
            if year_periods:
                for pp in sorted(year_periods, key=lambda p: p.valid_from):
                    day_before = pp.valid_from - timedelta(days=1)
                    prev_m = item.get_price_at_cached(day_before, price_periods_list, normalize_to_monthly=True)
                    new_m = item.get_price_at_cached(pp.valid_from, price_periods_list, normalize_to_monthly=True)
                    if new_m > prev_m:
                        increase_item_count += 1
                        increase_impact += (new_m - prev_m) * item.quantity * 12
            elif current_monthly > previous_monthly:
                increase_item_count += 1
                increase_impact += (current_monthly - previous_monthly) * item.quantity * 12

        if increase_item_count > 0:
            results.append(ContractPriceIncreaseDetailType(
                contract_id=strawberry.ID(str(contract.id)),
                contract_name=contract.name or "",
                customer_name=contract.customer.name if contract.customer else "",
                current_arr=contract_current_arr,
                previous_arr=contract_previous_arr,
                arr_diff=increase_impact,
                item_count=increase_item_count,
            ))

    return results


def calculate_revenue_by_stream(tenant, year: int) -> list[dict]:
    """
    Calculate revenue grouped by revenue stream (effective_revenue_type)
    for a given year.

    Returns a list of dicts, one per stream, each with:
    - revenue_type: str (or "unclassified")
    - ytd_actual: Decimal (Jan 1 → today, or full year if year < current)
    - full_year_forecast: Decimal (Jan 1 → Dec 31)
    """
    today = date.today()
    year_start = date(year, 1, 1)
    year_end = date(year, 12, 31)

    # For YTD: if current year, use today; if past year, use year_end; if future, 0
    ytd_cutoff = min(today, year_end) if year <= today.year else None

    active_contracts = Contract.objects.filter(
        tenant=tenant,
        status=Contract.Status.ACTIVE,
    ).exclude(
        end_date__lt=year_start,
    ).prefetch_related("items", "items__product", "items__price_periods", "items__depends_on")

    # Accumulators: stream -> {ytd, forecast}
    streams: dict[str, dict[str, Decimal]] = {}

    for contract in active_contracts:
        items = list(contract.items.all())

        # Build a lookup: item_id -> effective_revenue_type
        item_revenue_types: dict[int, str] = {}
        for item in items:
            ert = item.get_effective_revenue_type()
            item_revenue_types[item.id] = ert or "unclassified"

        schedule = contract.get_recognition_schedule(
            from_date=year_start,
            to_date=year_end,
            include_history=True,
            items=items,
            include_eta_items=True,
        )

        for event in schedule:
            event_date = event["date"]
            for ei in event["items"]:
                stream = item_revenue_types.get(ei["item_id"], "unclassified")
                if stream not in streams:
                    streams[stream] = {"ytd": Decimal("0"), "forecast": Decimal("0")}

                amount = ei["amount"]
                streams[stream]["forecast"] += amount

                if ytd_cutoff and event_date <= ytd_cutoff:
                    streams[stream]["ytd"] += amount

    # Ensure all 3 standard streams are present
    from apps.core.models import RevenueType
    for rt_value, _ in RevenueType.choices:
        if rt_value not in streams:
            streams[rt_value] = {"ytd": Decimal("0"), "forecast": Decimal("0")}

    result = []
    for stream, data in streams.items():
        result.append({
            "revenue_type": stream,
            "ytd_actual": data["ytd"],
            "full_year_forecast": data["forecast"],
        })

    return result


@strawberry.type
class RevenueStreamDataType:
    revenue_type: str
    ytd_actual: Decimal
    full_year_forecast: Decimal


def _customers_with_prior_year_revenue(tenant, year: int) -> set[int]:
    """Return customer IDs that had revenue in year-1.

    Checks two sources:
    1. InvoiceRecords with invoice_date in year-1
    2. Active contracts that started on or before Dec 31 of year-1
       (i.e. customer was already a customer before the current year)
    """
    from apps.invoices.models import InvoiceRecord

    prior_year = year - 1

    # Source 1: Invoiced revenue
    from_invoices = set(
        InvoiceRecord.objects.filter(
            tenant=tenant,
            invoice_date__year=prior_year,
        ).exclude(
            status=InvoiceRecord.Status.VOIDED,
        ).exclude(
            total_net=0,
        ).values_list("customer_id", flat=True).distinct()
    )

    # Source 2: Contracts that were active/billing in the prior year
    from datetime import date
    year_end = date(prior_year, 12, 31)
    from_contracts = set(
        Contract.objects.filter(
            tenant=tenant,
            status__in=[Contract.Status.ACTIVE, Contract.Status.PAUSED, Contract.Status.CANCELLED],
            start_date__lte=year_end,
        ).exclude(
            # Exclude zero-value contracts
            items__isnull=True,
        ).values_list("customer_id", flat=True).distinct()
    )

    return from_invoices | from_contracts


_ARR_MULTIPLIERS = {
    "monthly": 12,
    "quarterly": 4,
    "semi_annual": 2,
    "annual": 1,
    "biennial": Decimal("0.5"),
    "triennial": Decimal("1") / 3,
    "quadrennial": Decimal("0.25"),
    "quinquennial": Decimal("0.2"),
}


def calculate_new_business_metrics(tenant, year: int) -> dict:
    """
    Calculate new business metrics for a given year.

    Split criterion: New Name = customer had NO invoiced revenue in year-1.
    Back-to-Base = customer HAD invoiced revenue in year-1.

    B2B additionally includes expansion/upsell items on existing contracts.
    """
    from apps.core.models import RevenueType
    from apps.contracts.models import calculate_arr_value

    existing_customers = _customers_with_prior_year_revenue(tenant, year)

    # --- Won deals ---
    won_contracts = Contract.objects.filter(
        tenant=tenant,
        hubspot_deal_id__isnull=False,
        deal_won_date__year=year,
        status=Contract.Status.ACTIVE,
    ).exclude(
        hubspot_deal_id=""
    ).select_related("customer").prefetch_related("items", "items__product")

    won_new_arr = Decimal("0")
    won_b2b_arr = Decimal("0")
    won_development_revenue = Decimal("0")
    won_deal_count = won_contracts.count()

    for contract in won_contracts:
        is_existing = contract.customer_id in existing_customers
        for item in contract.items.all():
            ert = item.get_effective_revenue_type()
            face_value = item.unit_price * item.quantity

            if item.is_one_off:
                if ert in (RevenueType.ADVANCED_DEVELOPMENT, RevenueType.TRAINING_IMPLEMENTATION):
                    won_development_revenue += face_value
            else:
                annualized = face_value * _ARR_MULTIPLIERS.get(item.price_period or "monthly", 12)
                if ert in (RevenueType.ADVANCED_DEVELOPMENT, RevenueType.TRAINING_IMPLEMENTATION):
                    won_development_revenue += annualized
                elif is_existing:
                    won_b2b_arr += annualized
                else:
                    won_new_arr += annualized

    # --- Expansion/upsell on existing contracts ---
    # Only count items that have an explicit deal_won_date in the current year.
    # Items without deal_won_date are transfers/internal moves, not real upsells.
    won_contract_ids = set(won_contracts.values_list("id", flat=True))
    expansion_items = ContractItem.objects.filter(
        tenant=tenant,
        contract__status__in=[Contract.Status.ACTIVE, Contract.Status.PAUSED],
        deal_won_date__year=year,
    ).exclude(
        contract_id__in=won_contract_ids,
    ).select_related("contract", "product")

    for item in expansion_items:
        ert = item.get_effective_revenue_type()
        if item.is_one_off:
            # One-off expansion items → Won Development
            if ert in (RevenueType.ADVANCED_DEVELOPMENT, RevenueType.TRAINING_IMPLEMENTATION):
                face_value = item.unit_price * item.quantity
                won_development_revenue += face_value
        else:
            # Recurring expansion items → B2B ARR
            arr = calculate_arr_value(
                item.unit_price, item.quantity, item.price_period, False,
            )
            if arr > 0:
                won_b2b_arr += arr

    # --- Negotiated price increases on existing contracts = B2B bookings ---
    price_impact = calculate_price_increase_impact(tenant, year)
    won_b2b_arr += price_impact.negotiated_arr_impact

    return {
        "won_new_arr": won_new_arr,
        "won_b2b_arr": won_b2b_arr,
        "won_development_revenue": won_development_revenue,
        "won_deal_count": won_deal_count,
    }


@strawberry.type
class NewBusinessMetricsType:
    won_new_arr: Decimal
    back_to_base_arr: Decimal
    won_development_revenue: Decimal
    won_deal_count: int


@strawberry.type
class NewBusinessDetailItem:
    customer_id: int
    customer_name: str
    contract_id: int
    contract_name: str
    item_id: int | None = None
    item_description: str | None = None
    value: Decimal = Decimal("0")
    source: str = ""  # "won_deal" or "expansion"


@strawberry.type
class NewBusinessGoalGQLType:
    id: int
    year: int
    goal_type: str
    target_amount: Decimal


@strawberry.type
class NewBusinessGoalResult:
    goal: NewBusinessGoalGQLType | None = None
    success: bool = False
    error: str | None = None


@strawberry.type
class WonDealType:
    contract_id: int
    contract_name: str
    customer_name: str
    deal_won_date: str
    annual_recurring_revenue: Decimal


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
class ActivationPreviewOneOffItem:
    """A one-off item that may need a Clockodo project."""
    id: int
    description: str


@strawberry.type
class ActivationPreviewResult:
    """Preview of what Clockodo projects would be created on activation."""
    clockodo_configured: bool
    customer_linked: bool
    customer_name: str
    customer_id: int
    clockodo_customer_id: str | None
    maintenance_needed: bool
    maintenance_project_exists: bool
    maintenance_project_name: str
    one_off_items: list[ActivationPreviewOneOffItem]


@strawberry.type
class ProvisioningProjectResult:
    """A project that was created or linked during provisioning."""
    name: str
    action: str  # "created" or "linked"


@strawberry.type
class ProvisioningResult:
    """Result of Clockodo project provisioning."""
    success: bool
    created_projects: list[ProvisioningProjectResult]
    errors: list[str]


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
    contract_item_monthly_revenue: float | None = None  # monthly revenue of linked item
    link_source: str = "manual"


@strawberry.type
class AutoLinkRuleType:
    """A pattern-based auto-link rule for time tracking projects."""
    id: int
    pattern: str
    match_type: str
    is_active: bool
    contract_item_id: int | None = None
    contract_item_name: str | None = None
    created_mappings_count: int = 0


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
    auto_link_rules: list[AutoLinkRuleType] = strawberry.field(default_factory=list)
    last_synced: datetime | None = None


@strawberry.type
class TimeTrackingMappingResult:
    """Result of a mapping mutation."""
    success: bool
    error: str | None = None
    mapping: TimeTrackingMappingType | None = None
    # Populated when a "already mapped" conflict occurs so the UI can point
    # the user at the existing link.
    conflict_contract_id: int | None = None
    conflict_contract_name: str | None = None
    conflict_item_name: str | None = None


# =============================================================================
# Department Time Analysis Types
# =============================================================================


@strawberry.type
class DepartmentType:
    """A department for grouping time tracking services."""
    id: strawberry.ID
    name: str
    sort_order: int
    cost_center_id: Optional[strawberry.ID] = None
    cost_center_name: Optional[str] = None
    cost_center_code: Optional[str] = None


@strawberry.type
class DepartmentServiceMappingType:
    """A mapping between an external service and a department."""
    id: strawberry.ID
    external_service_id: str
    external_service_name: str
    department_id: strawberry.ID


@strawberry.type
class ClockodoServiceType:
    """An external service from the time tracking provider."""
    id: str
    name: str


@strawberry.type
class DepartmentTimeEntry:
    """Time distribution for a single department."""
    department_name: str
    hours: float
    percentage: float


@strawberry.type
class UserDepartmentHours:
    """Hours for a specific department within a user row."""
    department_name: str
    hours: float
    percentage: float


@strawberry.type
class UserDepartmentRow:
    """One user's time across all departments."""
    user_name: str
    departments: list[UserDepartmentHours]
    total_hours: float
    absence_days: float | None = None
    sick_days: float | None = None
    sick_certificate_days: float | None = None
    sick_child_days: float | None = None


@strawberry.type
class DepartmentTimeAnalysisType:
    """Full department time analysis result."""
    distribution: list[DepartmentTimeEntry]
    distribution_filled: list[DepartmentTimeEntry] | None = None
    user_matrix: list[UserDepartmentRow]
    user_matrix_filled: list[UserDepartmentRow] | None = None
    total_hours: float
    total_hours_filled: float | None = None
    cost_distribution: list["DepartmentCostEntry"] | None = None
    total_cost: float | None = None


@strawberry.input
class DepartmentServiceMappingInput:
    """Input for bulk saving department-service mappings."""
    external_service_id: str
    external_service_name: str
    department_id: strawberry.ID


@strawberry.type
class ClockodoUserType:
    """A user from the time tracking provider."""
    id: str
    name: str


@strawberry.type
class UserCostProfileType:
    """A user's cost profile for department cost analysis."""
    id: strawberry.ID
    external_user_id: str
    external_user_name: str
    fte_percentage: int
    monthly_income: float
    default_department_id: strawberry.ID | None


@strawberry.input
class UserCostProfileInput:
    """Input for saving a user cost profile."""
    external_user_id: str
    external_user_name: str
    fte_percentage: int
    monthly_income: float
    default_department_id: strawberry.ID | None = None


@strawberry.type
class DepartmentCostEntry:
    """Cost distribution for a single department."""
    department_name: str
    cost: float
    percentage: float
    ftes: float


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


class _ImportedInvoiceAdapter:
    """Adapter to make ImportedInvoice compatible with _find_best_invoice_for_period
    and _determine_cell_invoice_status (which expect InvoiceRecord-like objects)."""

    def __init__(self, imported):
        from dateutil.relativedelta import relativedelta

        self.id = imported.id
        # Map extraction_status to InvoiceRecord-like status
        status_map = {"confirmed": "sent", "sent": "sent", "paid": "paid"}
        self.status = status_map.get(imported.extraction_status, "finalized")
        # Use billing_date (set from forecast upload) or fall back to invoice_date
        ref_date = imported.billing_date or imported.invoice_date
        self.billing_date = ref_date
        if ref_date:
            # Derive period from linked contract's billing interval if available
            interval_months = 1
            if imported.contract:
                interval_map = {
                    "monthly": 1, "bi_monthly": 2, "quarterly": 3,
                    "semi_annual": 6, "annual": 12, "biennial": 24,
                    "triennial": 36, "quadrennial": 48, "quinquennial": 60,
                }
                interval_months = interval_map.get(imported.contract.billing_interval, 1)
            self.period_start = ref_date.replace(day=1)
            self.period_end = self.period_start + relativedelta(months=interval_months, days=-1)
        else:
            self.period_start = None
            self.period_end = None
        self.email_sent_at = None
        # Use bool() on prefetched queryset to avoid extra DB query
        self._is_paid_cached = imported.extraction_status == "paid" or bool(imported.payment_matches.all())
        self.contract_id = imported.contract_id


def _merge_imported_invoices(invoice_lookup, tenant, contract_ids, from_date, to_date):
    """Add confirmed/sent/paid imported invoices to the invoice lookup."""
    from apps.invoices.models import ImportedInvoice

    from django.db.models import Q

    imported_qs = ImportedInvoice.objects.filter(
        tenant=tenant,
        contract_id__in=contract_ids,
        extraction_status__in=["confirmed", "sent", "paid"],
    ).filter(
        # Match by billing_date (from forecast upload) or invoice_date
        Q(billing_date__gte=from_date, billing_date__lte=to_date) |
        Q(billing_date__isnull=True, invoice_date__gte=from_date, invoice_date__lte=to_date)
    ).select_related("contract").prefetch_related("payment_matches")

    for imp in imported_qs:
        adapter = _ImportedInvoiceAdapter(imp)
        if adapter.period_start and adapter.period_end:
            invoice_lookup[imp.contract_id].append(adapter)


def _find_best_invoice_for_period(period_str: str, invoices: list, is_quarterly: bool):
    """Find the most relevant non-voided InvoiceRecord for a given period.

    Uses period overlap matching (inv.period_start <= period_end AND inv.period_end >= period_start).
    When multiple match, picks highest priority status (paid > dunning > sent > finalized > draft).
    """
    from dateutil.relativedelta import relativedelta

    # Parse period string to date range
    if is_quarterly and "Q" in period_str:
        year_str, q_str = period_str.split("-Q")
        quarter = int(q_str)
        year = int(year_str)
        period_start = date(year, (quarter - 1) * 3 + 1, 1)
        period_end = period_start + relativedelta(months=3, days=-1)
    else:
        parts = period_str.split("-")
        year, month = int(parts[0]), int(parts[1])
        period_start = date(year, month, 1)
        period_end = period_start + relativedelta(months=1, days=-1)

    # Status priority (higher = better)
    status_priority = {
        "paid": 5,
        "dunning": 4,
        "sent": 3,
        "finalized": 2,
        "draft": 1,
    }

    best = None
    best_priority = -1
    for inv in invoices:
        # Check overlap: inv.period_start <= period_end AND inv.period_end >= period_start
        if inv.period_start <= period_end and inv.period_end >= period_start:
            priority = status_priority.get(inv.status, 0)
            if priority > best_priority:
                best = inv
                best_priority = priority

    return best


def _determine_cell_invoice_status(invoice, period_str: str, today: date, is_quarterly: bool) -> str | None:
    """Determine the display status for a forecast cell.

    Returns: None (future), "actionable", "sent", "paid", or "overdue"
    """
    from dateutil.relativedelta import relativedelta
    from datetime import timedelta

    # Determine period end date
    if is_quarterly and "Q" in period_str:
        year_str, q_str = period_str.split("-Q")
        quarter = int(q_str)
        year = int(year_str)
        period_end = date(year, (quarter - 1) * 3 + 1, 1) + relativedelta(months=3, days=-1)
    else:
        parts = period_str.split("-")
        year, month = int(parts[0]), int(parts[1])
        period_end = date(year, month, 1) + relativedelta(months=1, days=-1)

    # Future: period end is after today and no invoice
    if period_end > today and invoice is None:
        return None

    # No invoice or draft => actionable (for past/current periods)
    if invoice is None or invoice.status == "draft":
        return "actionable"

    # Finalized: check if email was actually sent (status may not have been updated)
    if invoice.status == "finalized":
        if invoice.email_sent_at:
            sent_date = invoice.email_sent_at.date()
            if (today - sent_date).days >= 60:
                return "overdue"
            return "sent"
        return "actionable"

    # Paid: has payment match or status is paid
    if invoice.status == "paid" or invoice._is_paid_cached:
        return "paid"

    # Sent or dunning: check overdue (60+ days)
    if invoice.status in ("sent", "dunning"):
        sent_date = None
        if invoice.email_sent_at:
            sent_date = invoice.email_sent_at.date()
        else:
            sent_date = invoice.billing_date

        if sent_date and (today - sent_date).days >= 60:
            return "overdue"
        return "sent"

    return "actionable"


# =============================================================================
# Revenue Goal Types
# =============================================================================


@strawberry.type
class RevenueGoalType:
    id: int
    year: int
    revenue_type: str
    target_amount: Decimal


@strawberry.type
class RevenueGoalResult:
    goal: RevenueGoalType | None = None
    success: bool = False
    error: str | None = None


@strawberry.type
class UnclassifiedItemType:
    """A contract item without a revenue type classification."""
    item_id: int
    product_name: str | None
    description: str
    is_one_off: bool
    unit_price: Decimal
    quantity: int
    contract_id: int
    contract_name: str
    customer_name: str
    customer_id: int


@strawberry.type
class AbsenceReportEntryType:
    """An individual absence entry within a report."""
    id: int
    user_name: str
    external_user_id: str
    absence_type: str
    date_from: date
    date_to: date
    days_count: Decimal


@strawberry.type
class AbsenceReportType:
    """Monthly absence report."""
    id: int
    year: int
    month: int
    status: str
    finalized_at: datetime | None
    entries: list[AbsenceReportEntryType]


@strawberry.input
class MergeContractItemOverrideInput:
    """Per-item date overrides for contract merge."""
    item_id: int
    start_date: date | None = None
    billing_start_date: date | None = None


@strawberry.input
class MergeContractInput:
    """Input for merging a source contract into a target contract."""
    source_contract_id: strawberry.ID
    target_contract_id: strawberry.ID
    item_overrides: list[MergeContractItemOverrideInput] | None = None


@strawberry.type
class MergePreviewItemType:
    """An item in the merge preview."""
    id: int
    product_name: str | None
    description: str
    quantity: int
    unit_price: str
    price_period: str
    start_date: str | None
    billing_start_date: str | None
    is_one_off: bool


@strawberry.type
class MergeClockodoPreviewType:
    """Clockodo impact preview for merge."""
    has_new_recurring_items: bool
    new_one_off_items: list[str]
    source_mappings_will_be_deleted: int


@strawberry.type
class MergeContractPreviewType:
    """Preview result for a contract merge."""
    items: list[MergePreviewItemType]
    will_create_amendments: bool
    clockodo_preview: MergeClockodoPreviewType | None = None
    source_contract_name: str
    target_contract_name: str
    errors: list[str] = strawberry.field(default_factory=list)


@strawberry.type
class MergeContractResult:
    """Result of a contract merge operation."""
    contract: ContractType | None = None
    success: bool = False
    errors: list[str] = strawberry.field(default_factory=list)
    items_transferred: int = 0


@strawberry.type
class ContractQuery:
    @strawberry.field
    def preview_contract_activation(
        self,
        info: Info[Context, None],
        contract_id: strawberry.ID,
    ) -> ActivationPreviewResult | None:
        """Preview Clockodo project creation for contract activation."""
        from apps.contracts.services.clockodo_provisioning import preview_activation

        user = require_perm(info, "contracts", "read")
        if not user.tenant:
            return None

        try:
            contract = Contract.objects.select_related("customer", "tenant").prefetch_related("items").get(
                id=contract_id, tenant=user.tenant
            )
        except Contract.DoesNotExist:
            return None

        result = preview_activation(contract)
        return ActivationPreviewResult(
            clockodo_configured=result["clockodo_configured"],
            customer_linked=result["customer_linked"],
            customer_name=result["customer_name"],
            customer_id=result["customer_id"],
            clockodo_customer_id=result.get("clockodo_customer_id"),
            maintenance_needed=result["maintenance_needed"],
            maintenance_project_exists=result["maintenance_project_exists"],
            maintenance_project_name=result["maintenance_project_name"],
            one_off_items=[
                ActivationPreviewOneOffItem(id=i["id"], description=i["description"])
                for i in result["one_off_items"]
            ],
        )

    @strawberry.field
    def merge_contract_preview(
        self,
        info: Info[Context, None],
        source_contract_id: strawberry.ID,
        target_contract_id: strawberry.ID,
    ) -> MergeContractPreviewType:
        """Preview a contract merge operation."""
        from apps.contracts.services.contract_merge import (
            preview_merge,
            validate_merge_preconditions,
        )

        user = require_perm(info, "contracts", "read")

        try:
            source = Contract.objects.select_related("customer", "tenant").prefetch_related(
                "items__product", "time_tracking_mappings"
            ).get(id=source_contract_id, tenant=user.tenant)
            target = Contract.objects.select_related("customer", "tenant").prefetch_related(
                "time_tracking_mappings"
            ).get(id=target_contract_id, tenant=user.tenant)
        except Contract.DoesNotExist:
            return MergeContractPreviewType(
                items=[], will_create_amendments=False,
                source_contract_name="", target_contract_name="",
                errors=["Contract not found"],
            )

        errors = validate_merge_preconditions(source, target)
        if errors:
            return MergeContractPreviewType(
                items=[], will_create_amendments=False,
                source_contract_name=source.name, target_contract_name=target.name,
                errors=errors,
            )

        result = preview_merge(source, target)

        clockodo_preview = None
        if result.get("clockodo_preview"):
            cp = result["clockodo_preview"]
            clockodo_preview = MergeClockodoPreviewType(
                has_new_recurring_items=cp["has_new_recurring_items"],
                new_one_off_items=[item["description"] for item in cp["new_one_off_items"]],
                source_mappings_will_be_deleted=cp["source_mappings_will_be_deleted"],
            )

        return MergeContractPreviewType(
            items=[
                MergePreviewItemType(
                    id=item["id"],
                    product_name=item["product_name"],
                    description=item["description"],
                    quantity=item["quantity"],
                    unit_price=item["unit_price"],
                    price_period=item["price_period"],
                    start_date=item["start_date"],
                    billing_start_date=item["billing_start_date"],
                    is_one_off=item["is_one_off"],
                )
                for item in result["items"]
            ],
            will_create_amendments=result["will_create_amendments"],
            clockodo_preview=clockodo_preview,
            source_contract_name=result["source_contract_name"],
            target_contract_name=result["target_contract_name"],
        )

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
    def price_increase_impact(
        self,
        info: Info[Context, None],
        year: int,
    ) -> PriceIncreaseImpactType:
        """Get YoY ARR impact from price increases for a given year."""
        user = require_perm(info, "contracts", "read")
        if not user.tenant:
            return PriceIncreaseImpactType(
                year=year,
                total_arr_impact=Decimal("0"),
                inflation_arr_impact=Decimal("0"),
                negotiated_arr_impact=Decimal("0"),
                untagged_arr_impact=Decimal("0"),
                item_count=0,
            )
        return calculate_price_increase_impact(user.tenant, year)

    @strawberry.field
    def contract_price_increases(
        self,
        info: Info[Context, None],
        year: int,
    ) -> list[ContractPriceIncreaseDetailType]:
        """Get per-contract price increase details for a given year."""
        user = require_perm(info, "contracts", "read")
        if not user.tenant:
            return []
        return calculate_contract_price_increases(user.tenant, year)

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
            ).exclude(status=InvoiceRecord.Status.VOIDED).exclude(document_type="storno")
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
                # Try exact match by billing_date on imported invoices
                matched_invoice = None
                for inv in contract_invoices:
                    if inv.billing_date == event["date"]:
                        pdf_url = inv.pdf_file.url if inv.pdf_file else None
                        matched_invoice = MatchedInvoiceType(
                            id=strawberry.ID(str(inv.id)),
                            invoice_number=inv.invoice_number or "",
                            is_paid=inv.is_paid,
                            pdf_url=pdf_url,
                        )
                        break

                # Fall back to imported invoice heuristic
                if not matched_invoice:
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
                            description=item.get("description", ""),
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
        refresh: bool = False,
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

        cache_params = dict(view=view, months=months, quarters=quarters, pro_rata=pro_rata, exclude_one_off=exclude_one_off)
        if not refresh:
            cached = get_cached_forecast("forecast", user.tenant.id, **cache_params)
            if cached is not None:
                return dict_to_forecast_result(cached)

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
        # Exclude contracts whose end_date is before the forecast start
        # (active + end_date in past = effectively ended)
        # Prefetch items with products and price_periods to avoid N+1 queries
        contracts = Contract.objects.filter(
            tenant=user.tenant,
            status__in=[Contract.Status.ACTIVE, Contract.Status.PAUSED],
        ).exclude(
            end_date__lt=from_date,
        ).select_related("customer").prefetch_related("items__product", "items__price_periods", "items__depends_on")

        # Bulk-fetch InvoiceRecords for invoice status color-coding
        from apps.invoices.models import ImportedInvoice, InvoiceRecord
        contract_ids = [c.id for c in contracts]
        invoice_qs = (
            InvoiceRecord.objects.filter(
                tenant=user.tenant,
                contract_id__in=contract_ids,
                period_start__lte=to_date,
                period_end__gte=from_date,
            )
            .exclude(status="voided")
            .exclude(document_type="storno")
            .prefetch_related("payment_matches")
        )
        # Build lookup: {contract_id: [InvoiceRecord, ...]}
        invoice_lookup: dict[int, list] = defaultdict(list)
        for inv in invoice_qs:
            # Use bool() on prefetched queryset — avoids extra DB query
            inv._is_paid_cached = bool(inv.payment_matches.all())
            invoice_lookup[inv.contract_id].append(inv)

        # Also include confirmed/sent/paid imported invoices linked to contracts
        _merge_imported_invoices(
            invoice_lookup, user.tenant, contract_ids, from_date, to_date
        )

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
                    item for item in contract.items.all()
                    if not item.is_one_off
                )
                if not items:
                    continue
                items_arg = items

            # For pro-rata mode we need billing events that started before from_date
            # but whose period extends into the forecast window (e.g. an annual
            # billing on 2025-04-01 that covers Apr 2025 – Mar 2026 must contribute
            # to Jan–Mar 2026). Look back by one full billing interval.
            if pro_rata:
                contract_billing_months = interval_months.get(contract.billing_interval, 1)
                sched_from_date = from_date - relativedelta(months=contract_billing_months)
            else:
                sched_from_date = from_date

            schedule = contract.get_billing_schedule(
                from_date=sched_from_date,
                to_date=to_date,
                include_history=False,
                items=items_arg,
                include_eta_items=True,
            )

            # Group by period
            period_amounts = defaultdict(Decimal)

            if pro_rata:
                # Pro-rata: distribute each billing event across the months it covers
                billing_months = contract_billing_months

                for event in schedule:
                    event_total = event["total"]
                    event_date = event["date"]

                    # Determine actual months this billing event covers.
                    #
                    # Priority 1 – event is explicitly pro-rated (pre-alignment stub
                    # or contract-end stub): derive directly from the stored
                    # prorate_factor so the distribution window matches the billing
                    # amount exactly.
                    #
                    # Priority 2 – event is NOT pro-rated but the contract runs
                    # shorter than the full billing interval (e.g. biennial with
                    # min_duration_months=13 and no end_date): cap at the contract's
                    # effective end derived from end_date or min_duration_months.
                    event_items = event.get("items", [])
                    prorated_item = next(
                        (i for i in event_items if i.get("is_prorated") and i.get("prorate_factor")),
                        None,
                    )
                    if prorated_item:
                        actual_months = max(1, round(billing_months * float(prorated_item["prorate_factor"])))
                    else:
                        next_billing = date(event_date.year, event_date.month, 1) + relativedelta(months=billing_months)
                        contract_effective_end = contract.end_date
                        if not contract_effective_end and contract.min_duration_months:
                            contract_effective_end = contract.start_date + relativedelta(months=contract.min_duration_months)
                        if contract_effective_end:
                            actual_end = min(next_billing, contract_effective_end)
                        else:
                            actual_end = next_billing
                        actual_months = (actual_end.year - event_date.year) * 12 + (actual_end.month - event_date.month)
                        actual_months = max(1, actual_months)

                    if is_quarterly:
                        # For quarterly view, distribute across quarters
                        actual_quarters = max(1, (actual_months + 2) // 3)
                        amount_per_quarter = event_total / actual_quarters

                        # Start from the billing quarter and go forward
                        q = (event_date.month - 1) // 3 + 1
                        y = event_date.year
                        for _ in range(actual_quarters):
                            period_key = f"{y}-Q{q}"
                            if period_key in period_column_set:
                                period_amounts[period_key] += amount_per_quarter
                            q += 1
                            if q > 4:
                                q = 1
                                y += 1
                    else:
                        # For monthly view, distribute across the actual covered months
                        amount_per_month = event_total / actual_months

                        # Start from the billing month and go forward
                        dist_date = date(event_date.year, event_date.month, 1)
                        for _ in range(actual_months):
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
            contract_invoices = invoice_lookup.get(contract.id, [])
            contract_periods = []
            contract_total = Decimal("0")
            for period in period_columns:
                amount = period_amounts.get(period, Decimal("0"))
                # Determine invoice status for non-zero cells
                inv_status = None
                if amount != 0:
                    best_inv = _find_best_invoice_for_period(period, contract_invoices, is_quarterly)
                    inv_status = _determine_cell_invoice_status(best_inv, period, today, is_quarterly)
                contract_periods.append(RevenueMonthData(month=period, amount=amount, invoice_status=inv_status))
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
                        customer_number=contract.customer.netsuite_customer_number,
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

        result = RevenueForecastResult(
            month_columns=period_columns,
            monthly_totals=totals_list,
            contracts=contract_rows,
            grand_total=grand_total,
        )
        set_cached_forecast("forecast", user.tenant, forecast_result_to_dict(result), **cache_params)
        return result

    @strawberry.field
    def recognition_forecast(
        self,
        info: Info[Context, None],
        months: int | None = None,
        quarters: int | None = None,
        view: str = "monthly",
        pro_rata: bool = False,
        exclude_one_off: bool = False,
        refresh: bool = False,
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

        cache_params = dict(view=view, months=months, quarters=quarters, pro_rata=pro_rata, exclude_one_off=exclude_one_off)
        if not refresh:
            cached = get_cached_forecast("recognition", user.tenant.id, **cache_params)
            if cached is not None:
                return dict_to_forecast_result(cached)

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
        # Exclude contracts whose end_date is before the forecast start
        # (active + end_date in past = effectively ended)
        # Prefetch items with products and price_periods to avoid N+1 queries
        contracts = Contract.objects.filter(
            tenant=user.tenant,
            status__in=[Contract.Status.ACTIVE, Contract.Status.PAUSED],
        ).exclude(
            end_date__lt=from_date,
        ).select_related("customer").prefetch_related("items__product", "items__price_periods", "items__depends_on")

        # Bulk-fetch InvoiceRecords for invoice status color-coding
        from apps.invoices.models import ImportedInvoice, InvoiceRecord
        contract_ids = [c.id for c in contracts]
        invoice_qs = (
            InvoiceRecord.objects.filter(
                tenant=user.tenant,
                contract_id__in=contract_ids,
                period_start__lte=to_date,
                period_end__gte=from_date,
            )
            .exclude(status="voided")
            .exclude(document_type="storno")
            .prefetch_related("payment_matches")
        )
        invoice_lookup: dict[int, list] = defaultdict(list)
        for inv in invoice_qs:
            # Use bool() on prefetched queryset — avoids extra DB query
            inv._is_paid_cached = bool(inv.payment_matches.all())
            invoice_lookup[inv.contract_id].append(inv)

        # Also include confirmed/sent/paid imported invoices linked to contracts
        _merge_imported_invoices(
            invoice_lookup, user.tenant, contract_ids, from_date, to_date
        )

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
                    item for item in contract.items.all()
                    if not item.is_one_off
                )
                if not items:
                    continue
                items_arg = items

            # Look back one full recognition interval so events that started
            # before the forecast window but distribute INTO it (e.g. an annual
            # contract that started 2025-05 distributes into Jan–Apr 2026) are
            # included. Months outside the window are filtered by
            # period_column_set during distribution.
            contract_billing_months = interval_months.get(contract.billing_interval, 1)
            recognition_lookback = min(contract_billing_months, 12)
            sched_from_date = from_date - relativedelta(months=recognition_lookback)

            schedule = contract.get_recognition_schedule(
                from_date=sched_from_date,
                to_date=to_date,
                include_history=True,
                items=items_arg,
                include_eta_items=True,
            )

            # Group by period
            period_amounts = defaultdict(Decimal)

            # Revenue recognition is *always* pro-rated by accounting principle
            # (monthly recognition for ongoing services, regardless of billing
            # cadence). The pro_rata flag is kept on the API for symmetry with
            # revenue_forecast but is effectively always-on here.
            #
            # Per-month amount comes directly from each item's monthly unit_price
            # (× quantity). This avoids dividing aggregated event totals back
            # into months and the rounding artifacts that come with it.
            #
            # For multi-year intervals, recognition_schedule emits annual events
            # (recognition_interval = min(interval_months, 12)).
            base_distribution_months = min(contract_billing_months, 12)

            for event in schedule:
                event_date = event["date"]
                event_items = event.get("items", [])

                # Honor prorate_factor for explicitly pro-rated events
                # (pre-alignment stub, contract-end stub) so the distribution
                # window matches the billing amount exactly. Falls back to the
                # full recognition interval for non-prorated events.
                prorated_item = next(
                    (i for i in event_items if i.get("is_prorated") and i.get("prorate_factor")),
                    None,
                )
                if prorated_item:
                    distribution_months = max(1, round(base_distribution_months * float(prorated_item["prorate_factor"])))
                else:
                    distribution_months = base_distribution_months

                # Sum monthly amounts from regular items (monthly unit_price × qty).
                # One-off items are recognized in full on the event date instead.
                monthly_total = Decimal("0")
                one_off_total = Decimal("0")
                for it in event_items:
                    if it.get("is_one_off"):
                        one_off_total += Decimal(it["amount"])
                    else:
                        monthly_total += Decimal(it["unit_price"]) * Decimal(it["quantity"])

                if is_quarterly:
                    # Distribute monthly_total over months, then group into quarters.
                    dist_date = date(event_date.year, event_date.month, 1)
                    for _ in range(distribution_months):
                        q = (dist_date.month - 1) // 3 + 1
                        period_key = f"{dist_date.year}-Q{q}"
                        if period_key in period_column_set:
                            period_amounts[period_key] += monthly_total
                        dist_date += relativedelta(months=1)
                    # One-off in the event's quarter
                    if one_off_total:
                        q = (event_date.month - 1) // 3 + 1
                        ok = f"{event_date.year}-Q{q}"
                        if ok in period_column_set:
                            period_amounts[ok] += one_off_total
                else:
                    dist_date = date(event_date.year, event_date.month, 1)
                    for _ in range(distribution_months):
                        period_key = dist_date.strftime("%Y-%m")
                        if period_key in period_column_set:
                            period_amounts[period_key] += monthly_total
                        dist_date += relativedelta(months=1)
                    if one_off_total:
                        ok = event_date.strftime("%Y-%m")
                        if ok in period_column_set:
                            period_amounts[ok] += one_off_total

            # Build period data for this contract
            contract_invoices = invoice_lookup.get(contract.id, [])
            contract_periods = []
            contract_total = Decimal("0")
            for period in period_columns:
                amount = period_amounts.get(period, Decimal("0"))
                inv_status = None
                if amount != 0:
                    best_inv = _find_best_invoice_for_period(period, contract_invoices, is_quarterly)
                    inv_status = _determine_cell_invoice_status(best_inv, period, today, is_quarterly)
                contract_periods.append(RevenueMonthData(month=period, amount=amount, invoice_status=inv_status))
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
                        customer_number=contract.customer.netsuite_customer_number,
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

        result = RevenueForecastResult(
            month_columns=period_columns,
            monthly_totals=totals_list,
            contracts=contract_rows,
            grand_total=grand_total,
        )
        set_cached_forecast("recognition", user.tenant, forecast_result_to_dict(result), **cache_params)
        return result

    @strawberry.field
    def contracts(
        self,
        info: Info[Context, None],
        search: str | None = None,
        status: str | None = None,
        is_new_business: bool | None = None,
        deal_won_year: int | None = None,
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

        queryset = Contract.objects.filter(tenant=user.tenant).select_related(
            "customer", "group"
        ).prefetch_related("items", "items__price_periods").annotate(
            _group_contract_count=Subquery(
                Contract.objects.filter(
                    group_id=OuterRef("group_id"),
                ).values("group_id").annotate(cnt=Count("id")).values("cnt")[:1]
            )
        )

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

        # New business filter
        if is_new_business is True:
            queryset = queryset.filter(
                hubspot_deal_id__isnull=False,
            ).exclude(hubspot_deal_id="")
        if deal_won_year is not None:
            queryset = queryset.filter(deal_won_date__year=deal_won_year)

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
            all_contracts = list(queryset)

            def get_arr(contract):
                from decimal import Decimal
                from datetime import date as date_type
                today = date_type.today()

                monthly_total = Decimal("0")
                for item in contract.items.all():
                    if not item.is_one_off:
                        price_periods = list(item.price_periods.all())
                        monthly_unit_price = item.get_price_at_cached(today, price_periods, normalize_to_monthly=True)
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

        mapping_types = []
        for m in mappings:
            item_monthly_revenue = None
            if m.contract_item:
                item = m.contract_item
                monthly_price = float(item.get_price_at(date.today(), normalize_to_monthly=True))
                item_monthly_revenue = item.quantity * monthly_price

            mapping_types.append(TimeTrackingMappingType(
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
                contract_item_monthly_revenue=item_monthly_revenue,
                link_source=m.link_source,
            ))

        # Load auto-link rules for this contract
        rules = AutoLinkRule.objects.filter(
            tenant=user.tenant, contract=contract,
        ).select_related("contract_item", "contract_item__product")
        rule_types = [
            AutoLinkRuleType(
                id=r.id,
                pattern=r.pattern,
                match_type=r.match_type,
                is_active=r.is_active,
                contract_item_id=r.contract_item_id,
                contract_item_name=(
                    r.contract_item.product.name if r.contract_item and r.contract_item.product
                    else r.contract_item.description[:50] if r.contract_item
                    else None
                ),
                created_mappings_count=r.created_mappings.count(),
            )
            for r in rules
        ]

        if not mappings.exists():
            return TimeTrackingSummaryType(
                total_hours=0,
                total_revenue=0,
                by_service=[],
                by_month=[],
                mappings=mapping_types,
                auto_link_rules=rule_types,
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
            auto_link_rules=rule_types,
            last_synced=cached["last_synced"],
        )

    @strawberry.field
    def preview_auto_link_matches(
        self,
        info: Info[Context, None],
        pattern: str,
        match_type: str = "contains",
    ) -> list[TimeTrackingExternalProject]:
        """Preview which unlinked projects match a pattern."""
        from apps.contracts.services.time_tracking import get_provider, matches_project_name

        user = require_perm(info, "contracts", "read")
        if not user.tenant:
            return []

        provider = get_provider(user.tenant)
        if not provider:
            return []

        if match_type not in ("contains", "starts_with"):
            return []

        try:
            projects = provider.get_projects()
        except Exception:
            return []

        # Exclude already-linked projects
        linked_ids = set(
            TimeTrackingProjectMapping.objects.filter(
                tenant=user.tenant,
            ).values_list("external_project_id", flat=True)
        )

        return [
            TimeTrackingExternalProject(
                id=p.id,
                name=p.name,
                customer_name=p.customer_name,
                active=p.active,
            )
            for p in projects
            if p.id not in linked_ids
            and matches_project_name(pattern, match_type, p.name)
        ]

    # -----------------------------------------------------------------
    # Department Time Analysis Queries
    # -----------------------------------------------------------------

    @strawberry.field
    def departments(self, info: Info[Context, None]) -> list[DepartmentType]:
        """Get all departments for the current tenant."""
        user = require_perm(info, "contracts", "read")
        if not user.tenant:
            return []
        return [
            DepartmentType(
                id=strawberry.ID(str(d.id)),
                name=d.name,
                sort_order=d.sort_order,
                cost_center_id=strawberry.ID(str(d.cost_center_id)) if d.cost_center_id else None,
                cost_center_name=d.cost_center.name if d.cost_center_id else None,
                cost_center_code=d.cost_center.code if d.cost_center_id else None,
            )
            for d in Department.objects.filter(tenant=user.tenant).select_related("cost_center")
        ]

    @strawberry.field
    def clockodo_services(self, info: Info[Context, None]) -> list[ClockodoServiceType]:
        """Fetch available services from the time tracking provider."""
        from apps.contracts.services.time_tracking import get_provider

        user = require_perm(info, "contracts", "read")
        if not user.tenant:
            return []
        provider = get_provider(user.tenant)
        if not provider:
            return []
        try:
            services = provider.get_services()
        except NotImplementedError:
            return []
        return [ClockodoServiceType(id=s["id"], name=s["name"]) for s in services]

    @strawberry.field
    def clockodo_users(self, info: Info[Context, None]) -> list[ClockodoUserType]:
        """Fetch available users from the time tracking provider."""
        from apps.contracts.services.time_tracking import get_provider

        user = require_perm(info, "contracts", "read")
        if not user.tenant:
            return []
        provider = get_provider(user.tenant)
        if not provider:
            return []
        try:
            users = provider.get_users()
        except NotImplementedError:
            return []
        return [ClockodoUserType(id=u["id"], name=u["name"]) for u in users]

    @strawberry.field
    def user_cost_profiles(self, info: Info[Context, None]) -> list[UserCostProfileType]:
        """Get all user cost profiles for the current tenant."""
        user = require_perm(info, "contracts", "read")
        if not user.tenant:
            return []
        return [
            UserCostProfileType(
                id=strawberry.ID(str(p.id)),
                external_user_id=p.external_user_id,
                external_user_name=p.external_user_name,
                fte_percentage=p.fte_percentage,
                monthly_income=float(p.monthly_income),
                default_department_id=strawberry.ID(str(p.default_department_id)) if p.default_department_id else None,
            )
            for p in UserCostProfile.objects.filter(tenant=user.tenant)
        ]

    @strawberry.field
    def department_service_mappings(
        self, info: Info[Context, None]
    ) -> list[DepartmentServiceMappingType]:
        """Get all department-service mappings for the current tenant."""
        user = require_perm(info, "contracts", "read")
        if not user.tenant:
            return []
        return [
            DepartmentServiceMappingType(
                id=strawberry.ID(str(m.id)),
                external_service_id=m.external_service_id,
                external_service_name=m.external_service_name,
                department_id=strawberry.ID(str(m.department_id)),
            )
            for m in DepartmentServiceMapping.objects.filter(tenant=user.tenant)
        ]

    @strawberry.field
    def department_time_analysis(
        self,
        info: Info[Context, None],
        date_from: date,
        date_to: date,
    ) -> DepartmentTimeAnalysisType:
        """Compute department time analysis from provider data."""
        from collections import defaultdict
        from django.core.cache import cache
        from apps.contracts.services.time_tracking import get_provider

        user = require_perm(info, "department_analysis", "read")
        if not user.tenant:
            return DepartmentTimeAnalysisType(distribution=[], user_matrix=[], total_hours=0)

        provider = get_provider(user.tenant)
        if not provider:
            return DepartmentTimeAnalysisType(distribution=[], user_matrix=[], total_hours=0)

        # Fetch raw user × service data (cached for 1 hour)
        _sentinel = object()
        cache_key = f"dept_time_{user.tenant_id}_{date_from}_{date_to}"
        raw_data = cache.get(cache_key, _sentinel)
        if raw_data is _sentinel:
            try:
                raw_data = provider.get_department_time_data(date_from, date_to)
            except NotImplementedError:
                return DepartmentTimeAnalysisType(distribution=[], user_matrix=[], total_hours=0)
            cache.set(cache_key, raw_data, 3600)

        if not raw_data:
            return DepartmentTimeAnalysisType(distribution=[], user_matrix=[], total_hours=0)

        # Fetch absences (cached per year)
        user_absence_days: dict[str, float] = defaultdict(float)
        user_sick_days: dict[str, float] = defaultdict(float)
        user_sick_certificate_days: dict[str, float] = defaultdict(float)
        user_sick_child_days: dict[str, float] = defaultdict(float)
        try:
            period_start = date.fromisoformat(date_from) if isinstance(date_from, str) else date_from
            period_end = date.fromisoformat(date_to) if isinstance(date_to, str) else date_to
            years = set(range(period_start.year, period_end.year + 1))
            all_absences: list[dict] = []
            for yr in years:
                abs_cache_key = f"absences_{user.tenant_id}_{yr}"
                cached_abs = cache.get(abs_cache_key, _sentinel)
                if cached_abs is _sentinel:
                    try:
                        cached_abs = provider.get_absences(yr)
                    except NotImplementedError:
                        cached_abs = []
                    cache.set(abs_cache_key, cached_abs, 3600)
                all_absences.extend(cached_abs)

            for ab in all_absences:
                # status: 0=enquired, 1=approved, 2=declined, 3=approval cancelled, 4=request cancelled
                if ab.get("status") in (2, 3, 4):
                    continue
                # Skip home office (type=8) and work out of office (type=9)
                if ab.get("type") in (8, 9):
                    continue

                ab_start_str = ab.get("date_since", "")[:10]
                ab_end_str = ab.get("date_until", "")[:10]
                if not ab_start_str or not ab_end_str:
                    continue

                ab_start = date.fromisoformat(ab_start_str)
                ab_end = date.fromisoformat(ab_end_str)

                # Check overlap with the requested period
                if ab_end < period_start or ab_start > period_end:
                    continue

                total_days = ab.get("count_days", 0) or 0
                if total_days <= 0:
                    continue

                # If the absence fully falls within the period, use count_days directly
                if ab_start >= period_start and ab_end <= period_end:
                    counted_days = total_days
                else:
                    # Partial overlap: pro-rate based on calendar days
                    absence_span = (ab_end - ab_start).days + 1
                    overlap_start = max(ab_start, period_start)
                    overlap_end = min(ab_end, period_end)
                    overlap_days = (overlap_end - overlap_start).days + 1
                    if absence_span > 0:
                        counted_days = total_days * (overlap_days / absence_span)
                    else:
                        counted_days = 0

                if counted_days <= 0:
                    continue

                uid = ab["user_id"]
                user_absence_days[uid] += counted_days

                # Categorize sick-related absences for sub-totals
                try:
                    normalized = provider.normalize_absence_type(ab.get("type", 0))
                except Exception:
                    normalized = "other"
                if normalized == "sick":
                    user_sick_days[uid] += counted_days
                elif normalized == "sick_certificate":
                    user_sick_certificate_days[uid] += counted_days
                elif normalized == "sick_child":
                    user_sick_child_days[uid] += counted_days
        except Exception:
            pass  # Absences are optional, don't fail the whole analysis

        # Load service→department mappings
        mappings = DepartmentServiceMapping.objects.filter(
            tenant=user.tenant
        ).select_related("department")
        service_to_dept: dict[str, str] = {}
        for m in mappings:
            service_to_dept[m.external_service_id] = m.department.name

        # Aggregate by department
        dept_hours: dict[str, float] = defaultdict(float)
        # Aggregate by user × department
        user_dept_hours: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
        total_hours = 0.0

        unassigned_label = "Unassigned"

        # Build per-user logged hours lookup (keyed by external_user_id)
        user_id_to_name: dict[str, str] = {}
        user_logged_hours: dict[str, float] = defaultdict(float)

        for entry in raw_data:
            dept_name = service_to_dept.get(entry["service_id"], unassigned_label)
            hours = entry["hours"]
            dept_hours[dept_name] += hours
            user_dept_hours[entry["user_name"]][dept_name] += hours
            total_hours += hours
            # Track user_id → name mapping and total logged hours
            if entry.get("user_id"):
                user_id_to_name[entry["user_id"]] = entry["user_name"]
                user_logged_hours[entry["user_id"]] += hours

        # Snapshot unfilled data before backfilling
        unfilled_dept_hours: dict[str, float] = dict(dept_hours)
        unfilled_user_dept_hours: dict[str, dict[str, float]] = {
            u: dict(depts) for u, depts in user_dept_hours.items()
        }
        unfilled_total_hours = total_hours

        # Hour backfilling from UserCostProfile
        cost_profiles = list(
            UserCostProfile.objects.filter(tenant=user.tenant).select_related("default_department")
        )
        profile_by_user_id: dict[str, "UserCostProfile"] = {
            p.external_user_id: p for p in cost_profiles
        }

        has_backfill = False
        for profile in cost_profiles:
            if not profile.default_department:
                continue
            target_hours = 168.0 * profile.fte_percentage / 100.0
            logged = user_logged_hours.get(profile.external_user_id, 0.0)
            if logged < target_hours:
                backfill = target_hours - logged
                dept_name = profile.default_department.name
                user_name = user_id_to_name.get(profile.external_user_id, profile.external_user_name)
                dept_hours[dept_name] += backfill
                user_dept_hours[user_name][dept_name] += backfill
                total_hours += backfill
                # Update logged hours for cost computation
                user_logged_hours[profile.external_user_id] = target_hours
                has_backfill = True

        # Build distributions (unfilled = raw logged, filled = after backfill)
        all_depts = sorted(dept_hours.keys())

        distribution = []
        for dept_name in all_depts:
            h = round(unfilled_dept_hours.get(dept_name, 0), 2)
            pct = round((h / unfilled_total_hours * 100) if unfilled_total_hours > 0 else 0, 1)
            distribution.append(DepartmentTimeEntry(department_name=dept_name, hours=h, percentage=pct))

        distribution_filled = None
        if has_backfill:
            distribution_filled = []
            for dept_name in all_depts:
                h = round(dept_hours[dept_name], 2)
                pct = round((h / total_hours * 100) if total_hours > 0 else 0, 1)
                distribution_filled.append(DepartmentTimeEntry(department_name=dept_name, hours=h, percentage=pct))

        # Build reverse lookup: user_name → user_id for absence days
        # Include users from absences even if they have no time entries
        try:
            for u in provider.get_users():
                uid = str(u["id"])
                uname = u.get("name", "")
                if uid not in user_id_to_name and uname:
                    user_id_to_name[uid] = uname
        except Exception:
            pass
        name_to_user_id: dict[str, str] = {v: k for k, v in user_id_to_name.items()}

        def _get_absence_days(user_name: str) -> float | None:
            uid = name_to_user_id.get(user_name)
            if uid and uid in user_absence_days:
                return round(user_absence_days[uid], 1)
            return None

        def _get_sick_breakdown(user_name: str) -> tuple[float | None, float | None, float | None]:
            uid = name_to_user_id.get(user_name)
            if not uid:
                return (None, None, None)
            sick = round(user_sick_days[uid], 1) if uid in user_sick_days else None
            cert = round(user_sick_certificate_days[uid], 1) if uid in user_sick_certificate_days else None
            child = round(user_sick_child_days[uid], 1) if uid in user_sick_child_days else None
            return (sick, cert, child)

        # Unfilled matrix (raw hours)
        all_unfilled_users = sorted(set(list(unfilled_user_dept_hours.keys()) + list(user_dept_hours.keys())))
        user_matrix = []
        for user_name in all_unfilled_users:
            user_total = sum(unfilled_user_dept_hours.get(user_name, {}).values())
            dept_entries = []
            for dept_name in all_depts:
                h = round(unfilled_user_dept_hours.get(user_name, {}).get(dept_name, 0), 2)
                pct = round((h / user_total * 100) if user_total > 0 else 0, 1)
                dept_entries.append(UserDepartmentHours(department_name=dept_name, hours=h, percentage=pct))
            sick, cert, child = _get_sick_breakdown(user_name)
            user_matrix.append(UserDepartmentRow(
                user_name=user_name,
                departments=dept_entries,
                total_hours=round(user_total, 2),
                absence_days=_get_absence_days(user_name),
                sick_days=sick,
                sick_certificate_days=cert,
                sick_child_days=child,
            ))

        # Filled matrix (after backfill) — only if backfilling actually occurred
        user_matrix_filled = None
        if has_backfill:
            user_matrix_filled = []
            for user_name in sorted(user_dept_hours.keys()):
                user_total = sum(user_dept_hours[user_name].values())
                dept_entries = []
                for dept_name in all_depts:
                    h = round(user_dept_hours[user_name].get(dept_name, 0), 2)
                    pct = round((h / user_total * 100) if user_total > 0 else 0, 1)
                    dept_entries.append(UserDepartmentHours(department_name=dept_name, hours=h, percentage=pct))
                sick, cert, child = _get_sick_breakdown(user_name)
                user_matrix_filled.append(UserDepartmentRow(
                    user_name=user_name,
                    departments=dept_entries,
                    total_hours=round(user_total, 2),
                    absence_days=_get_absence_days(user_name),
                    sick_days=sick,
                    sick_certificate_days=cert,
                    sick_child_days=child,
                ))

        # Cost computation
        cost_distribution_list = None
        total_cost_value = None

        dept_cost: dict[str, float] = defaultdict(float)
        dept_ftes: dict[str, float] = defaultdict(float)
        total_cost = 0.0
        has_cost_data = False

        for profile in cost_profiles:
            if float(profile.monthly_income) <= 0:
                continue
            target_hours = 168.0 * profile.fte_percentage / 100.0
            if target_hours <= 0:
                continue
            hourly_cost = float(profile.monthly_income) / target_hours
            user_fte = profile.fte_percentage / 100.0
            user_name = user_id_to_name.get(profile.external_user_id, profile.external_user_name)
            user_depts = user_dept_hours.get(user_name, {})
            user_total = sum(user_depts.values())
            for d_name, d_hours in user_depts.items():
                cost = hourly_cost * d_hours
                dept_cost[d_name] += cost
                total_cost += cost
                # FTE allocation: proportional to hours in this department
                if user_total > 0:
                    dept_ftes[d_name] += user_fte * (d_hours / user_total)
            has_cost_data = True

        if has_cost_data and total_cost > 0:
            cost_distribution_list = []
            for dept_name in sorted(dept_cost.keys()):
                c = round(dept_cost[dept_name], 2)
                pct = round((c / total_cost * 100) if total_cost > 0 else 0, 1)
                ftes = round(dept_ftes.get(dept_name, 0), 2)
                cost_distribution_list.append(DepartmentCostEntry(department_name=dept_name, cost=c, percentage=pct, ftes=ftes))
            total_cost_value = round(total_cost, 2)

        return DepartmentTimeAnalysisType(
            distribution=distribution,
            distribution_filled=distribution_filled,
            user_matrix=user_matrix,
            user_matrix_filled=user_matrix_filled,
            total_hours=round(unfilled_total_hours, 2),
            total_hours_filled=round(total_hours, 2) if has_backfill else None,
            cost_distribution=cost_distribution_list,
            total_cost=total_cost_value,
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

        # Projects are one-off deliverable items only.
        qs = ContractItem.objects.filter(
            tenant=user.tenant,
            delivery_status__isnull=False,
            is_one_off=True,
        ).select_related("contract", "contract__customer", "product")

        if status:
            qs = qs.filter(delivery_status=status)

        if customer_id:
            qs = qs.filter(contract__customer_id=customer_id)

        from django.db.models import Count, Sum

        qs = qs.annotate(dep_count=Count("dependent_items"))
        items = list(qs.order_by("-contract__created_at"))

        # Booked hours per item, summed from Clockodo time-tracking mappings.
        item_ids = [item.id for item in items]
        hours_by_item = {
            row["contract_item_id"]: row["total"] or 0
            for row in TimeTrackingProjectMapping.objects.filter(
                tenant=user.tenant,
                contract_item_id__in=item_ids,
            )
            .values("contract_item_id")
            .annotate(total=Sum("cached_total_hours"))
        }
        ps_rate = float((user.tenant.settings or {}).get("ps_hourly_rate", 160.0))

        result = []
        for item in items:
            hours = float(hours_by_item.get(item.id, 0) or 0)
            order_value = float(item.total_price_raw)
            ps_ratio = (
                order_value / (hours * ps_rate)
                if hours > 0 and ps_rate > 0
                else None
            )
            result.append(
                DeliverableItemType(
                    id=item.id,
                    product_name=item.product.name if item.product else None,
                    description=item.description,
                    is_one_off=item.is_one_off,
                    delivery_status=item.delivery_status,
                    delivered_at=item.delivered_at,
                    estimated_delivery_date=item.estimated_delivery_date,
                    invoice_independent=item.invoice_independent,
                    contract_id=item.contract_id,
                    contract_name=item.contract.name or "",
                    customer_name=item.contract.customer.name,
                    customer_id=item.contract.customer_id,
                    dependent_items_count=item.dep_count,
                    hours_booked=hours,
                    order_value=order_value,
                    order_confirmation_number=item.order_confirmation_number,
                    ps_ratio=ps_ratio,
                )
            )
        return result

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

    @strawberry.field
    def revenue_goals(
        self,
        info: Info[Context, None],
        year: int,
    ) -> list[RevenueGoalType]:
        """Get revenue goals for a given year."""
        user = require_perm(info, "contracts", "read")
        if not user.tenant:
            return []

        goals = RevenueGoal.objects.filter(tenant=user.tenant, year=year)
        return [
            RevenueGoalType(
                id=g.id,
                year=g.year,
                revenue_type=g.revenue_type,
                target_amount=g.target_amount,
            )
            for g in goals
        ]

    @strawberry.field
    def revenue_by_stream(
        self,
        info: Info[Context, None],
        year: int,
    ) -> list[RevenueStreamDataType]:
        """Get revenue data broken down by revenue stream for a given year."""
        user = require_perm(info, "contracts", "read")
        if not user.tenant:
            return []

        stream_data = calculate_revenue_by_stream(user.tenant, year)
        return [
            RevenueStreamDataType(
                revenue_type=s["revenue_type"],
                ytd_actual=s["ytd_actual"],
                full_year_forecast=s["full_year_forecast"],
            )
            for s in stream_data
        ]

    @strawberry.field
    def unclassified_revenue_items(
        self,
        info: Info[Context, None],
    ) -> list[UnclassifiedItemType]:
        """Get contract items from active contracts that have no effective revenue type."""
        user = require_perm(info, "contracts", "read")
        if not user.tenant:
            return []

        current_year_start = date.today().replace(month=1, day=1)
        items = ContractItem.objects.filter(
            tenant=user.tenant,
            contract__status=Contract.Status.ACTIVE,
        ).exclude(
            contract__end_date__lt=current_year_start,
        ).select_related("product", "contract", "contract__customer")

        result = []
        for item in items:
            if item.unit_price == 0:
                continue
            if item.get_effective_revenue_type() is None:
                result.append(UnclassifiedItemType(
                    item_id=item.id,
                    product_name=item.product.name if item.product else None,
                    description=item.description or "",
                    is_one_off=item.is_one_off,
                    unit_price=item.unit_price,
                    quantity=item.quantity,
                    contract_id=item.contract_id,
                    contract_name=item.contract.name or f"Contract {item.contract_id}",
                    customer_name=item.contract.customer.name,
                    customer_id=item.contract.customer_id,
                ))
        return result

    @strawberry.field
    def absence_report(
        self,
        info: Info[Context, None],
        year: int,
        month: int,
    ) -> AbsenceReportType | None:
        """Get an existing absence report for the given month."""
        user = require_perm(info, "department_analysis", "read")
        if not user.tenant:
            return None

        from apps.contracts.models import AbsenceReport
        report = AbsenceReport.objects.filter(
            tenant=user.tenant, year=year, month=month,
        ).prefetch_related("entries").first()

        if not report:
            return None

        return AbsenceReportType(
            id=report.id,
            year=report.year,
            month=report.month,
            status=report.status,
            finalized_at=report.finalized_at,
            entries=[
                AbsenceReportEntryType(
                    id=e.id,
                    user_name=e.user_name,
                    external_user_id=e.external_user_id,
                    absence_type=e.absence_type,
                    date_from=e.date_from,
                    date_to=e.date_to,
                    days_count=e.days_count,
                )
                for e in report.entries.all()
            ],
        )

    @strawberry.field
    def new_business_goals(
        self, info: Info[Context, None], year: int
    ) -> list[NewBusinessGoalGQLType]:
        user = require_perm(info, "contracts", "read")
        if not user.tenant:
            return []
        goals = NewBusinessGoal.objects.filter(tenant=user.tenant, year=year)
        return [
            NewBusinessGoalGQLType(
                id=g.id,
                year=g.year,
                goal_type=g.goal_type,
                target_amount=g.target_amount,
            )
            for g in goals
        ]

    @strawberry.field
    def new_business_metrics(
        self, info: Info[Context, None], year: int
    ) -> NewBusinessMetricsType:
        user = require_perm(info, "contracts", "read")
        if not user.tenant:
            return NewBusinessMetricsType(
                won_new_arr=Decimal("0"),
                back_to_base_arr=Decimal("0"),
                won_development_revenue=Decimal("0"),
                won_deal_count=0,
            )
        metrics = calculate_new_business_metrics(user.tenant, year)
        return NewBusinessMetricsType(
            won_new_arr=metrics["won_new_arr"],
            back_to_base_arr=metrics["won_b2b_arr"],
            won_development_revenue=metrics["won_development_revenue"],
            won_deal_count=metrics["won_deal_count"],
        )

    @strawberry.field
    def won_deals(
        self, info: Info[Context, None], year: int
    ) -> list[WonDealType]:
        user = require_perm(info, "contracts", "read")
        if not user.tenant:
            return []

        won_contracts = Contract.objects.filter(
            tenant=user.tenant,
            hubspot_deal_id__isnull=False,
            deal_won_date__year=year,
            status=Contract.Status.ACTIVE,
        ).exclude(
            hubspot_deal_id=""
        ).select_related("customer").prefetch_related("items")

        result = []
        for contract in won_contracts.order_by("-deal_won_date"):
            # Calculate ARR for this contract
            arr = Decimal("0")
            multipliers = {
                "monthly": 12, "quarterly": 4, "semi_annual": 2,
                "annual": 1, "biennial": Decimal("0.5"),
            }
            for item in contract.items.all():
                if not item.is_one_off:
                    period = item.price_period or "monthly"
                    arr += item.unit_price * item.quantity * multipliers.get(period, 12)

            result.append(WonDealType(
                contract_id=contract.id,
                contract_name=contract.name or f"Contract {contract.id}",
                customer_name=contract.customer.name,
                deal_won_date=str(contract.deal_won_date),
                annual_recurring_revenue=arr,
            ))
        return result

    @strawberry.field
    def new_business_details(
        self, info: Info[Context, None], year: int, metric_type: str
    ) -> list[NewBusinessDetailItem]:
        """Return line-item-level breakdown for a specific new business metric."""
        from apps.core.models import RevenueType
        from apps.contracts.models import calculate_arr_value

        user = require_perm(info, "contracts", "read")
        if not user.tenant:
            return []

        existing_customers = _customers_with_prior_year_revenue(user.tenant, year)
        result: list[NewBusinessDetailItem] = []

        # --- Won deals ---
        won_contracts = Contract.objects.filter(
            tenant=user.tenant,
            hubspot_deal_id__isnull=False,
            deal_won_date__year=year,
            status=Contract.Status.ACTIVE,
        ).exclude(
            hubspot_deal_id=""
        ).select_related("customer").prefetch_related("items", "items__product")

        for contract in won_contracts:
            is_existing = contract.customer_id in existing_customers
            cname = contract.customer.name if contract.customer else "—"
            con_name = contract.name or f"Contract {contract.id}"

            if metric_type == "new_deal_count":
                result.append(NewBusinessDetailItem(
                    customer_id=contract.customer_id or 0,
                    customer_name=cname,
                    contract_id=contract.id,
                    contract_name=con_name,
                    value=Decimal("0"),
                    source="won_deal",
                ))
                continue

            for item in contract.items.all():
                ert = item.get_effective_revenue_type()
                face_value = item.unit_price * item.quantity
                item_desc = item.product.name if item.product else (item.description or "—")

                if item.is_one_off:
                    if metric_type == "new_development" and ert in (
                        RevenueType.ADVANCED_DEVELOPMENT, RevenueType.TRAINING_IMPLEMENTATION
                    ):
                        result.append(NewBusinessDetailItem(
                            customer_id=contract.customer_id or 0,
                            customer_name=cname,
                            contract_id=contract.id,
                            contract_name=con_name,
                            item_id=item.id,
                            item_description=item_desc,
                            value=face_value,
                            source="won_deal",
                        ))
                else:
                    annualized = face_value * _ARR_MULTIPLIERS.get(item.price_period or "monthly", 12)
                    if ert in (RevenueType.ADVANCED_DEVELOPMENT, RevenueType.TRAINING_IMPLEMENTATION):
                        if metric_type == "new_development":
                            result.append(NewBusinessDetailItem(
                                customer_id=contract.customer_id or 0,
                                customer_name=cname,
                                contract_id=contract.id,
                                contract_name=con_name,
                                item_id=item.id,
                                item_description=item_desc,
                                value=annualized,
                                source="won_deal",
                            ))
                    elif metric_type == "new_arr" and not is_existing:
                        result.append(NewBusinessDetailItem(
                            customer_id=contract.customer_id or 0,
                            customer_name=cname,
                            contract_id=contract.id,
                            contract_name=con_name,
                            item_id=item.id,
                            item_description=item_desc,
                            value=annualized,
                            source="won_deal",
                        ))
                    elif metric_type == "back_to_base_arr" and is_existing:
                        result.append(NewBusinessDetailItem(
                            customer_id=contract.customer_id or 0,
                            customer_name=cname,
                            contract_id=contract.id,
                            contract_name=con_name,
                            item_id=item.id,
                            item_description=item_desc,
                            value=annualized,
                            source="won_deal",
                        ))

        # --- Expansion items ---
        if metric_type in ("back_to_base_arr", "new_development"):
            won_contract_ids = set(won_contracts.values_list("id", flat=True))
            expansion_items = ContractItem.objects.filter(
                tenant=user.tenant,
                contract__status__in=[Contract.Status.ACTIVE, Contract.Status.PAUSED],
                deal_won_date__year=year,
            ).exclude(
                contract_id__in=won_contract_ids,
            ).select_related("contract", "contract__customer", "product")

            for item in expansion_items:
                ert = item.get_effective_revenue_type()
                contract = item.contract
                item_desc = item.product.name if item.product else (item.description or "—")

                if item.is_one_off:
                    # One-off expansion → new_development
                    if metric_type == "new_development" and ert in (RevenueType.ADVANCED_DEVELOPMENT, RevenueType.TRAINING_IMPLEMENTATION):
                        result.append(NewBusinessDetailItem(
                            customer_id=contract.customer_id or 0,
                            customer_name=contract.customer.name if contract.customer else "—",
                            contract_id=contract.id,
                            contract_name=contract.name or f"Contract {contract.id}",
                            item_id=item.id,
                            item_description=item_desc,
                            value=item.unit_price * item.quantity,
                            source="expansion",
                        ))
                else:
                    # Recurring expansion → back_to_base_arr
                    if metric_type == "back_to_base_arr":
                        arr = calculate_arr_value(
                            item.unit_price, item.quantity, item.price_period, False,
                        )
                        if arr > 0:
                            result.append(NewBusinessDetailItem(
                                customer_id=contract.customer_id or 0,
                                customer_name=contract.customer.name if contract.customer else "—",
                                contract_id=contract.id,
                                contract_name=contract.name or f"Contract {contract.id}",
                                item_id=item.id,
                                item_description=item_desc,
                                value=arr,
                                source="expansion",
                            ))

        # --- Negotiated price increases (B2B only) ---
        if metric_type == "back_to_base_arr":
            from apps.contracts.models import ContractItemPrice

            jan1 = date(year, 1, 1)
            price_increase_contracts = Contract.objects.filter(
                tenant=user.tenant,
                status__in=[Contract.Status.ACTIVE, Contract.Status.PAUSED],
                start_date__lt=jan1,
            ).filter(
                Q(end_date__isnull=True) | Q(end_date__gte=jan1)
            ).select_related("customer").prefetch_related("items__price_periods", "items__product")

            for contract in price_increase_contracts:
                for item in contract.items.all():
                    if item.is_one_off:
                        continue
                    pps = list(item.price_periods.all())
                    for pp in pps:
                        if pp.valid_from.year != year or pp.increase_type != "negotiated":
                            continue
                        day_before = pp.valid_from - timedelta(days=1)
                        prev_m = item.get_price_at_cached(day_before, pps, normalize_to_monthly=True)
                        new_m = item.get_price_at_cached(pp.valid_from, pps, normalize_to_monthly=True)
                        if new_m > prev_m:
                            delta = (new_m - prev_m) * item.quantity * 12
                            result.append(NewBusinessDetailItem(
                                customer_id=contract.customer_id or 0,
                                customer_name=contract.customer.name if contract.customer else "—",
                                contract_id=contract.id,
                                contract_name=contract.name or f"Contract {contract.id}",
                                item_id=item.id,
                                item_description=item.product.name if item.product else (item.description or "—"),
                                value=delta,
                                source="price_increase",
                            ))

        return result


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
    def generate_absence_report(
        self,
        info: Info[Context, None],
        year: int,
        month: int,
    ) -> AbsenceReportType:
        """Generate or regenerate a draft absence report."""
        user = require_perm(info, "department_analysis", "regenerate")
        from apps.contracts.models import AbsenceReport as AbsenceReportModel
        from apps.contracts.services.absence_report import AbsenceReportService

        existing = AbsenceReportModel.objects.filter(
            tenant=user.tenant, year=year, month=month
        ).first()
        allow_reset = existing and existing.status == AbsenceReportModel.Status.FINALIZED

        service = AbsenceReportService(user.tenant)
        report = service.generate_report(year, month, allow_reset_finalized=allow_reset)
        report.refresh_from_db()

        return AbsenceReportType(
            id=report.id,
            year=report.year,
            month=report.month,
            status=report.status,
            finalized_at=report.finalized_at,
            entries=[
                AbsenceReportEntryType(
                    id=e.id,
                    user_name=e.user_name,
                    external_user_id=e.external_user_id,
                    absence_type=e.absence_type,
                    date_from=e.date_from,
                    date_to=e.date_to,
                    days_count=e.days_count,
                )
                for e in report.entries.all()
            ],
        )

    @strawberry.mutation
    def finalize_absence_report(
        self,
        info: Info[Context, None],
        report_id: strawberry.ID,
    ) -> AbsenceReportType:
        """Finalize a draft absence report."""
        user = require_perm(info, "department_analysis", "finalize")
        from apps.contracts.services.absence_report import AbsenceReportService

        service = AbsenceReportService(user.tenant)
        report = service.finalize_report(int(report_id), user)

        return AbsenceReportType(
            id=report.id,
            year=report.year,
            month=report.month,
            status=report.status,
            finalized_at=report.finalized_at,
            entries=[
                AbsenceReportEntryType(
                    id=e.id,
                    user_name=e.user_name,
                    external_user_id=e.external_user_id,
                    absence_type=e.absence_type,
                    date_from=e.date_from,
                    date_to=e.date_to,
                    days_count=e.days_count,
                )
                for e in report.entries.all()
            ],
        )

    @strawberry.mutation
    def send_absence_report(
        self,
        info: Info[Context, None],
        report_id: strawberry.ID,
        recipients: list[str],
    ) -> bool:
        """Send a finalized absence report via email."""
        user = require_perm(info, "department_analysis", "send")
        from apps.contracts.services.absence_report import AbsenceReportService

        service = AbsenceReportService(user.tenant)
        return service.send_report(int(report_id), recipients)

    @strawberry.mutation
    def provision_clockodo_projects(
        self,
        info: Info[Context, None],
        contract_id: strawberry.ID,
        create_maintenance: bool = True,
        oneoff_strategy: str = "combined",
        selected_oneoff_item_ids: list[int] | None = None,
    ) -> ProvisioningResult:
        """Create Clockodo projects for a contract."""
        from apps.contracts.services.clockodo_provisioning import provision_projects

        user, err = check_perm(info, "contracts", "write")
        if err:
            return ProvisioningResult(success=False, created_projects=[], errors=[err])

        try:
            contract = Contract.objects.select_related("customer", "tenant").prefetch_related("items").get(
                id=contract_id, tenant=user.tenant
            )
        except Contract.DoesNotExist:
            return ProvisioningResult(success=False, created_projects=[], errors=["Contract not found"])

        result = provision_projects(
            contract,
            create_maintenance=create_maintenance,
            oneoff_strategy=oneoff_strategy,
            selected_oneoff_item_ids=selected_oneoff_item_ids,
        )

        return ProvisioningResult(
            success=result["success"],
            created_projects=[
                ProvisioningProjectResult(name=p["name"], action=p["action"])
                for p in result["created_projects"]
            ],
            errors=result["errors"],
        )

    @strawberry.mutation
    def save_time_tracking_project_templates(
        self,
        info: Info[Context, None],
        maintenance_template: str | None = None,
        oneoff_template: str | None = None,
    ) -> OperationResult:
        """Save Clockodo project naming templates."""
        user, err = check_perm(info, "settings", "write")
        if err:
            return OperationResult(success=False, error=err)
        if not user.tenant:
            return OperationResult(success=False, error="No tenant assigned")

        config = user.tenant.time_tracking_config or {}
        if maintenance_template is not None:
            config["maintenance_project_template"] = maintenance_template
        if oneoff_template is not None:
            config["oneoff_project_template"] = oneoff_template
        user.tenant.time_tracking_config = config
        user.tenant.save(update_fields=["time_tracking_config"])

        return OperationResult(success=True)

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
                offer_number=input.offer_number,
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
                payment_term_days=input.payment_term_days,
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
            if input.offer_number is not None:
                contract.offer_number = input.offer_number
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
            if input.payment_term_days is not UNSET:
                contract.payment_term_days = input.payment_term_days
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
            if input.deal_won_date is not UNSET:
                contract.deal_won_date = input.deal_won_date

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
                    invoice_independent=input.invoice_independent if input.delivery_tracking else False,
                    depends_on=depends_on_item,
                    revenue_type=input.revenue_type,
                    deal_won_date=input.deal_won_date,
                )

                # Create amendment record only for non-draft contracts
                if contract.status != Contract.Status.DRAFT:
                    item_name = product.name if product else input.description[:50]
                    arr_delta = calculate_arr_value(
                        input.unit_price, input.quantity,
                        input.price_period, input.is_one_off,
                    )
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
                            "price_period": input.price_period,
                            "is_one_off": input.is_one_off,
                        },
                        arr_delta=arr_delta,
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
                    invoice_independent=item.invoice_independent,
                    depends_on=None,
                    dependent_items=[],
                    price_periods=[],  # Newly created items have no price periods
                    revenue_type=item.revenue_type,
                    effective_revenue_type=item.get_effective_revenue_type(),
                    source_hubspot_deal_id=item.source_hubspot_deal_id,
                    deal_won_date=item.deal_won_date,
                    **_moved_fields(item),
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
                    "price_period": item.price_period,
                    "is_one_off": item.is_one_off,
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
                    if is_price_locked and input.unit_price != item.unit_price:
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
                    if input.billing_end_date is not None:
                        # Prevent ending billing within an already-invoiced period
                        from apps.invoices.models import InvoiceRecord

                        max_period_end = None
                        for record in item.contract.invoice_records.exclude(
                            status=InvoiceRecord.Status.VOIDED
                        ).only("line_items_snapshot", "period_end"):
                            for line in record.line_items_snapshot or []:
                                if line.get("item_id") == item.id:
                                    if max_period_end is None or record.period_end > max_period_end:
                                        max_period_end = record.period_end
                                    break
                        if max_period_end and input.billing_end_date < max_period_end:
                            return ContractItemResult(
                                error=f"Billing end date cannot be before {max_period_end.isoformat()} — this item is invoiced until that date."
                            )
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
                        item.invoice_independent = False
                if input.invoice_independent is not None:
                    # Only meaningful on items with delivery tracking enabled
                    if item.delivery_status:
                        item.invoice_independent = input.invoice_independent
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

                if input.revenue_type is not UNSET:
                    item.revenue_type = input.revenue_type
                if input.deal_won_date is not UNSET:
                    item.deal_won_date = input.deal_won_date

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

                        old_arr = calculate_arr_value(
                            old_values["unit_price"], old_values["quantity"],
                            old_values["price_period"], old_values["is_one_off"],
                        )
                        new_arr = calculate_arr_value(
                            item.unit_price, item.quantity,
                            item.price_period, item.is_one_off,
                        )
                        arr_delta = new_arr - old_arr

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
                            arr_delta=arr_delta,
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
                    increase_type=pp.increase_type,
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
                    invoice_independent=item.invoice_independent,
                    depends_on=None,
                    dependent_items=[],
                    price_periods=price_periods,
                    revenue_type=item.revenue_type,
                    effective_revenue_type=item.get_effective_revenue_type(),
                    source_hubspot_deal_id=item.source_hubspot_deal_id,
                    deal_won_date=item.deal_won_date,
                    **_moved_fields(item),
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

        # Guard: prevent deleting items that appear in non-voided invoices
        from apps.invoices.models import InvoiceRecord

        for record in item.contract.invoice_records.exclude(
            status=InvoiceRecord.Status.VOIDED
        ).only("line_items_snapshot"):
            for line in record.line_items_snapshot or []:
                if line.get("item_id") == item.id:
                    return DeleteResult(
                        error="Cannot delete an invoiced item. Set a billing end date instead."
                    )

        try:
            with transaction.atomic():
                # Create amendment record only for non-draft contracts
                if item.contract.status != Contract.Status.DRAFT:
                    item_name = item.product.name if item.product else (item.description or "")[:50]
                    arr_delta = -calculate_arr_value(
                        item.unit_price, item.quantity,
                        item.price_period, item.is_one_off,
                    )
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
                            "price_period": item.price_period,
                            "is_one_off": item.is_one_off,
                        },
                        arr_delta=arr_delta,
                    )

                item.delete()

            return DeleteResult(success=True)
        except Exception as e:
            return DeleteResult(error=str(e))

    @strawberry.mutation
    def move_contract_item(
        self, info: Info[Context, None], input: MoveContractItemInput
    ) -> MoveContractItemResult:
        """Move a line item from one contract to another of the same customer."""
        from apps.contracts.services.contract_item_move import execute_move, validate_move

        user, err = check_perm(info, "contracts", "write")
        if err:
            return MoveContractItemResult(error=err)
        if not user.tenant:
            return MoveContractItemResult(error="No tenant assigned")

        item = ContractItem.objects.filter(
            tenant=user.tenant, id=input.item_id
        ).select_related("contract__customer", "product").first()
        if not item:
            return MoveContractItemResult(error="Item not found")

        target = Contract.objects.filter(
            tenant=user.tenant, id=input.target_contract_id
        ).select_related("customer").first()
        if not target:
            return MoveContractItemResult(error="Target contract not found")

        errors = validate_move(item, target, input.effective_date)
        if errors:
            return MoveContractItemResult(error=errors[0])

        try:
            source_item, new_item = execute_move(item, target, input.effective_date)
            # Re-fetch with relations for response
            source_item = ContractItem.objects.select_related(
                "product", "contract", "moved_to", "moved_to__contract",
            ).get(pk=source_item.pk)
            new_item = ContractItem.objects.select_related(
                "product", "contract",
            ).get(pk=new_item.pk)
            today = date.today()
            s_eff, s_ep = source_item.get_effective_price_info(today)
            n_eff, n_ep = new_item.get_effective_price_info(today)
            return MoveContractItemResult(
                success=True,
                source_item=ContractItemType(
                    id=source_item.id, quantity=source_item.quantity,
                    unit_price=source_item.unit_price, price_period=source_item.price_period,
                    price_source=source_item.price_source, total_price=source_item.total_price,
                    effective_price=s_eff, effective_price_period=s_ep,
                    product=source_item.product, description=source_item.description,
                    billing_end_date=source_item.billing_end_date,
                    is_one_off=False, **_moved_fields(source_item),
                ),
                new_item=ContractItemType(
                    id=new_item.id, quantity=new_item.quantity,
                    unit_price=new_item.unit_price, price_period=new_item.price_period,
                    price_source=new_item.price_source, total_price=new_item.total_price,
                    effective_price=n_eff, effective_price_period=n_ep,
                    product=new_item.product, description=new_item.description,
                    billing_start_date=new_item.billing_start_date,
                    is_one_off=False, **_moved_fields(new_item),
                ),
            )
        except Exception as e:
            return MoveContractItemResult(error=str(e))

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
                    arr_delta=Decimal("0"),
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
                    arr_delta=Decimal("0"),
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
        activation_options: ActivationOptionsInput | None = None,
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
            Contract.Status.CANCELLED: [Contract.Status.ENDED, Contract.Status.ACTIVE],
            Contract.Status.ENDED: [Contract.Status.DRAFT, Contract.Status.ACTIVE],
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
                        arr_delta=Decimal("0"),
                    )

            # Post-activation: create order confirmation if requested
            if (
                old_status == Contract.Status.DRAFT
                and new_status == Contract.Status.ACTIVE
            ):
                create_ab = False
                send_ab = False
                if activation_options is not None:
                    if activation_options.create_order_confirmation_only:
                        create_ab = True
                    elif activation_options.send_order_confirmation:
                        create_ab = True
                        send_ab = True
                else:
                    create_ab = True
                    send_ab = True

                if create_ab:
                    try:
                        from apps.contracts.services.order_confirmation import OrderConfirmationService
                        from django.conf import settings as django_settings

                        request = info.context.request
                        origin = request.headers.get("Origin") or request.headers.get("Referer", "").rstrip("/")
                        base_url = origin or getattr(django_settings, "FRONTEND_URL", "")

                        service = OrderConfirmationService(user.tenant)
                        ab = service.create_order_confirmation(
                            contract=contract,
                            user=user,
                        )
                        # Set contract OC number and create link
                        OrderConfirmationService.link_to_contract(ab, user, base_url)

                        if send_ab:
                            from apps.contracts.tasks import send_order_confirmation_email_task
                            send_order_confirmation_email_task.delay(ab.id, user_id=user.id)
                    except Exception:
                        # AB creation failure should not block activation
                        import logging
                        logging.getLogger(__name__).exception(
                            "Failed to create order confirmation for contract %s", contract.id
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
        """Move a contract to a different customer."""
        user, err = check_perm(info, "contracts", "write")
        if err:
            return ContractResult(error=err)
        if not user.tenant:
            return ContractResult(error="No tenant assigned")

        contract = Contract.objects.select_related("customer").filter(
            tenant=user.tenant, id=contract_id
        ).first()
        if not contract:
            return ContractResult(error="Contract not found")

        customer = Customer.objects.filter(
            tenant=user.tenant, id=customer_id
        ).first()
        if not customer:
            return ContractResult(error="Customer not found")

        if contract.customer_id == customer.id:
            return ContractResult(error="Contract already belongs to this customer")

        old_customer_name = contract.customer.name if contract.customer else "—"
        contract.customer = customer
        contract.group = None
        contract.save(update_fields=["customer", "group", "updated_at"])

        if contract.status != Contract.Status.DRAFT:
            ContractAmendment.objects.create(
                tenant=user.tenant,
                contract=contract,
                effective_date=date.today(),
                type=ContractAmendment.AmendmentType.TERMS_CHANGED,
                description=f"Moved from {old_customer_name} to {customer.name}",
                changes={
                    "customer": {"old": old_customer_name, "new": customer.name},
                },
            )

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
                increase_type=input.increase_type,
            )
            return ContractItemPriceResult(
                price_period=ContractItemPriceType(
                    id=price_period_record.id,
                    valid_from=price_period_record.valid_from,
                    valid_to=price_period_record.valid_to,
                    unit_price=price_period_record.unit_price,
                    price_period=price_period_record.price_period,
                    source=price_period_record.source,
                    increase_type=price_period_record.increase_type,
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
            if input.increase_type is not None:
                price_period.increase_type = input.increase_type
            price_period.save()

            return ContractItemPriceResult(
                price_period=ContractItemPriceType(
                    id=price_period.id,
                    valid_from=price_period.valid_from,
                    valid_to=price_period.valid_to,
                    unit_price=price_period.unit_price,
                    price_period=price_period.price_period,
                    source=price_period.source,
                    increase_type=price_period.increase_type,
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
                category=input.category,
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
                    category=attachment.category,
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

    @strawberry.mutation
    def update_contract_attachment_meta(
        self,
        info: Info[Context, None],
        input: UpdateAttachmentMetaInput,
    ) -> AttachmentResult:
        """Update category and/or description on an existing attachment."""
        user, err = check_perm(info, "contracts", "write")
        if err:
            return AttachmentResult(error=err)
        if not user.tenant:
            return AttachmentResult(error="No tenant assigned")

        attachment = ContractAttachment.objects.filter(
            tenant=user.tenant, id=input.attachment_id
        ).select_related("uploaded_by").first()
        if not attachment:
            return AttachmentResult(error="Attachment not found")

        if input.category is not None:
            attachment.category = input.category
        if input.description is not None:
            attachment.description = input.description
        attachment.save()

        return AttachmentResult(
            attachment=ContractAttachmentType(
                id=attachment.id,
                original_filename=attachment.original_filename,
                file_size=attachment.file_size,
                content_type=attachment.content_type,
                description=attachment.description,
                category=attachment.category,
                uploaded_at=attachment.created_at,
                uploaded_by_name=attachment.uploaded_by.email if attachment.uploaded_by else None,
                download_url=f"/api/attachments/{attachment.id}/download/",
            ),
            success=True,
        )

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

        # Check if already mapped — surface where, so user can fix/unmap.
        existing = (
            TimeTrackingProjectMapping.objects
            .filter(tenant=user.tenant, external_project_id=external_project_id)
            .select_related("contract", "contract_item", "contract_item__product")
            .first()
        )
        if existing:
            existing_contract = existing.contract
            existing_item = existing.contract_item
            item_name = None
            if existing_item:
                item_name = (
                    existing_item.product.name if existing_item.product
                    else (existing_item.description[:50] if existing_item.description else f"Item {existing_item.id}")
                )
            contract_name = existing_contract.name or f"#{existing_contract.id}"
            error_msg = (
                f"Project is already linked to contract '{contract_name}'"
                + (f" (item: {item_name})" if item_name else "")
            )
            return TimeTrackingMappingResult(
                success=False,
                error=error_msg,
                conflict_contract_id=existing_contract.id,
                conflict_contract_name=contract_name,
                conflict_item_name=item_name,
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
    def update_time_tracking_mapping_item(
        self,
        info: Info[Context, None],
        mapping_id: strawberry.ID,
        contract_item_id: strawberry.ID | None = None,
    ) -> TimeTrackingMappingResult:
        """Assign or change the contract item for an existing project mapping.

        Pass contract_item_id=null to clear the assignment.
        """
        user, err = check_perm(info, "contracts", "write")
        if err:
            return TimeTrackingMappingResult(success=False, error=err)
        if not user.tenant:
            return TimeTrackingMappingResult(success=False, error="No tenant assigned")

        mapping = (
            TimeTrackingProjectMapping.objects
            .filter(tenant=user.tenant, id=mapping_id)
            .select_related("contract", "contract_item", "contract_item__product")
            .first()
        )
        if not mapping:
            return TimeTrackingMappingResult(success=False, error="Mapping not found")

        contract_item = None
        if contract_item_id:
            contract_item = ContractItem.objects.filter(
                contract=mapping.contract, id=contract_item_id
            ).first()
            if not contract_item:
                return TimeTrackingMappingResult(
                    success=False, error="Item not found in this contract"
                )

        mapping.contract_item = contract_item
        mapping.save(update_fields=["contract_item", "updated_at"])

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
    def create_clockodo_project_for_contract(
        self,
        info: Info[Context, None],
        contract_id: strawberry.ID,
        project_name: str,
        contract_item_id: strawberry.ID | None = None,
    ) -> TimeTrackingMappingResult:
        """Create a new Clockodo project and map it to a contract."""
        from apps.contracts.services.time_tracking import get_provider

        user, err = check_perm(info, "contracts", "write")
        if err:
            return TimeTrackingMappingResult(success=False, error=err)
        if not user.tenant:
            return TimeTrackingMappingResult(success=False, error="No tenant assigned")

        contract = Contract.objects.select_related("customer").filter(
            tenant=user.tenant, id=contract_id
        ).first()
        if not contract:
            return TimeTrackingMappingResult(success=False, error="Contract not found")

        customer = contract.customer
        if not customer.clockodo_customer_id:
            return TimeTrackingMappingResult(
                success=False, error="Customer is not linked to Clockodo"
            )

        # If a maintenance mapping already exists, require a contract item
        has_maintenance = TimeTrackingProjectMapping.objects.filter(
            tenant=user.tenant,
            contract=contract,
            contract_item__isnull=True,
        ).exists()
        if has_maintenance and not contract_item_id:
            return TimeTrackingMappingResult(
                success=False,
                error="A maintenance project already exists. New projects must be linked to a line item.",
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

        provider = get_provider(user.tenant)
        if not provider:
            return TimeTrackingMappingResult(
                success=False, error="No time tracking provider configured"
            )

        try:
            result = provider.create_project(
                customer.clockodo_customer_id, project_name.strip()
            )
        except Exception as e:
            return TimeTrackingMappingResult(
                success=False, error=f"Failed to create Clockodo project: {e}"
            )

        mapping = TimeTrackingProjectMapping.objects.create(
            tenant=user.tenant,
            contract=contract,
            contract_item=contract_item,
            external_project_id=result["id"],
            external_project_name=result["name"],
            external_customer_name=customer.name,
            link_source=TimeTrackingProjectMapping.LinkSource.MANUAL,
        )

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
    def create_auto_link_rule(
        self,
        info: Info[Context, None],
        contract_id: strawberry.ID,
        pattern: str,
        match_type: str = "contains",
        contract_item_id: strawberry.ID | None = None,
    ) -> DeleteResult:
        """Create an auto-link rule for time tracking projects."""
        user, err = check_perm(info, "contracts", "write")
        if err:
            return DeleteResult(error=err)
        if not user.tenant:
            return DeleteResult(error="No tenant assigned")

        contract = Contract.objects.filter(
            tenant=user.tenant, id=contract_id
        ).first()
        if not contract:
            return DeleteResult(error="Contract not found")

        if match_type not in ("contains", "starts_with"):
            return DeleteResult(error="Invalid match type")

        if not pattern.strip():
            return DeleteResult(error="Pattern cannot be empty")

        contract_item = None
        if contract_item_id:
            contract_item = ContractItem.objects.filter(
                contract=contract, id=contract_item_id
            ).first()
            if not contract_item:
                return DeleteResult(error="Item not found in this contract")

        rule = AutoLinkRule.objects.create(
            tenant=user.tenant,
            contract=contract,
            contract_item=contract_item,
            pattern=pattern.strip(),
            match_type=match_type,
        )

        # Apply rule asynchronously so projects get linked without waiting for
        # the daily task, and without blocking the GraphQL request on a slow
        # Clockodo API call. Dispatch after the current transaction commits so
        # the worker can always find the rule row.
        from apps.contracts.tasks import apply_auto_link_rule_task
        transaction.on_commit(lambda: apply_auto_link_rule_task.delay(rule.id))

        return DeleteResult(success=True)

    @strawberry.mutation
    def delete_auto_link_rule(
        self,
        info: Info[Context, None],
        rule_id: strawberry.ID,
    ) -> DeleteResult:
        """Delete an auto-link rule. Existing mappings created by it remain."""
        user, err = check_perm(info, "contracts", "write")
        if err:
            return DeleteResult(error=err)
        if not user.tenant:
            return DeleteResult(error="No tenant assigned")

        rule = AutoLinkRule.objects.filter(
            tenant=user.tenant, id=rule_id
        ).first()
        if not rule:
            return DeleteResult(error="Rule not found")

        rule.delete()
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

    @strawberry.mutation
    def merge_contract(
        self,
        info: Info[Context, None],
        input: MergeContractInput,
    ) -> MergeContractResult:
        """Merge a source contract's items into a target contract."""
        from apps.contracts.services.contract_merge import execute_merge

        user, err = check_perm(info, "contracts", "write")
        if err:
            return MergeContractResult(errors=[err])

        try:
            source = Contract.objects.select_related("customer", "tenant").prefetch_related(
                "items__product", "time_tracking_mappings"
            ).get(id=input.source_contract_id, tenant=user.tenant)
            target = Contract.objects.select_related("customer", "tenant").get(
                id=input.target_contract_id, tenant=user.tenant
            )
        except Contract.DoesNotExist:
            return MergeContractResult(errors=["Contract not found"])

        # Build item_overrides dict
        item_overrides = {}
        if input.item_overrides:
            for override in input.item_overrides:
                overrides = {}
                if override.start_date is not None:
                    overrides["start_date"] = override.start_date
                if override.billing_start_date is not None:
                    overrides["billing_start_date"] = override.billing_start_date
                if overrides:
                    item_overrides[override.item_id] = overrides

        try:
            items_count = source.items.count()
            updated_target = execute_merge(
                source, target, item_overrides=item_overrides, user=user
            )
            return MergeContractResult(
                contract=updated_target,
                success=True,
                items_transferred=items_count,
            )
        except ValueError as e:
            return MergeContractResult(errors=str(e).split("; "))


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
                            old_arr = calculate_arr_value(
                                old_item_values["unit_price"], old_item_values["quantity"],
                                old_item_values["price_period"], old_item_values["is_one_off"],
                            )
                            new_arr = calculate_arr_value(
                                item_input.unit_price, item_input.quantity,
                                item_input.price_period, item_input.is_one_off,
                            )
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
                                arr_delta=new_arr - old_arr,
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
                                arr_delta=calculate_arr_value(
                                    item_input.unit_price, item_input.quantity,
                                    item_input.price_period, item_input.is_one_off,
                                ),
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
                            increase_type=input.increase_type,
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
                    # Compute total ARR delta from changed items
                    items_by_id = {item.id: item for item in items}
                    bulk_arr_delta = Decimal("0")
                    for d in details:
                        if not d.skipped:
                            itm = items_by_id.get(d.item_id)
                            if itm:
                                old_arr = calculate_arr_value(d.old_price, itm.quantity, itm.price_period, False)
                                new_arr = calculate_arr_value(d.new_price, itm.quantity, itm.price_period, False)
                                bulk_arr_delta += new_arr - old_arr

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
                            "increase_type": input.increase_type,
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
                        arr_delta=bulk_arr_delta,
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

    @strawberry.mutation
    def set_revenue_goal(
        self,
        info: Info[Context, None],
        year: int,
        revenue_type: str,
        target_amount: Decimal,
    ) -> RevenueGoalResult:
        """Create or update a revenue goal for a year and revenue type."""
        user, err = check_perm(info, "settings", "write")
        if err:
            return RevenueGoalResult(error=err)
        if not user.tenant:
            return RevenueGoalResult(error="No tenant assigned")

        from apps.core.models import RevenueType
        valid_types = [c[0] for c in RevenueType.choices]
        if revenue_type not in valid_types:
            return RevenueGoalResult(
                error=f"Invalid revenue type. Must be one of: {', '.join(valid_types)}"
            )

        goal, _ = RevenueGoal.objects.update_or_create(
            tenant=user.tenant,
            year=year,
            revenue_type=revenue_type,
            defaults={"target_amount": target_amount},
        )

        return RevenueGoalResult(
            goal=RevenueGoalType(
                id=goal.id,
                year=goal.year,
                revenue_type=goal.revenue_type,
                target_amount=goal.target_amount,
            ),
            success=True,
        )

    @strawberry.mutation
    def delete_revenue_goal(
        self,
        info: Info[Context, None],
        year: int,
        revenue_type: str,
    ) -> DeleteResult:
        """Delete a revenue goal."""
        user, err = check_perm(info, "settings", "write")
        if err:
            return DeleteResult(error=err)
        if not user.tenant:
            return DeleteResult(error="No tenant assigned")

        deleted, _ = RevenueGoal.objects.filter(
            tenant=user.tenant,
            year=year,
            revenue_type=revenue_type,
        ).delete()

        if deleted == 0:
            return DeleteResult(error="Revenue goal not found")
        return DeleteResult(success=True)

    @strawberry.mutation
    def set_new_business_goal(
        self,
        info: Info[Context, None],
        year: int,
        goal_type: str,
        target_amount: Decimal,
    ) -> NewBusinessGoalResult:
        """Set or update a new business goal (upsert)."""
        user, err = check_perm(info, "settings", "write")
        if err:
            return NewBusinessGoalResult(error=err)
        if not user.tenant:
            return NewBusinessGoalResult(error="No tenant assigned")

        from .models import NewBusinessGoalType as NBGType
        valid_types = [c[0] for c in NBGType.choices]
        if goal_type not in valid_types:
            return NewBusinessGoalResult(
                error=f"Invalid goal type. Must be one of: {', '.join(valid_types)}"
            )

        goal, _ = NewBusinessGoal.objects.update_or_create(
            tenant=user.tenant,
            year=year,
            goal_type=goal_type,
            defaults={"target_amount": target_amount},
        )
        return NewBusinessGoalResult(
            goal=NewBusinessGoalGQLType(
                id=goal.id,
                year=goal.year,
                goal_type=goal.goal_type,
                target_amount=goal.target_amount,
            ),
            success=True,
        )

    @strawberry.mutation
    def delete_new_business_goal(
        self,
        info: Info[Context, None],
        year: int,
        goal_type: str,
    ) -> DeleteResult:
        """Delete a new business goal."""
        user, err = check_perm(info, "settings", "write")
        if err:
            return DeleteResult(error=err)
        if not user.tenant:
            return DeleteResult(error="No tenant assigned")

        deleted, _ = NewBusinessGoal.objects.filter(
            tenant=user.tenant,
            year=year,
            goal_type=goal_type,
        ).delete()

        if deleted == 0:
            return DeleteResult(error="New business goal not found")
        return DeleteResult(success=True)

    # -----------------------------------------------------------------
    # Department CRUD Mutations
    # -----------------------------------------------------------------

    @strawberry.mutation
    def create_department(
        self, info: Info[Context, None], name: str
    ) -> DeleteResult:
        """Create a new department."""
        user, err = check_perm(info, "settings", "write")
        if err:
            return DeleteResult(error=err)
        if not user.tenant:
            return DeleteResult(error="No tenant assigned")

        name = name.strip()
        if not name:
            return DeleteResult(error="Name is required")

        if Department.objects.filter(tenant=user.tenant, name=name).exists():
            return DeleteResult(error="A department with this name already exists")

        max_order = Department.objects.filter(tenant=user.tenant).count()
        Department.objects.create(tenant=user.tenant, name=name, sort_order=max_order)
        return DeleteResult(success=True)

    @strawberry.mutation
    def update_department(
        self,
        info: Info[Context, None],
        id: strawberry.ID,
        name: str,
        cost_center_id: Optional[strawberry.ID] = UNSET,
    ) -> DeleteResult:
        """Update a department (name and/or cost center)."""
        user, err = check_perm(info, "settings", "write")
        if err:
            return DeleteResult(error=err)
        if not user.tenant:
            return DeleteResult(error="No tenant assigned")

        name = name.strip()
        if not name:
            return DeleteResult(error="Name is required")

        dept = Department.objects.filter(tenant=user.tenant, id=id).first()
        if not dept:
            return DeleteResult(error="Department not found")

        if Department.objects.filter(tenant=user.tenant, name=name).exclude(id=id).exists():
            return DeleteResult(error="A department with this name already exists")

        update_fields = ["name", "updated_at"]
        dept.name = name

        if cost_center_id is not UNSET:
            if cost_center_id is None:
                dept.cost_center = None
            else:
                from apps.banking.models import CostCenter

                cc = CostCenter.objects.filter(tenant=user.tenant, id=cost_center_id).first()
                if not cc:
                    return DeleteResult(error="Cost center not found")
                dept.cost_center = cc
            update_fields.append("cost_center_id")

        dept.save(update_fields=update_fields)
        return DeleteResult(success=True)

    @strawberry.mutation
    def delete_department(
        self, info: Info[Context, None], id: strawberry.ID
    ) -> DeleteResult:
        """Delete a department (cascades service mappings)."""
        user, err = check_perm(info, "settings", "write")
        if err:
            return DeleteResult(error=err)
        if not user.tenant:
            return DeleteResult(error="No tenant assigned")

        dept = Department.objects.filter(tenant=user.tenant, id=id).first()
        if not dept:
            return DeleteResult(error="Department not found")

        dept.delete()
        return DeleteResult(success=True)

    @strawberry.mutation
    def save_department_service_mappings(
        self,
        info: Info[Context, None],
        mappings: list[DepartmentServiceMappingInput],
    ) -> DeleteResult:
        """Bulk replace all department-service mappings for the tenant."""
        user, err = check_perm(info, "settings", "write")
        if err:
            return DeleteResult(error=err)
        if not user.tenant:
            return DeleteResult(error="No tenant assigned")

        # Validate all department IDs belong to tenant
        dept_ids = {m.department_id for m in mappings}
        valid_dept_ids = set(
            Department.objects.filter(
                tenant=user.tenant, id__in=dept_ids
            ).values_list("id", flat=True)
        )
        invalid = dept_ids - {str(d) for d in valid_dept_ids}
        if invalid:
            return DeleteResult(error="Invalid department ID(s)")

        with transaction.atomic():
            DepartmentServiceMapping.objects.filter(tenant=user.tenant).delete()
            for m in mappings:
                DepartmentServiceMapping.objects.create(
                    tenant=user.tenant,
                    department_id=int(m.department_id),
                    external_service_id=m.external_service_id,
                    external_service_name=m.external_service_name,
                )

        return DeleteResult(success=True)

    @strawberry.mutation
    def save_user_cost_profiles(
        self,
        info: Info[Context, None],
        profiles: list[UserCostProfileInput],
    ) -> DeleteResult:
        """Bulk replace all user cost profiles for the tenant."""
        user, err = check_perm(info, "settings", "write")
        if err:
            return DeleteResult(error=err)
        if not user.tenant:
            return DeleteResult(error="No tenant assigned")

        # Validate department IDs
        dept_ids = {p.default_department_id for p in profiles if p.default_department_id}
        if dept_ids:
            valid_dept_ids = set(
                Department.objects.filter(
                    tenant=user.tenant, id__in=dept_ids
                ).values_list("id", flat=True)
            )
            invalid = dept_ids - {str(d) for d in valid_dept_ids}
            if invalid:
                return DeleteResult(error="Invalid department ID(s)")

        with transaction.atomic():
            UserCostProfile.objects.filter(tenant=user.tenant).delete()
            for p in profiles:
                UserCostProfile.objects.create(
                    tenant=user.tenant,
                    external_user_id=p.external_user_id,
                    external_user_name=p.external_user_name,
                    fte_percentage=p.fte_percentage,
                    monthly_income=p.monthly_income,
                    default_department_id=int(p.default_department_id) if p.default_department_id else None,
                )

        return DeleteResult(success=True)
