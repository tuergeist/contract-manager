"""Core GraphQL schema for authentication."""
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


AuthResult = strawberry.union("AuthResult", [AuthPayload, AuthError])


@strawberry.type
class DeleteResult:
    """Result of delete operations."""

    success: bool = False
    error: str | None = None


@strawberry.type
class CurrentUser:
    """Current authenticated user info."""

    id: int
    email: str
    first_name: str
    last_name: str
    tenant_id: int | None
    tenant_name: str | None
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
    def me(self, info: Info[Context, None]) -> CurrentUser | None:
        """Get current authenticated user."""
        user = info.context.user
        if user is None:
            return None

        role_names = [r.name for r in user.roles.all()]
        permissions = sorted(user.effective_permissions)
        return CurrentUser(
            id=user.id,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            tenant_id=user.tenant_id,
            tenant_name=user.tenant.name if user.tenant else None,
            role_name=user.role.name if user.role else None,
            is_admin=user.is_admin or user.is_super_admin,
            roles=role_names,
            permissions=permissions,
        )

    @strawberry.field
    def global_search(
        self, info: Info[Context, None], query: str, limit: int = 10
    ) -> GlobalSearchResult:
        """Search across customers and contracts."""
        from apps.contracts.models import Contract
        from apps.customers.models import Customer

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
