"""Core GraphQL schema for authentication."""
from typing import Annotated, Union

import strawberry
from django.contrib.auth import authenticate
from django.db.models import Q
from strawberry.types import Info

from apps.core.auth import create_access_token, create_refresh_token, get_user_from_token
from apps.core.context import Context


@strawberry.type
class AuthPayload:
    """Authentication response with tokens."""

    access_token: str
    refresh_token: str
    user_id: int
    email: str
    tenant_id: int | None


@strawberry.type
class AuthError:
    """Authentication error."""

    message: str


AuthResult = Annotated[Union[AuthPayload, AuthError], strawberry.union("AuthResult")]


@strawberry.type
class DeleteResult:
    """Result of delete operations."""

    success: bool = False
    error: str | None = None


import enum


@strawberry.enum
class FeedbackType(enum.Enum):
    """Type of feedback being submitted."""

    BUG = "bug"
    FEATURE = "feature"
    GENERAL = "general"


@strawberry.input
class FeedbackInput:
    """Input for submitting feedback."""

    type: FeedbackType
    title: str
    description: str | None = None
    screenshot: str | None = None  # Base64 encoded
    page_url: str | None = None
    viewport: str | None = None  # e.g., "1920x1080"
    user_agent: str | None = None


@strawberry.type
class FeedbackResult:
    """Result of feedback submission."""

    success: bool = False
    error: str | None = None
    task_url: str | None = None


@strawberry.type
class CurrentUser:
    """Current authenticated user info."""

    id: int
    email: str
    first_name: str
    last_name: str
    tenant_id: int | None
    tenant_name: str | None
    company_name: str | None
    role_name: str | None
    is_admin: bool
    roles: list[str] | None = None
    permissions: list[str] | None = None


@strawberry.type
class SearchResultItem:
    """A single search result item."""

    id: int
    title: str
    subtitle: str | None = None
    url: str


@strawberry.type
class SearchResultGroup:
    """A group of search results by type."""

    type: str
    label: str
    items: list[SearchResultItem]
    has_more: bool = False


@strawberry.type
class GlobalSearchResult:
    """Global search results grouped by type."""

    groups: list[SearchResultGroup]
    total_count: int


@strawberry.type
class CoreQuery:
    """Core queries including auth status."""

    @strawberry.field
    def feedback_enabled(self) -> bool:
        """Check if the selected feedback backend is configured."""
        from apps.core.feedback import get_feedback_service
        return get_feedback_service().is_configured()

    @strawberry.field
    def me(self, info: Info[Context, None]) -> CurrentUser | None:
        """Get current authenticated user."""
        user = info.context.user
        if user is None:
            return None

        role_names = [r.name for r in user.roles.all()]
        permissions = sorted(user.effective_permissions)

        company_name = None
        if user.tenant:
            from apps.invoices.models import CompanyLegalData
            legal = CompanyLegalData.objects.filter(tenant=user.tenant).values_list("company_name", flat=True).first()
            if legal:
                company_name = legal

        return CurrentUser(
            id=user.id,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            tenant_id=user.tenant_id,
            tenant_name=user.tenant.name if user.tenant else None,
            company_name=company_name,
            role_name=user.role.name if user.role else None,
            is_admin=user.is_admin or user.is_super_admin,
            roles=role_names,
            permissions=permissions,
        )

    @strawberry.field
    def global_search(
        self, info: Info[Context, None], query: str, limit: int = 10
    ) -> GlobalSearchResult:
        """Search across customers, contracts, and invoices."""
        from apps.contracts.models import Contract
        from apps.customers.models import Customer
        from apps.invoices.models import InvoiceRecord

        user = info.context.user
        if user is None or not user.tenant:
            return GlobalSearchResult(groups=[], total_count=0)

        query = query.strip()
        if len(query) < 2:
            return GlobalSearchResult(groups=[], total_count=0)

        groups = []
        total_count = 0

        # Search customers (include all, not just active)
        # Order by: customers with CUS ID first, then by name
        # Fetch limit+1 to check if there are more
        from django.db.models import Case, When, Value, IntegerField
        customers = list(Customer.objects.filter(
            tenant=user.tenant,
        ).filter(
            Q(name__icontains=query) |
            Q(netsuite_customer_number__icontains=query)
        ).annotate(
            has_cus_id=Case(
                When(netsuite_customer_number__isnull=False, netsuite_customer_number__gt='', then=Value(0)),
                default=Value(1),
                output_field=IntegerField(),
            )
        ).order_by('has_cus_id', 'name')[:limit + 1])

        customers_has_more = len(customers) > limit
        if customers_has_more:
            customers = customers[:limit]

        if customers:
            customer_items = [
                SearchResultItem(
                    id=c.id,
                    title=c.name,
                    subtitle=c.netsuite_customer_number or None,
                    url=f"/customers/{c.id}",
                )
                for c in customers
            ]
            groups.append(SearchResultGroup(
                type="customer",
                label="Customers",
                items=customer_items,
                has_more=customers_has_more,
            ))
            total_count += len(customer_items)

        # Search contracts
        # Fetch limit+1 to check if there are more
        contracts = list(Contract.objects.filter(
            tenant=user.tenant,
        ).filter(
            Q(name__icontains=query) |
            Q(netsuite_sales_order_number__icontains=query) |
            Q(po_number__icontains=query) |
            Q(order_confirmation_number__icontains=query)
        ).select_related("customer")[:limit + 1])

        contracts_has_more = len(contracts) > limit
        if contracts_has_more:
            contracts = contracts[:limit]

        if contracts:
            contract_items = [
                SearchResultItem(
                    id=c.id,
                    title=c.name,
                    subtitle=_build_contract_subtitle(c),
                    url=f"/contracts/{c.id}",
                )
                for c in contracts
            ]
            groups.append(SearchResultGroup(
                type="contract",
                label="Contracts",
                items=contract_items,
                has_more=contracts_has_more,
            ))
            total_count += len(contract_items)

        # Search invoice records by invoice number
        invoice_records = list(InvoiceRecord.objects.filter(
            tenant=user.tenant,
            invoice_number__icontains=query,
        ).exclude(
            status=InvoiceRecord.Status.VOIDED,
        ).select_related("customer")[:limit + 1])

        invoices_has_more = len(invoice_records) > limit
        if invoices_has_more:
            invoice_records = invoice_records[:limit]

        if invoice_records:
            invoice_items = [
                SearchResultItem(
                    id=r.id,
                    title=r.invoice_number,
                    subtitle=r.customer_name,
                    url=f"/invoices/{r.id}",
                )
                for r in invoice_records
            ]
            groups.append(SearchResultGroup(
                type="invoice",
                label="Invoices",
                items=invoice_items,
                has_more=invoices_has_more,
            ))
            total_count += len(invoice_items)

        return GlobalSearchResult(groups=groups, total_count=total_count)


