"""GraphQL schema for tenants."""
import strawberry
from strawberry import auto
import strawberry_django
from strawberry.types import Info

from django.conf import settings
from django.contrib.auth.hashers import check_password

from apps.core.auth import create_access_token, create_refresh_token
from apps.core.context import Context
from apps.core.permissions import get_current_user
from apps.customers.hubspot import HubSpotService
from .models import PasswordResetToken, Tenant, User, UserInvitation


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
    is_admin: auto
    last_login: auto

    @strawberry.field
    def full_name(self) -> str:
        """Return the user's full name."""
        if self.first_name or self.last_name:
            return f"{self.first_name or ''} {self.last_name or ''}".strip()
        return self.email


@strawberry_django.type(UserInvitation)
class InvitationType:
    id: auto
    email: auto
    status: auto
    expires_at: auto
    created_at: auto

    @strawberry.field
    def is_expired(self) -> bool:
        return self.is_expired

    @strawberry.field
    def created_by_name(self) -> str | None:
        if self.created_by:
            return self.created_by.email
        return None

    @strawberry.field
    def invite_url(self) -> str:
        """Return the full invite URL."""
        base_url = getattr(settings, "FRONTEND_URL", "http://localhost:5173")
        return f"{base_url}/invite/{self.token}"


@strawberry.type
class OperationResult:
    """Generic result for mutations."""
    success: bool
    error: str | None = None


@strawberry.type
class InvitationResult:
    """Result of creating an invitation."""
    success: bool
    error: str | None = None
    invitation: InvitationType | None = None
    invite_url: str | None = None


@strawberry.type
class ResetLinkResult:
    """Result of creating a password reset link."""
    success: bool
    error: str | None = None
    reset_url: str | None = None


@strawberry.type
class InvitationValidation:
    """Result of validating an invitation token."""
    valid: bool
    email: str | None = None
    error: str | None = None


@strawberry.type
class ResetTokenValidation:
    """Result of validating a password reset token."""
    valid: bool
    email: str | None = None
    error: str | None = None


