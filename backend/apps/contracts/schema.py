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
from .models import Contract, ContractItem, ContractAmendment, ContractItemPrice, ContractAttachment, ContractLink, TimeTrackingProjectMapping
from .services import ExcelParser, ImportService, MatchStatus

if TYPE_CHECKING:
    from apps.todos.schema import TodoItemType


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
        items = ContractItem.objects.filter(contract=self).select_related("product", "contract").prefetch_related("price_periods")
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
        """Calculate total contract value based on duration + one-off items."""
        from datetime import date
        today = date.today()

        # Get items and calculate monthly-normalized totals
        items = ContractItem.objects.filter(contract=self)

        monthly_recurring = Decimal("0")
        one_off_total = Decimal("0")

        for item in items:
            if item.is_one_off:
                # One-off items use effective price × quantity
                effective_price, period = item.get_effective_price_info(today)
                one_off_total += effective_price * item.quantity
            else:
                # Recurring items use effective price (monthly-normalized)
                monthly_unit_price = item.get_price_at(today, normalize_to_monthly=True)
                monthly_recurring += monthly_unit_price * item.quantity

        # Total value based on contract duration
        duration_months = self.get_duration_months()
        return (monthly_recurring * duration_months) + one_off_total

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
        """Calculate Annual Recurring Revenue (monthly × 12)."""
        from datetime import date
        today = date.today()

        items = ContractItem.objects.filter(contract=self, is_one_off=False)
        monthly_total = Decimal("0")
        for item in items:
            # Use effective price considering period-specific pricing
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


@strawberry.input
class UpdateContractItemInput:
    id: strawberry.ID
    product_id: strawberry.ID | None = None
    description: str | None = None
    quantity: int | None = None
    unit_price: Decimal | None = None
    price_period: str | None = None  # Period the price refers to (monthly, quarterly, annual, etc.)
    price_source: str | None = None
    start_date: date | None = None
    billing_start_date: date | None = None
    billing_end_date: date | None = None
    align_to_contract_at: date | None = None
    is_one_off: bool | None = None
    order_confirmation_number: str | None = None
    price_locked: bool | None = None
    price_locked_until: date | None = None


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
class BillingEvent:
    """A billing event on a specific date."""

    date: date
    items: List[BillingScheduleItem]
    total: Decimal


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

    # Get all active contracts for this tenant
    active_contracts = Contract.objects.filter(
        tenant=tenant,
        status=Contract.Status.ACTIVE,
    ).prefetch_related("items", "items__price_periods")

    total_active_contracts = active_contracts.count()
    total_contract_value = Decimal("0")
    annual_recurring_revenue = Decimal("0")
    year_to_date_revenue = Decimal("0")
    current_year_forecast = Decimal("0")
    next_year_forecast = Decimal("0")

    for contract in active_contracts:
        # TCV: monthly value × duration months
        items = contract.items.all()
        monthly_value = Decimal("0")
        for item in items:
            if not item.is_one_off:
                monthly_unit_price = item.get_price_at(today, normalize_to_monthly=True)
                monthly_value += monthly_unit_price * item.quantity

        duration_months = contract.get_duration_months()
        total_contract_value += monthly_value * duration_months

        # Add one-off items to TCV
        for item in items:
            if item.is_one_off:
                effective_price, _ = item.get_effective_price_info(today)
                total_contract_value += effective_price * item.quantity

        # ARR: annualized recurring revenue (monthly × 12)
        annual_recurring_revenue += monthly_value * 12

        # YTD Revenue: use recognition schedule from Jan 1 to today
        ytd_schedule = contract.get_recognition_schedule(
            from_date=current_year_start,
            to_date=today,
            include_history=True,
        )
        for event in ytd_schedule:
            year_to_date_revenue += event["total"]

        # Current Year Forecast: Jan 1 to Dec 31
        current_year_schedule = contract.get_recognition_schedule(
            from_date=current_year_start,
            to_date=current_year_end,
            include_history=True,
        )
        for event in current_year_schedule:
            current_year_forecast += event["total"]

        # Next Year Forecast: Jan 1 to Dec 31 of next year
        # Only include contracts that will still be active next year
        contract_end = contract.end_date or contract.get_effective_end_date()
        if not contract_end or contract_end >= next_year_start:
            next_year_schedule = contract.get_recognition_schedule(
                from_date=next_year_start,
                to_date=next_year_end,
                include_history=True,
            )
            for event in next_year_schedule:
                next_year_forecast += event["total"]

    return {
        "total_active_contracts": total_active_contracts,
        "total_contract_value": total_contract_value,
        "annual_recurring_revenue": annual_recurring_revenue,
        "year_to_date_revenue": year_to_date_revenue,
        "current_year_forecast": current_year_forecast,
        "next_year_forecast": next_year_forecast,
    }


