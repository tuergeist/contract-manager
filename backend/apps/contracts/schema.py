"""GraphQL schema for contracts."""
from datetime import date, datetime
from decimal import Decimal
from typing import List

import strawberry
from strawberry import auto
import strawberry_django
from strawberry.types import Info
from django.db import transaction
from django.db.models import Sum, F

from apps.core.context import Context
from apps.core.permissions import get_current_user
from apps.customers.models import Customer
from apps.customers.schema import CustomerType
from apps.products.models import Product
from apps.products.schema import ProductType
from .models import Contract, ContractItem, ContractAmendment, ContractItemPrice


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
class ContractItemPriceType:
    """A price period for a contract item."""

    id: int
    valid_from: date
    valid_to: date | None
    unit_price: Decimal
    source: str


@strawberry.type
class ContractItemType:
    """A line item in a contract."""

    id: int
    quantity: int
    unit_price: Decimal
    price_source: str
    total_price: Decimal
    product: ProductType
    # When item becomes effective
    start_date: date | None = None
    # Billing fields
    billing_start_date: date | None = None
    billing_end_date: date | None = None
    align_to_contract_at: date | None = None
    suggested_alignment_date: date | None = None
    is_one_off: bool = False
    # Price lock fields
    price_locked: bool = False
    price_locked_until: date | None = None
    # Year-specific pricing
    price_periods: List[ContractItemPriceType] = strawberry.field(default_factory=list)