@strawberry.type
class ProfileUpdateResult:
    """Result of updating user profile."""
    success: bool
    error: str | None = None
    user: UserType | None = None


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
    def current_user(self, info: Info[Context, None]) -> UserType | None:
        if info.context.is_authenticated:
            return info.context.user
        return None

    @strawberry.field
    def current_tenant(self, info) -> TenantType | None:
        tenant = getattr(info.context.request, "tenant", None)
        return tenant

    @strawberry.field
    def users(self, info: Info[Context, None]) -> list[UserType]:
        """List all users in the current tenant. Admin only."""
        user = get_current_user(info)
        if not user.tenant:
            return []
        if not user.is_admin and not user.is_super_admin:
            return []
        return list(User.objects.filter(tenant=user.tenant))

    @strawberry.field
    def pending_invitations(self, info: Info[Context, None]) -> list[InvitationType]:
        """List pending invitations for current tenant. Admin only."""
        user = get_current_user(info)
        if not user.tenant:
            return []
        if not user.is_admin and not user.is_super_admin:
            return []
        return list(
            UserInvitation.objects.filter(
                tenant=user.tenant,
                status=UserInvitation.Status.PENDING,
            )
        )

    @strawberry.field
    def validate_invitation(self, token: str) -> InvitationValidation:
        """Validate an invitation token. Public."""
        invitation = UserInvitation.objects.filter(token=token).first()
        if not invitation:
            return InvitationValidation(valid=False, error="Invalid invitation link")
        if invitation.status != UserInvitation.Status.PENDING:
            return InvitationValidation(valid=False, error="This invitation has already been used")
        if invitation.is_expired:
            return InvitationValidation(valid=False, error="This invitation has expired")
        return InvitationValidation(valid=True, email=invitation.email)

    @strawberry.field
    def validate_password_reset(self, token: str) -> ResetTokenValidation:
        """Validate a password reset token. Public."""
        reset_token = PasswordResetToken.objects.filter(token=token).first()
        if not reset_token:
            return ResetTokenValidation(valid=False, error="Invalid reset link")
        if reset_token.used:
            return ResetTokenValidation(valid=False, error="This reset link has already been used")
        if reset_token.is_expired:
            return ResetTokenValidation(valid=False, error="This reset link has expired")
        return ResetTokenValidation(valid=True, email=reset_token.user.email)

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

    # User Management Mutations

    @strawberry.mutation
    def deactivate_user(
        self, info: Info[Context, None], user_id: strawberry.ID
    ) -> OperationResult:
        """Deactivate a user. Admin only."""
        admin = get_current_user(info)
        if not admin.tenant:
            return OperationResult(success=False, error="No tenant assigned")
        if not admin.is_admin and not admin.is_super_admin:
            return OperationResult(success=False, error="Admin access required")

        try:
            target_user = User.objects.get(id=user_id, tenant=admin.tenant)
        except User.DoesNotExist:
            return OperationResult(success=False, error="User not found")

        if target_user.id == admin.id:
            return OperationResult(success=False, error="Cannot deactivate yourself")

        target_user.is_active = False
        target_user.save(update_fields=["is_active"])
        return OperationResult(success=True)

    @strawberry.mutation
    def reactivate_user(
        self, info: Info[Context, None], user_id: strawberry.ID
    ) -> OperationResult:
        """Reactivate a user. Admin only."""
        admin = get_current_user(info)
        if not admin.tenant:
            return OperationResult(success=False, error="No tenant assigned")
        if not admin.is_admin and not admin.is_super_admin:
            return OperationResult(success=False, error="Admin access required")

        try:
            target_user = User.objects.get(id=user_id, tenant=admin.tenant)
        except User.DoesNotExist:
            return OperationResult(success=False, error="User not found")

        target_user.is_active = True
        target_user.save(update_fields=["is_active"])
        return OperationResult(success=True)

    # Invitation Mutations

    @strawberry.mutation
    def create_invitation(
        self, info: Info[Context, None], email: str, base_url: str | None = None
    ) -> InvitationResult:
        """Create an invitation for a new user. Admin only."""
        admin = get_current_user(info)
        if not admin.tenant:
            return InvitationResult(success=False, error="No tenant assigned")
        if not admin.is_admin and not admin.is_super_admin:
            return InvitationResult(success=False, error="Admin access required")

        email = email.lower().strip()

        # Check if user already exists
        if User.objects.filter(email=email, tenant=admin.tenant).exists():
            return InvitationResult(success=False, error="User with this email already exists")

        # Check for existing pending invitation
        existing = UserInvitation.objects.filter(
            email=email,
            tenant=admin.tenant,
            status=UserInvitation.Status.PENDING,
        ).first()
        if existing and existing.is_valid:
            return InvitationResult(success=False, error="Pending invitation already exists for this email")

        invitation = UserInvitation.create_invitation(
            tenant=admin.tenant,
            email=email,
            created_by=admin,
        )
        url_base = base_url or getattr(settings, "FRONTEND_URL", "http://localhost:5173")
        invite_url = f"{url_base}/invite/{invitation.token}"

        return InvitationResult(
            success=True,
            invitation=invitation,
            invite_url=invite_url,
        )

    @strawberry.mutation
    def revoke_invitation(
        self, info: Info[Context, None], invitation_id: strawberry.ID
    ) -> OperationResult:
        """Revoke a pending invitation. Admin only."""
        admin = get_current_user(info)
        if not admin.tenant:
            return OperationResult(success=False, error="No tenant assigned")
        if not admin.is_admin and not admin.is_super_admin:
            return OperationResult(success=False, error="Admin access required")

        try:
            invitation = UserInvitation.objects.get(
                id=invitation_id,
                tenant=admin.tenant,
                status=UserInvitation.Status.PENDING,
            )
        except UserInvitation.DoesNotExist:
            return OperationResult(success=False, error="Invitation not found")

        invitation.status = UserInvitation.Status.REVOKED
        invitation.save(update_fields=["status"])
        return OperationResult(success=True)

    @strawberry.mutation
    def accept_invitation(
        self,
        token: str,
        password: str,
        first_name: str = "",
        last_name: str = "",
    ) -> OperationResult:
        """Accept an invitation and create account. Public."""
        invitation = UserInvitation.objects.filter(token=token).first()
        if not invitation:
            return OperationResult(success=False, error="Invalid invitation link")
        if invitation.status != UserInvitation.Status.PENDING:
            return OperationResult(success=False, error="This invitation has already been used")
        if invitation.is_expired:
            return OperationResult(success=False, error="This invitation has expired")

        if len(password) < 8:
            return OperationResult(success=False, error="Password must be at least 8 characters")

        # Create user
        User.objects.create_user(
            email=invitation.email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            tenant=invitation.tenant,
            is_active=True,
        )

        # Mark invitation as used
        invitation.status = UserInvitation.Status.USED
        invitation.save(update_fields=["status"])

        return OperationResult(success=True)

    # Password Mutations

    @strawberry.mutation
    def change_password(
        self,
        info: Info[Context, None],
        current_password: str,
        new_password: str,
    ) -> OperationResult:
        """Change the current user's password."""
        user = get_current_user(info)

        if not check_password(current_password, user.password):
            return OperationResult(success=False, error="Current password is incorrect")

        if len(new_password) < 8:
            return OperationResult(success=False, error="Password must be at least 8 characters")

        user.set_password(new_password)
        user.save()
        return OperationResult(success=True)

    @strawberry.mutation
    def update_profile(
        self,
        info: Info[Context, None],
        first_name: str | None = None,
        last_name: str | None = None,
        email: str | None = None,
    ) -> ProfileUpdateResult:
        """Update the current user's profile."""
        import re
        user = get_current_user(info)

        # Validate email format if provided
        if email is not None:
            email = email.lower().strip()
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, email):
                return ProfileUpdateResult(success=False, error="Invalid email format")

            # Check email uniqueness within tenant (excluding current user)
            if User.objects.filter(email=email, tenant=user.tenant).exclude(id=user.id).exists():
                return ProfileUpdateResult(success=False, error="Email is already in use")

            user.email = email

        if first_name is not None:
            user.first_name = first_name.strip()

        if last_name is not None:
            user.last_name = last_name.strip()

        user.save()
        return ProfileUpdateResult(success=True, user=user)

    @strawberry.mutation
    def create_password_reset(
        self, info: Info[Context, None], user_id: strawberry.ID, base_url: str | None = None
    ) -> ResetLinkResult:
        """Create a password reset link for a user. Admin only."""
        admin = get_current_user(info)
        if not admin.tenant:
            return ResetLinkResult(success=False, error="No tenant assigned")
        if not admin.is_admin and not admin.is_super_admin:
            return ResetLinkResult(success=False, error="Admin access required")

        try:
            target_user = User.objects.get(id=user_id, tenant=admin.tenant)
        except User.DoesNotExist:
            return ResetLinkResult(success=False, error="User not found")

        reset_token = PasswordResetToken.create_token(target_user)
        url_base = base_url or getattr(settings, "FRONTEND_URL", "http://localhost:5173")
        reset_url = f"{url_base}/reset-password/{reset_token.token}"

        return ResetLinkResult(success=True, reset_url=reset_url)

    @strawberry.mutation
    def reset_password(self, token: str, new_password: str) -> OperationResult:
        """Reset password using a reset token. Public."""
        reset_token = PasswordResetToken.objects.filter(token=token).first()
        if not reset_token:
            return OperationResult(success=False, error="Invalid reset link")
        if reset_token.used:
            return OperationResult(success=False, error="This reset link has already been used")
        if reset_token.is_expired:
            return OperationResult(success=False, error="This reset link has expired")

        if len(new_password) < 8:
            return OperationResult(success=False, error="Password must be at least 8 characters")

        user = reset_token.user
        user.set_password(new_password)
        user.save()

        reset_token.used = True
        reset_token.save(update_fields=["used"])

        return OperationResult(success=True)