@strawberry.type
class DashboardKPIsType:
    """Dashboard KPI metrics for contract portfolio."""

    total_active_contracts: int
    total_contract_value: Decimal
    annual_recurring_revenue: Decimal
    year_to_date_revenue: Decimal
    current_year_forecast: Decimal
    next_year_forecast: Decimal


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
                next_year_forecast=Decimal("0"),
            )

        kpis = calculate_dashboard_kpis(user.tenant)
        return DashboardKPIsType(
            total_active_contracts=kpis["total_active_contracts"],
            total_contract_value=kpis["total_contract_value"],
            annual_recurring_revenue=kpis["annual_recurring_revenue"],
            year_to_date_revenue=kpis["year_to_date_revenue"],
            current_year_forecast=kpis["current_year_forecast"],
            next_year_forecast=kpis["next_year_forecast"],
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
        )

        # Convert to GraphQL types
        events = [
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
            )
            for event in schedule
        ]

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
        ).select_related("customer").prefetch_related("items__product", "items__price_periods")

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
            schedule = contract.get_billing_schedule(
                from_date=from_date,
                to_date=to_date,
                include_history=False,
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

            # Only include contracts with revenue
            if contract_total > 0:
                contract_name = contract.name or f"Vertrag {contract.id}"
                contract_rows.append(
                    ContractRevenueRow(
                        contract_id=contract.id,
                        contract_name=contract_name,
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
        ).select_related("customer").prefetch_related("items__product", "items__price_periods")

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
            # Use get_recognition_schedule instead of get_billing_schedule
            schedule = contract.get_recognition_schedule(
                from_date=from_date,
                to_date=to_date,
                include_history=False,
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

            # Only include contracts with revenue
            if contract_total > 0:
                contract_name = contract.name or f"Vertrag {contract.id}"
                contract_rows.append(
                    ContractRevenueRow(
                        contract_id=contract.id,
                        contract_name=contract_name,
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
            from django.db.models import Q
            queryset = queryset.filter(
                Q(customer__name__icontains=search) |
                Q(name__icontains=search) |
                Q(netsuite_sales_order_number__icontains=search) |
                Q(netsuite_contract_number__icontains=search) |
                Q(po_number__icontains=search)
            )

        # Status filter
        if status:
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
        """Get time tracking summary for a contract's mapped projects."""
        from apps.contracts.services.time_tracking import get_provider

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
        )
        mapping_types = [
            TimeTrackingMappingType(
                id=m.id,
                external_project_id=m.external_project_id,
                external_project_name=m.external_project_name,
                external_customer_name=m.external_customer_name,
                contract_item_id=m.contract_item_id,
            )
            for m in mappings
        ]

        project_ids = [m.external_project_id for m in mappings]
        if not project_ids:
            return TimeTrackingSummaryType(
                total_hours=0,
                total_revenue=0,
                by_service=[],
                by_month=[],
                mappings=mapping_types,
            )

        provider = get_provider(user.tenant)
        if not provider:
            return TimeTrackingSummaryType(
                total_hours=0,
                total_revenue=0,
                by_service=[],
                by_month=[],
                mappings=mapping_types,
            )

        summary = provider.get_time_summary(project_ids)
        return TimeTrackingSummaryType(
            total_hours=summary.total_hours,
            total_revenue=summary.total_revenue,
            by_service=[
                ServiceBreakdown(
                    service_name=s["service_name"],
                    hours=s["hours"],
                    revenue=s["revenue"],
                )
                for s in summary.by_service
            ],
            by_month=[
                MonthlyBreakdown(
                    month=m["month"],
                    hours=m["hours"],
                    revenue=m["revenue"],
                )
                for m in summary.by_month
            ],
            mappings=mapping_types,
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
                if input.start_date is not None:
                    item.start_date = input.start_date
                if input.billing_start_date is not None:
                    item.billing_start_date = input.billing_start_date
                if input.billing_end_date is not None:
                    item.billing_end_date = input.billing_end_date
                if input.align_to_contract_at is not None:
                    item.align_to_contract_at = input.align_to_contract_at
                if input.is_one_off is not None:
                    item.is_one_off = input.is_one_off
                if input.order_confirmation_number is not None:
                    item.order_confirmation_number = input.order_confirmation_number
                if input.price_locked is not None:
                    item.price_locked = input.price_locked
                if input.price_locked_until is not None:
                    item.price_locked_until = input.price_locked_until

                item.save()

                # Create amendment record only for non-draft contracts
                if item.contract.status != Contract.Status.DRAFT:
                    # Determine amendment type
                    item_name = item.product.name if item.product else item.description[:50]
                    if input.product_id is not None and old_values["product_id"] != str(input.product_id):
                        amendment_type = ContractAmendment.AmendmentType.TERMS_CHANGED
                        description = f"Changed product from {old_values['product_name'] or 'none'} to {item_name}"
                    elif input.quantity is not None and old_values["quantity"] != input.quantity:
                        amendment_type = ContractAmendment.AmendmentType.QUANTITY_CHANGED
                        description = f"Changed {item_name} quantity from {old_values['quantity']} to {input.quantity}"
                    elif input.unit_price is not None:
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
                            "new_values": {
                                "quantity": item.quantity,
                                "unit_price": str(item.unit_price),
                                "price_source": item.price_source,
                                "description": item.description,
                                "product_id": str(item.product_id) if item.product_id else None,
                            },
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
        user, err = check_perm(info, "contracts", "delete")
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
                    item_name = item.product.name if item.product else item.description[:50]
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
        - active -> paused, cancelled
        - paused -> active, cancelled
        - cancelled -> ended
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
            Contract.Status.ACTIVE: [Contract.Status.PAUSED, Contract.Status.CANCELLED],
            Contract.Status.PAUSED: [Contract.Status.ACTIVE, Contract.Status.CANCELLED],
            Contract.Status.CANCELLED: [Contract.Status.ENDED],
            Contract.Status.ENDED: [],
        }

        current_status = contract.status
        allowed = allowed_transitions.get(current_status, [])

        if new_status not in allowed:
            return ContractResult(
                error=f"Cannot transition from {current_status} to {new_status}"
            )

        try:
            with transaction.atomic():
                old_status = contract.status
                contract.status = new_status

                # Set timestamps for specific transitions
                if new_status == Contract.Status.CANCELLED:
                    contract.cancelled_at = datetime.now()
                    contract.cancellation_effective_date = date.today()

                contract.save()

                # Create amendment for status change (not for drafts)
                if old_status != Contract.Status.DRAFT:
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
        user, err = check_perm(info, "contracts", "delete")
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
        user, err = check_perm(info, "contracts", "delete")
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
        user, err = check_perm(info, "contracts", "delete")
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

        mapping = TimeTrackingProjectMapping.objects.create(
            tenant=user.tenant,
            contract=contract,
            external_project_id=external_project_id,
            external_project_name=external_project_name,
            external_customer_name=external_customer_name,
        )
        return TimeTrackingMappingResult(
            success=True,
            mapping=TimeTrackingMappingType(
                id=mapping.id,
                external_project_id=mapping.external_project_id,
                external_project_name=mapping.external_project_name,
                external_customer_name=mapping.external_customer_name,
                contract_item_id=mapping.contract_item_id,
            ),
        )

    @strawberry.mutation
    def unmap_time_tracking_project(
        self,
        info: Info[Context, None],
        mapping_id: strawberry.ID,
    ) -> DeleteResult:
        """Remove a time tracking project mapping."""
        user, err = check_perm(info, "contracts", "delete")
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

                        existing_item.product = product
                        existing_item.description = item_input.description
                        existing_item.quantity = item_input.quantity
                        existing_item.unit_price = item_input.unit_price
                        existing_item.price_period = item_input.price_period
                        existing_item.price_source = ContractItem.PriceSource.CUSTOM
                        existing_item.is_one_off = item_input.is_one_off
                        existing_item.save()

                        if contract.status != Contract.Status.DRAFT:
                            item_name = product.name if product else item_input.description[:50]
                            ContractAmendment.objects.create(
                                tenant=user.tenant,
                                contract=contract,
                                effective_date=date.today(),
                                type=ContractAmendment.AmendmentType.PRICE_CHANGE,
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