@strawberry_django.type(Contract)
class ContractType:
    """A contract with a customer."""

    id: auto
    name: auto
    hubspot_deal_id: auto
    status: auto
    start_date: auto
    end_date: auto
    billing_start_date: auto
    billing_interval: auto
    billing_anchor_day: auto
    min_duration_months: auto
    notice_period_months: auto
    notice_period_anchor: auto
    notice_period_after_min_months: auto
    cancelled_at: auto
    cancellation_effective_date: auto
    created_at: auto
    customer: CustomerType

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
        for item in items:
            # Get price periods for this item
            price_periods = [
                ContractItemPriceType(
                    id=pp.id,
                    valid_from=pp.valid_from,
                    valid_to=pp.valid_to,
                    unit_price=pp.unit_price,
                    source=pp.source,
                )
                for pp in item.price_periods.all()
            ]
            result.append(
                ContractItemType(
                    id=item.id,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    price_source=item.price_source,
                    total_price=item.total_price,
                    product=item.product,
                    start_date=item.start_date,
                    billing_start_date=item.billing_start_date,
                    billing_end_date=item.billing_end_date,
                    align_to_contract_at=item.align_to_contract_at,
                    suggested_alignment_date=item.get_suggested_alignment_date(),
                    is_one_off=item.is_one_off,
                    price_locked=item.price_locked,
                    price_locked_until=item.price_locked_until,
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
    def total_value(self) -> Decimal:
        """Calculate total contract value: ARR + one-off items."""
        # Get monthly recurring value
        recurring = ContractItem.objects.filter(
            contract=self,
            is_one_off=False,
        ).aggregate(
            total=Sum(F("quantity") * F("unit_price"))
        )
        monthly_recurring = recurring["total"] or Decimal("0")

        # Get one-off items total
        one_off = ContractItem.objects.filter(
            contract=self,
            is_one_off=True,
        ).aggregate(
            total=Sum(F("quantity") * F("unit_price"))
        )
        one_off_total = one_off["total"] or Decimal("0")

        # ARR (annual) + one-off
        return (monthly_recurring * 12) + one_off_total

    @strawberry.field
    def monthly_recurring_value(self) -> Decimal:
        """Calculate monthly recurring value (excludes one-off items)."""
        result = ContractItem.objects.filter(
            contract=self,
            is_one_off=False,
        ).aggregate(
            total=Sum(F("quantity") * F("unit_price"))
        )
        return result["total"] or Decimal("0")


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
    start_date: date
    end_date: date | None = None
    billing_start_date: date | None = None
    billing_interval: str = "monthly"
    billing_anchor_day: int = 1
    min_duration_months: int | None = None
    notice_period_months: int = 3
    notice_period_anchor: str = "end_of_duration"
    notice_period_after_min_months: int | None = None


@strawberry.input
class UpdateContractInput:
    id: strawberry.ID
    name: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    billing_start_date: date | None = None
    billing_interval: str | None = None
    billing_anchor_day: int | None = None
    min_duration_months: int | None = None
    notice_period_months: int | None = None
    notice_period_anchor: str | None = None
    notice_period_after_min_months: int | None = None


@strawberry.input
class ContractItemInput:
    product_id: strawberry.ID
    quantity: int
    unit_price: Decimal
    price_source: str = "list"
    start_date: date | None = None
    billing_start_date: date | None = None
    align_to_contract_at: date | None = None
    is_one_off: bool = False


@strawberry.input
class UpdateContractItemInput:
    id: strawberry.ID
    quantity: int | None = None
    unit_price: Decimal | None = None
    price_source: str | None = None
    start_date: date | None = None
    billing_start_date: date | None = None
    billing_end_date: date | None = None
    align_to_contract_at: date | None = None
    is_one_off: bool | None = None
    price_locked: bool | None = None
    price_locked_until: date | None = None


@strawberry.input
class ContractItemPriceInput:
    """Input for creating/updating a price period."""
    valid_from: date
    valid_to: date | None = None
    unit_price: Decimal
    source: str = "fixed"


@strawberry.input
class UpdateContractItemPriceInput:
    """Input for updating a price period."""
    id: strawberry.ID
    valid_from: date | None = None
    valid_to: date | None = None
    unit_price: Decimal | None = None
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
class DeleteResult:
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


@strawberry.type
class ContractQuery:
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
        user = get_current_user(info)
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
    ) -> BillingScheduleResult:
        """
        Calculate the billing schedule for a contract.

        Args:
            contract_id: The contract to calculate for
            months: Number of months to forecast (default: 13)
            include_history: Include past billing periods (default: False)
        """
        from dateutil.relativedelta import relativedelta

        user = get_current_user(info)
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
        from_date = contract.billing_start_date if include_history else today
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

        user = get_current_user(info)
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

        # Start from beginning of current period to include all billing events in this period
        if is_quarterly:
            # Start of current quarter
            current_quarter_month = ((today.month - 1) // 3) * 3 + 1
            from_date = date(today.year, current_quarter_month, 1)
            num_quarters = quarters if quarters is not None else 6
            to_date = today + relativedelta(months=num_quarters * 3)
        else:
            # Start of current month
            from_date = date(today.year, today.month, 1)
            num_months = months if months is not None else 13
            to_date = today + relativedelta(months=num_months)

        # Generate period columns
        period_columns = []
        period_column_set = set()
        if is_quarterly:
            # Start from current quarter
            current_quarter = (today.month - 1) // 3 + 1
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
            current = date(today.year, today.month, 1)
            while current <= to_date:
                key = current.strftime("%Y-%m")
                period_columns.append(key)
                period_column_set.add(key)
                current += relativedelta(months=1)

        # Get all active/paused contracts
        contracts = Contract.objects.filter(
            tenant=user.tenant,
            status__in=[Contract.Status.ACTIVE, Contract.Status.PAUSED, Contract.Status.DRAFT],
        ).select_related("customer")

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
    def contracts(
        self,
        info: Info[Context, None],
        search: str | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str | None = "created_at",
        sort_order: str | None = "desc",
    ) -> ContractConnection:
        """Get paginated list of contracts with filtering and sorting."""
        user = get_current_user(info)
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

        # Search filter (by customer name)
        if search:
            queryset = queryset.filter(customer__name__icontains=search)

        # Status filter
        if status:
            queryset = queryset.filter(status=status)

        # Sorting
        allowed_sort_fields = {
            "created_at",
            "start_date",
            "end_date",
            "status",
            "customer_name",
        }
        if sort_by == "customer_name":
            order_field = "-customer__name" if sort_order == "desc" else "customer__name"
        elif sort_by and sort_by in allowed_sort_fields:
            order_field = f"-{sort_by}" if sort_order == "desc" else sort_by
        else:
            order_field = "-created_at"
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
        user = get_current_user(info)
        if user.tenant:
            return Contract.objects.filter(tenant=user.tenant, id=id).first()
        return None


@strawberry.type
class ContractMutation:
    @strawberry.mutation
    def create_contract(
        self, info: Info[Context, None], input: CreateContractInput
    ) -> ContractResult:
        """Create a new contract."""
        user = get_current_user(info)
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
                status=Contract.Status.DRAFT,
                start_date=input.start_date,
                end_date=input.end_date,
                billing_start_date=input.billing_start_date or input.start_date,
                billing_interval=input.billing_interval,
                billing_anchor_day=input.billing_anchor_day,
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
        user = get_current_user(info)
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
            # Start date and billing start date can only be changed for draft contracts
            if input.start_date is not None:
                if contract.status != Contract.Status.DRAFT:
                    return ContractResult(error="Start date can only be changed for draft contracts")
                contract.start_date = input.start_date
            if input.billing_start_date is not None:
                if contract.status != Contract.Status.DRAFT:
                    return ContractResult(error="Billing start date can only be changed for draft contracts")
                contract.billing_start_date = input.billing_start_date
            if input.end_date is not None:
                contract.end_date = input.end_date
            if input.billing_interval is not None:
                contract.billing_interval = input.billing_interval
            if input.billing_anchor_day is not None:
                contract.billing_anchor_day = input.billing_anchor_day
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
        user = get_current_user(info)
        if not user.tenant:
            return ContractItemResult(error="No tenant assigned")

        contract = Contract.objects.filter(
            tenant=user.tenant, id=contract_id
        ).first()
        if not contract:
            return ContractItemResult(error="Contract not found")

        product = Product.objects.filter(
            tenant=user.tenant, id=input.product_id
        ).first()
        if not product:
            return ContractItemResult(error="Product not found")

        try:
            with transaction.atomic():
                item = ContractItem.objects.create(
                    tenant=user.tenant,
                    contract=contract,
                    product=product,
                    quantity=input.quantity,
                    unit_price=input.unit_price,
                    price_source=input.price_source,
                    start_date=input.start_date,
                    billing_start_date=input.billing_start_date,
                    align_to_contract_at=input.align_to_contract_at,
                    is_one_off=input.is_one_off,
                )

                # Create amendment record only for non-draft contracts
                if contract.status != Contract.Status.DRAFT:
                    ContractAmendment.objects.create(
                        tenant=user.tenant,
                        contract=contract,
                        effective_date=date.today(),
                        type=ContractAmendment.AmendmentType.PRODUCT_ADDED,
                        description=f"Added {product.name} x{input.quantity}",
                        changes={
                            "product_id": str(product.id),
                            "product_name": product.name,
                            "quantity": input.quantity,
                            "unit_price": str(input.unit_price),
                        },
                    )

            return ContractItemResult(
                item=ContractItemType(
                    id=item.id,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    price_source=item.price_source,
                    total_price=item.total_price,
                    product=product,
                    start_date=item.start_date,
                    billing_start_date=item.billing_start_date,
                    billing_end_date=item.billing_end_date,
                    align_to_contract_at=item.align_to_contract_at,
                    suggested_alignment_date=item.get_suggested_alignment_date(),
                    is_one_off=item.is_one_off,
                    price_locked=item.price_locked,
                    price_locked_until=item.price_locked_until,
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
        user = get_current_user(info)
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
                }

                # Check if price is locked
                is_price_locked = item.price_locked and (
                    item.price_locked_until is None or item.price_locked_until >= date.today()
                )

                if input.quantity is not None:
                    item.quantity = input.quantity
                if input.unit_price is not None:
                    if is_price_locked:
                        return ContractItemResult(error="Price is locked and cannot be changed")
                    item.unit_price = input.unit_price
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
                if input.price_locked is not None:
                    item.price_locked = input.price_locked
                if input.price_locked_until is not None:
                    item.price_locked_until = input.price_locked_until

                item.save()

                # Create amendment record only for non-draft contracts
                if item.contract.status != Contract.Status.DRAFT:
                    # Determine amendment type
                    if input.quantity is not None and old_values["quantity"] != input.quantity:
                        amendment_type = ContractAmendment.AmendmentType.QUANTITY_CHANGED
                        description = f"Changed {item.product.name} quantity from {old_values['quantity']} to {input.quantity}"
                    elif input.unit_price is not None:
                        amendment_type = ContractAmendment.AmendmentType.PRICE_CHANGED
                        description = f"Changed {item.product.name} price from {old_values['unit_price']} to {input.unit_price}"
                    else:
                        amendment_type = ContractAmendment.AmendmentType.TERMS_CHANGED
                        description = f"Updated {item.product.name}"

                    ContractAmendment.objects.create(
                        tenant=user.tenant,
                        contract=item.contract,
                        effective_date=date.today(),
                        type=amendment_type,
                        description=description,
                        changes={
                            "item_id": str(item.id),
                            "product_name": item.product.name,
                            "old_values": old_values,
                            "new_values": {
                                "quantity": item.quantity,
                                "unit_price": str(item.unit_price),
                                "price_source": item.price_source,
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
                    source=pp.source,
                )
                for pp in item.price_periods.all()
            ]

            return ContractItemResult(
                item=ContractItemType(
                    id=item.id,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    price_source=item.price_source,
                    total_price=item.total_price,
                    product=item.product,
                    start_date=item.start_date,
                    billing_start_date=item.billing_start_date,
                    billing_end_date=item.billing_end_date,
                    align_to_contract_at=item.align_to_contract_at,
                    suggested_alignment_date=item.get_suggested_alignment_date(),
                    is_one_off=item.is_one_off,
                    price_locked=item.price_locked,
                    price_locked_until=item.price_locked_until,
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
        user = get_current_user(info)
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
                    ContractAmendment.objects.create(
                        tenant=user.tenant,
                        contract=item.contract,
                        effective_date=date.today(),
                        type=ContractAmendment.AmendmentType.PRODUCT_REMOVED,
                        description=f"Removed {item.product.name}",
                        changes={
                            "product_id": str(item.product.id),
                            "product_name": item.product.name,
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
        user = get_current_user(info)
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
        user = get_current_user(info)
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
        user = get_current_user(info)
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

        try:
            price_period = ContractItemPrice.objects.create(
                tenant=user.tenant,
                item=item,
                valid_from=input.valid_from,
                valid_to=input.valid_to,
                unit_price=input.unit_price,
                source=input.source,
            )
            return ContractItemPriceResult(
                price_period=ContractItemPriceType(
                    id=price_period.id,
                    valid_from=price_period.valid_from,
                    valid_to=price_period.valid_to,
                    unit_price=price_period.unit_price,
                    source=price_period.source,
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
        user = get_current_user(info)
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

        try:
            if input.valid_from is not None:
                price_period.valid_from = input.valid_from
            if input.valid_to is not None:
                price_period.valid_to = input.valid_to
            if input.unit_price is not None:
                price_period.unit_price = input.unit_price
            if input.source is not None:
                price_period.source = input.source
            price_period.save()

            return ContractItemPriceResult(
                price_period=ContractItemPriceType(
                    id=price_period.id,
                    valid_from=price_period.valid_from,
                    valid_to=price_period.valid_to,
                    unit_price=price_period.unit_price,
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
        user = get_current_user(info)
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
