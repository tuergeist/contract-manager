"""GraphQL schema for customers."""
from typing import TYPE_CHECKING, Annotated, List

import strawberry
from strawberry import auto
import strawberry_django
from strawberry.types import Info

from apps.core.context import Context
from apps.core.permissions import get_current_user
from .models import Customer

if TYPE_CHECKING:
    from apps.contracts.schema import ContractType


@strawberry_django.type(Customer)
class CustomerType:
    id: auto
    name: auto
    hubspot_id: auto
    netsuite_customer_number: auto
    address: auto
    is_active: auto
    synced_at: auto
    created_at: auto

    @strawberry.field
    def hubspot_url(self, info: Info[Context, None]) -> str | None:
        """Get the HubSpot company URL if this customer was synced from HubSpot."""
        if not self.hubspot_id:
            return None
        user = get_current_user(info)
        if not user.tenant:
            return None
        config = user.tenant.hubspot_config or {}
        portal_id = config.get("portal_id")
        if not portal_id:
            return None
        return f"https://app-eu1.hubspot.com/contacts/{portal_id}/company/{self.hubspot_id}"

    @strawberry.field
    def contracts(self) -> List[Annotated["ContractType", strawberry.lazy("apps.contracts.schema")]]:
        """Get all contracts for this customer."""
        from apps.contracts.models import Contract

        return list(Contract.objects.filter(customer=self).order_by("-created_at"))

    @strawberry.field
    def active_contract_count(self) -> int:
        """Get the number of active contracts for this customer."""
        from apps.contracts.models import Contract

        return Contract.objects.filter(
            customer=self,
            status=Contract.Status.ACTIVE,
        ).count()


@strawberry.type
class CustomerConnection:
    """Paginated customer list."""

    items: list[CustomerType]
    total_count: int
    page: int
    page_size: int
    has_next_page: bool
    has_previous_page: bool


@strawberry.type
class CustomerQuery:
    @strawberry.field
    def customers(
        self,
        info: Info[Context, None],
        search: str | None = None,
        is_active: bool | None = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str | None = "name",
        sort_order: str | None = "asc",
    ) -> CustomerConnection:
        user = get_current_user(info)
        if not user.tenant:
            return CustomerConnection(
                items=[],
                total_count=0,
                page=page,
                page_size=page_size,
                has_next_page=False,
                has_previous_page=False,
            )

        queryset = Customer.objects.filter(tenant=user.tenant)

        if is_active is not None:
            queryset = queryset.filter(is_active=is_active)

        if search:
            from django.db.models import Q
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(netsuite_customer_number__icontains=search)
            )

        # Sorting
        allowed_sort_fields = {"name", "is_active", "synced_at", "created_at"}
        if sort_by and sort_by in allowed_sort_fields:
            order_field = f"-{sort_by}" if sort_order == "desc" else sort_by
            queryset = queryset.order_by(order_field)
        else:
            queryset = queryset.order_by("name")

        total_count = queryset.count()

        # Calculate pagination
        offset = (page - 1) * page_size
        items = list(queryset[offset : offset + page_size])

        return CustomerConnection(
            items=items,
            total_count=total_count,
            page=page,
            page_size=page_size,
            has_next_page=offset + page_size < total_count,
            has_previous_page=page > 1,
        )

    @strawberry.field
    def customer(self, info: Info[Context, None], id: strawberry.ID) -> CustomerType | None:
        user = get_current_user(info)
        if user.tenant:
            return Customer.objects.filter(tenant=user.tenant, id=id).first()
        return None
