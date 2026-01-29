"""GraphQL schema for tenants."""
import strawberry
from strawberry import auto
import strawberry_django
from strawberry.types import Info

from apps.core.context import Context
from apps.core.permissions import get_current_user
from apps.customers.hubspot import HubSpotService
from .models import Tenant, User


@strawberry_django.type(Tenant)
class TenantType:
    id: auto
    name: auto
    currency: auto
    is_active: auto


@strawberry_django.type(User)
class UserType:
    id: auto
    email: auto
    first_name: auto
    last_name: auto
    is_active: auto


@strawberry.type
class HubSpotCompanyFilter:
    """A filter for HubSpot company sync."""
    property_name: str  # e.g., "lifecyclestage"
    values: list[str]   # e.g., ["customer", "evangelist"]


@strawberry.type
class HubSpotSettings:
    """HubSpot integration settings."""

    is_configured: bool
    api_key_set: bool
    last_sync: str | None
    last_product_sync: str | None
    last_deal_sync: str | None
    company_filters: list[HubSpotCompanyFilter]


@strawberry.type
class HubSpotTestResult:
    """Result of HubSpot connection test."""

    success: bool
    error: str | None


@strawberry.type
class HubSpotSyncResult:
    """Result of HubSpot sync operation."""

    success: bool
    error: str | None
    created: int
    updated: int


@strawberry.type
class HubSpotDealSyncResult:
    """Result of HubSpot deal sync operation."""

    success: bool
    error: str | None
    created: int
    skipped: int


@strawberry.type
class HubSpotPropertyCheckResult:
    """Result of checking a HubSpot company property."""

    success: bool
    error: str | None
    exists: bool
    options: list[str] | None  # Available values for enumeration properties
    property_type: str | None  # e.g., "enumeration", "string", "number"


@strawberry.type
class HubSpotProperty:
    """A HubSpot company property."""

    name: str  # Internal name (e.g., "lifecyclestage")
    label: str  # Display label (e.g., "Lifecycle Stage")
    property_type: str  # e.g., "enumeration", "string", "number"
    options: list[str] | None  # Available values for enumeration properties


@strawberry.type
class HubSpotPropertiesResult:
    """Result of listing HubSpot company properties."""

    success: bool
    error: str | None
    properties: list[HubSpotProperty] | None


@strawberry.type
class TenantQuery:
    @strawberry.field
    def current_user(self, info) -> UserType | None:
        user = info.context.request.user
        if user.is_authenticated:
            return user
        return None

    @strawberry.field
    def current_tenant(self, info) -> TenantType | None:
        tenant = getattr(info.context.request, "tenant", None)
        return tenant

    @strawberry.field
    def hubspot_settings(self, info: Info[Context, None]) -> HubSpotSettings | None:
        """Get HubSpot settings for current tenant."""
        user = get_current_user(info)
        if not user.tenant:
            return None

        config = user.tenant.hubspot_config or {}
        api_key = config.get("api_key", "")

        # Parse company filters from config
        filters_data = config.get("company_filters", [])
        company_filters = [
            HubSpotCompanyFilter(
                property_name=f.get("property_name", ""),
                values=f.get("values", []),
            )
            for f in filters_data
        ]

        return HubSpotSettings(
            is_configured=bool(api_key),
            api_key_set=bool(api_key),
            last_sync=config.get("last_sync"),
            last_product_sync=config.get("last_product_sync"),
            last_deal_sync=config.get("last_deal_sync"),
            company_filters=company_filters,
        )

    @strawberry.field
    def hubspot_company_properties(
        self, info: Info[Context, None]
    ) -> HubSpotPropertiesResult:
        """List all available HubSpot company properties."""
        user = get_current_user(info)
        if not user.tenant:
            return HubSpotPropertiesResult(
                success=False,
                error="No tenant assigned",
                properties=None,
            )

        service = HubSpotService(user.tenant)
        result = service.list_company_properties()

        properties = None
        if result.get("properties"):
            properties = [
                HubSpotProperty(
                    name=p["name"],
                    label=p["label"],
                    property_type=p["type"],
                    options=p.get("options"),
                )
                for p in result["properties"]
            ]

        return HubSpotPropertiesResult(
            success=result.get("success", False),
            error=result.get("error"),
            properties=properties,
        )


@strawberry.input
class HubSpotCompanyFilterInput:
    """Input for HubSpot company filter."""
    property_name: str  # e.g., "lifecyclestage"
    values: list[str]   # e.g., ["customer", "evangelist"]