def _build_contract_subtitle(contract) -> str | None:
    """Build subtitle from contract metadata."""
    parts = []
    if contract.customer:
        parts.append(contract.customer.name)
    if contract.netsuite_sales_order_number:
        parts.append(f"SO: {contract.netsuite_sales_order_number}")
    if contract.po_number:
        parts.append(f"PO: {contract.po_number}")
    return " • ".join(parts) if parts else None


@strawberry.type
class AuthMutation:
    """Authentication mutations."""

    @strawberry.mutation
    def login(self, email: str, password: str) -> AuthResult:
        """Authenticate user and return tokens."""
        user = authenticate(username=email, password=password)

        if user is None or not user.is_active:
            return AuthError(message="Invalid email or password")

        if user.tenant and not user.tenant.is_active:
            return AuthError(message="Tenant is inactive")

        from django.utils import timezone
        user.last_login = timezone.now()
        user.save(update_fields=["last_login"])

        access_token = create_access_token(user)
        refresh_token = create_refresh_token(user)

        return AuthPayload(
            access_token=access_token,
            refresh_token=refresh_token,
            user_id=user.id,
            email=user.email,
            tenant_id=user.tenant_id,
        )

    @strawberry.mutation
    def refresh_token(self, refresh_token: str) -> AuthResult:
        """Get new access token using refresh token."""
        user = get_user_from_token(refresh_token)

        if user is None:
            return AuthError(message="Invalid or expired refresh token")

        if user.tenant and not user.tenant.is_active:
            return AuthError(message="Tenant is inactive")

        access_token = create_access_token(user)
        new_refresh_token = create_refresh_token(user)

        return AuthPayload(
            access_token=access_token,
            refresh_token=new_refresh_token,
            user_id=user.id,
            email=user.email,
            tenant_id=user.tenant_id,
        )


@strawberry.type
class FeedbackMutation:
    """Feedback submission mutations."""

    @strawberry.mutation
    def submit_feedback(self, info: Info[Context, None], input: FeedbackInput) -> FeedbackResult:
        """Submit user feedback via the configured backend."""
        from datetime import datetime
        from apps.core.feedback import get_feedback_service

        user = info.context.user
        if user is None:
            return FeedbackResult(success=False, error="Authentication required")

        # Build description with context
        lines = []
        if input.description:
            lines.append(input.description)
            lines.append("")

        lines.append("---")
        lines.append(f"**Submitted by:** {user.first_name} {user.last_name} ({user.email})")
        lines.append(f"**Type:** {input.type.value}")
        lines.append(f"**Time:** {datetime.now().isoformat()}")

        if input.page_url:
            lines.append(f"**Page:** {input.page_url}")
        if input.viewport:
            lines.append(f"**Viewport:** {input.viewport}")
        if input.user_agent:
            lines.append(f"**Browser:** {input.user_agent}")

        description = "\n".join(lines)

        try:
            service = get_feedback_service()

            result = service.create_feedback(
                title=input.title,
                description=description,
                feedback_type=input.type.value,
                screenshot=input.screenshot,
            )

            return FeedbackResult(
                success=True,
                task_url=result.url,
            )

        except Exception as e:
            import logging
            logging.getLogger(__name__).error("Feedback submission failed: %s", e)
            if "not configured" in str(e).lower():
                return FeedbackResult(success=False, error="Feedback system is not configured. Please contact an administrator.")
            return FeedbackResult(success=False, error=str(e))
