"""Core GraphQL schema for authentication."""
from typing import Annotated, Union

import strawberry
from django.contrib.auth import authenticate
from django.db.models import Q
from strawberry.types import Info

from apps.core.auth import (
    create_access_token,
    create_refresh_token,
    create_2fa_challenge_token,
    create_2fa_setup_token,
    decode_2fa_challenge,
    get_user_from_token,
)
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
class TwoFactorChallenge:
    """Response when 2FA is required."""

    requires_two_factor: bool = True
    challenge_token: str = ""
    method: str = ""  # "totp" or "email"


@strawberry.type
class AuthError:
    """Authentication error."""

    message: str


AuthResult = Annotated[Union[AuthPayload, TwoFactorChallenge, AuthError], strawberry.union("AuthResult")]


@strawberry.type
class OperationResult:
    """Simple success/error result."""
    success: bool
    error: str | None = None


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
    two_factor_enabled: bool = False
    two_factor_method: str | None = None


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


def _get_2fa_enabled(user) -> bool:
    try:
        return user.two_factor_config.is_active
    except Exception:
        return False


def _get_2fa_method(user) -> str | None:
    try:
        cfg = user.two_factor_config
        return cfg.method if cfg.is_active else None
    except Exception:
        return None


@strawberry.type
class CoreQuery:
    """Core queries including auth status."""

    @strawberry.field
    def feedback_enabled(self) -> bool:
        """Check if the selected feedback backend is configured."""
        from apps.core.feedback import get_feedback_service
        return get_feedback_service().is_configured()

    @strawberry.field
    def signup_enabled(self) -> bool:
        """Check if public tenant signup is enabled."""
        from django.conf import settings
        return settings.SIGNUP_ENABLED

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
            two_factor_enabled=_get_2fa_enabled(user),
            two_factor_method=_get_2fa_method(user),
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

        # Check if user has 2FA enabled
        try:
            tfa = user.two_factor_config
            if tfa.is_active:
                challenge_token = create_2fa_challenge_token(user, tfa.method)

                # Send email code if method is email
                if tfa.method == "email":
                    from apps.tenants.tasks import send_2fa_email_code
                    send_2fa_email_code.delay(user.id)

                return TwoFactorChallenge(
                    challenge_token=challenge_token,
                    method=tfa.method,
                )
        except Exception:
            pass  # No 2FA config — proceed normally

        # Check if tenant enforces 2FA and user doesn't have it
        if user.tenant and (user.tenant.settings or {}).get("two_factor_enforced"):
            access_token = create_2fa_setup_token(user)
            return AuthPayload(
                access_token=access_token,
                refresh_token="",
                user_id=user.id,
                email=user.email,
                tenant_id=user.tenant_id,
            )

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
    def verify_2fa(self, challenge_token: str, code: str) -> AuthResult:
        """Verify 2FA code and return full tokens."""
        from django.core.cache import cache
        from apps.tenants.models import User

        payload = decode_2fa_challenge(challenge_token)
        if payload is None:
            return AuthError(message="Invalid or expired verification session")

        user_id = int(payload["sub"])
        method = payload.get("method")

        # Rate limiting
        rate_key = f"2fa_attempts:{user_id}"
        attempts = cache.get(rate_key, 0)
        if attempts >= 5:
            return AuthError(message="Too many attempts. Please log in again.")

        try:
            user = User.objects.select_related("tenant", "role").prefetch_related("roles").get(
                id=user_id, is_active=True
            )
        except User.DoesNotExist:
            return AuthError(message="User not found")

        try:
            tfa = user.two_factor_config
        except Exception:
            return AuthError(message="2FA not configured")

        # Verify code
        verified = False
        code_clean = code.strip()

        if method == "totp":
            import pyotp
            totp = pyotp.TOTP(tfa.get_totp_secret())
            if totp.verify(code_clean, valid_window=1):
                verified = True
            elif tfa.verify_recovery_code(code_clean):
                verified = True
        elif method == "email":
            cached_code = cache.get(f"2fa_code:{user_id}")
            if cached_code and cached_code == code_clean:
                cache.delete(f"2fa_code:{user_id}")  # Single-use
                verified = True
            elif tfa.verify_recovery_code(code_clean):
                verified = True

        if not verified:
            cache.set(rate_key, attempts + 1, timeout=900)
            return AuthError(message="Invalid verification code")

        # Clear rate limit on success
        cache.delete(rate_key)

        access_token = create_access_token(user)
        refresh_token_val = create_refresh_token(user)

        return AuthPayload(
            access_token=access_token,
            refresh_token=refresh_token_val,
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