@strawberry.type
class TenantMutation:
    @strawberry.mutation
    def save_hubspot_settings(
        self, info: Info[Context, None], api_key: str
    ) -> HubSpotTestResult:
        """Save HubSpot API key and test connection."""
        user = get_current_user(info)
        if not user.tenant:
            return HubSpotTestResult(success=False, error="No tenant assigned")

        tenant = user.tenant

        # Save the API key
        if not tenant.hubspot_config:
            tenant.hubspot_config = {}
        tenant.hubspot_config["api_key"] = api_key
        tenant.save(update_fields=["hubspot_config"])

        # Test connection
        service = HubSpotService(tenant)
        result = service.test_connection_sync()

        return HubSpotTestResult(
            success=result["success"],
            error=result.get("error"),
        )

    @strawberry.mutation
    def test_hubspot_connection(self, info: Info[Context, None]) -> HubSpotTestResult:
        """Test the HubSpot API connection."""
        user = get_current_user(info)
        if not user.tenant:
            return HubSpotTestResult(success=False, error="No tenant assigned")

        service = HubSpotService(user.tenant)
        result = service.test_connection_sync()

        return HubSpotTestResult(
            success=result["success"],
            error=result.get("error"),
        )

    @strawberry.mutation
    def sync_hubspot_customers(self, info: Info[Context, None]) -> HubSpotSyncResult:
        """Sync customers from HubSpot."""
        user = get_current_user(info)
        if not user.tenant:
            return HubSpotSyncResult(
                success=False, error="No tenant assigned", created=0, updated=0
            )

        service = HubSpotService(user.tenant)
        result = service.sync_companies()

        return HubSpotSyncResult(
            success=result["success"],
            error=result.get("error"),
            created=result.get("created", 0),
            updated=result.get("updated", 0),
        )

    @strawberry.mutation
    def sync_hubspot_products(self, info: Info[Context, None]) -> HubSpotSyncResult:
        """Sync products from HubSpot."""
        user = get_current_user(info)
        if not user.tenant:
            return HubSpotSyncResult(
                success=False, error="No tenant assigned", created=0, updated=0
            )

        service = HubSpotService(user.tenant)
        result = service.sync_products()

        return HubSpotSyncResult(
            success=result["success"],
            error=result.get("error"),
            created=result.get("created", 0),
            updated=result.get("updated", 0),
        )

    @strawberry.mutation
    def sync_hubspot_deals(self, info: Info[Context, None]) -> HubSpotDealSyncResult:
        """Sync closed won deals from HubSpot as contract drafts."""
        user = get_current_user(info)
        if not user.tenant:
            return HubSpotDealSyncResult(
                success=False, error="No tenant assigned", created=0, skipped=0
            )

        service = HubSpotService(user.tenant)
        result = service.sync_deals()

        return HubSpotDealSyncResult(
            success=result["success"],
            error=result.get("error"),
            created=result.get("created", 0),
            skipped=result.get("skipped", 0),
        )

    @strawberry.mutation
    def save_hubspot_company_filters(
        self,
        info: Info[Context, None],
        filters: list[HubSpotCompanyFilterInput],
    ) -> HubSpotTestResult:
        """Save HubSpot company sync filters."""
        user = get_current_user(info)
        if not user.tenant:
            return HubSpotTestResult(success=False, error="No tenant assigned")

        tenant = user.tenant

        # Save the filters
        if not tenant.hubspot_config:
            tenant.hubspot_config = {}

        tenant.hubspot_config["company_filters"] = [
            {"property_name": f.property_name, "values": f.values}
            for f in filters
        ]
        tenant.save(update_fields=["hubspot_config"])

        return HubSpotTestResult(success=True, error=None)

    @strawberry.mutation
    def check_hubspot_property(
        self,
        info: Info[Context, None],
        property_name: str,
    ) -> HubSpotPropertyCheckResult:
        """Check if a HubSpot company property exists and get available values."""
        user = get_current_user(info)
        if not user.tenant:
            return HubSpotPropertyCheckResult(
                success=False,
                error="No tenant assigned",
                exists=False,
                options=None,
                property_type=None,
            )

        service = HubSpotService(user.tenant)
        result = service.check_company_property(property_name)

        return HubSpotPropertyCheckResult(
            success=result.get("success", False),
            error=result.get("error"),
            exists=result.get("exists", False),
            options=result.get("options"),
            property_type=result.get("property_type"),
        )
