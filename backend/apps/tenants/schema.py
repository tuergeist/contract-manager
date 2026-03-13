"""GraphQL schema for tenants."""
from datetime import date
from decimal import Decimal

import strawberry
from strawberry import auto
import strawberry_django
from strawberry.types import Info

from django.conf import settings
from django.contrib.auth.hashers import check_password

from apps.core.auth import create_access_token, create_refresh_token
from apps.core.context import Context
from apps.core.permissions import (
    ADMIN_PROTECTED_PERMISSIONS,
    ALL_PERMISSIONS,
    PERMISSION_REGISTRY,
    check_perm,
    get_current_user,
    normalize_permissions,
    require_perm,
)
from apps.customers.hubspot import HubSpotService
from .models import PasswordResetToken, Role, SignupVerification, Tenant, TwoFactorConfig, User, UserInvitation


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

    @strawberry.field
    def role_names(self) -> list[str]:
        """Return list of assigned role names."""
        return [r.name for r in self.roles.all()]

    @strawberry.field
    def two_factor_enabled(self) -> bool:
        """Whether 2FA is active for this user."""
        try:
            return self.two_factor_config.is_active
        except Exception:
            return False

    @strawberry.field
    def two_factor_method(self) -> str | None:
        """The 2FA method if enabled."""
        try:
            cfg = self.two_factor_config
            return cfg.method if cfg.is_active else None
        except Exception:
            return None


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
    def invite_url(self, info: Info) -> str:
        """Return the full invite URL."""
        request = info.context.request
        origin = request.headers.get("Origin") or request.headers.get("Referer", "").rstrip("/")
        base_url = origin or getattr(settings, "FRONTEND_URL", "http://localhost:5173")
        return f"{base_url}/invite/{self.token}"


from apps.core.schema import OperationResult  # noqa: E402 - re-exported for backward compat


@strawberry.type
class InvitationResult:
    """Result of creating an invitation."""
    success: bool
    error: str | None = None
    invitation: InvitationType | None = None
    invite_url: str | None = None


@strawberry.type
class SignupVerifyResult:
    """Result of signup verification."""
    success: bool
    error: str | None = None
    access_token: str | None = None
    refresh_token: str | None = None


@strawberry.type
class TotpSetupResult:
    """Result of TOTP setup initiation."""
    success: bool
    error: str | None = None
    secret: str | None = None
    provisioning_uri: str | None = None


@strawberry.type
class TwoFactorConfirmResult:
    """Result of 2FA confirmation with recovery codes."""
    success: bool
    error: str | None = None
    recovery_codes: list[str] | None = None


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
class RoleType:
    """A role with permissions."""
    id: int
    name: str
    is_system: bool
    permissions: strawberry.scalars.JSON
    user_count: int


@strawberry.type
class RoleResult:
    """Result of a role mutation."""
    success: bool
    error: str | None = None
    role: RoleType | None = None


@strawberry.type
class PermissionResource:
    """A resource in the permission registry."""
    resource: str
    actions: list[str]


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
    auto_sync_enabled: bool = False
    last_auto_sync_customers: str | None = None
    last_auto_sync_products: str | None = None
    last_auto_sync_deals: str | None = None
    billing_contact_label: str | None = None
    portal_id: str | None = None
    sync_mode: str | None = None
    webhook_last_received: str | None = None


@strawberry.type
class WebhookEventLogType:
    """A single webhook event log entry."""
    id: int
    subscription_type: str
    object_id: str
    object_kind: str
    status: str
    result: str
    error_message: str
    received_at: str


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
    warnings: list[str] | None = None


@strawberry.type
class HubSpotDealSyncResult:
    """Result of HubSpot deal sync operation."""

    success: bool
    error: str | None
    created: int
    skipped: int
    warnings: list[str] | None = None


@strawberry.input
class HubSpotDateRangeInput:
    """Optional date range for filtered sync."""

    modified_since: date | None = None
    modified_until: date | None = None


@strawberry.type
class HubSpotAssociatedCompany:
    """Associated company info from deal check."""

    hubspot_id: str
    name: str | None
    synced: bool


@strawberry.type
class HubSpotDealCheckResult:
    """Result of checking a single HubSpot deal."""

    success: bool
    error: str | None = None
    deal_name: str | None = None
    deal_stage: str | None = None
    deal_stage_id: str | None = None
    pipeline: str | None = None
    pipeline_id: str | None = None
    is_closed_won: bool | None = None
    associated_company: HubSpotAssociatedCompany | None = None
    existing_contract_id: str | None = None
    would_sync: bool | None = None
    reasons: list[str] | None = None


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
class HubSpotAssociationLabel:
    """A HubSpot association label for company-to-contact relationships."""

    type_id: int
    label: str
    category: str


@strawberry.type
class HubSpotAssociationLabelsResult:
    """Result of listing HubSpot association labels."""

    success: bool
    error: str | None
    labels: list[HubSpotAssociationLabel] | None


@strawberry.type
class InvoiceEmailTemplate:
    """An email template for a specific language."""
    language: str
    subject: str
    body: str
    is_custom: bool


@strawberry.type
class InvoiceEmailTemplatesResult:
    """Result of querying invoice email templates."""
    success: bool
    error: str | None = None
    templates: list[InvoiceEmailTemplate] | None = None


@strawberry.input
class SetInvoiceEmailTemplateInput:
    """Input for setting an invoice email template."""
    language: str
    subject: str
    body: str


DOCUMENT_BCC_TYPES = ("invoice", "storno", "order_confirmation", "offer")


@strawberry.type
class DocumentEmailBccEntry:
    """BCC recipients for a specific document type."""
    document_type: str
    recipients: list[str]


@strawberry.input
class SetDocumentEmailBccInput:
    """Input for setting BCC recipients per document type."""
    document_type: str
    recipients: list[str]


@strawberry.type
class M365Settings:
    """Microsoft 365 integration settings."""
    is_configured: bool
    sender_mailbox: str | None = None
    client_id_masked: str | None = None
    azure_tenant_id_masked: str | None = None


@strawberry.type
class M365MailboxType:
    """A mailbox discovered from M365."""
    email: str
    display_name: str


@strawberry.type
class M365TestResult:
    """Result of M365 connection test."""
    success: bool
    error: str | None = None
    organization: str | None = None


@strawberry.type
class M365MailboxesResult:
    """Result of M365 mailbox discovery."""
    success: bool
    error: str | None = None
    mailboxes: list[M365MailboxType] | None = None


@strawberry.type
class SmtpSettingsType:
    """SMTP notification service settings."""
    host: str
    port: int
    username: str
    from_name: str
    from_address: str
    use_tls: bool
    is_configured: bool
    password_set: bool


@strawberry.type
class BankingSettingsType:
    """Banking fee tolerance settings for invoice matching."""
    fee_tolerance_fixed: Decimal
    fee_tolerance_percent: Decimal


@strawberry.type
class NotificationPreferencesType:
    """Per-user notification subscription preferences."""
    todo_assigned: bool
    hubspot_new_contract: bool
    hubspot_sync_completed: bool
    time_tracking_sync_completed: bool


@strawberry.type
class DashboardPreferencesType:
    """Per-user dashboard section visibility preferences."""
    show_contracts: bool = True
    show_revenue_goals: bool = True
    show_new_business: bool = True
    show_price_increase_impact: bool = True


@strawberry.type
class TimeTrackingSettings:
    """Time tracking integration settings."""
    provider: str | None
    is_configured: bool
    show_revenue: bool = True
    maintenance_project_template: str = ""
    oneoff_project_template: str = ""


@strawberry.type
class TimeTrackingTestResult:
    """Result of time tracking connection test."""
    success: bool
    error: str | None = None


ACTIVATION_CHECKABLE_FIELDS = [
    "po_number",
    "order_confirmation_number",
    "netsuite_sales_order_number",
    "netsuite_contract_number",
    "netsuite_url",
]


@strawberry.type
class ActivationChecklistField:
    """A field that can be required for contract activation."""
    field_name: str
    required: bool


@strawberry.type
class ActivationChecklistSettings:
    """Activation checklist configuration."""
    available_fields: list[str]
    required_fields: list[str]


@strawberry.type
class HelpVideoLinkType:
    """A single help video link."""
    url: str
    label: str | None = None


@strawberry.type
class HelpVideoLinksEntryType:
    """Help video links for a specific route."""
    route_key: str
    links: list[HelpVideoLinkType]


@strawberry.input
class HelpVideoLinkInput:
    """Input for a single help video link."""
    url: str
    label: str | None = None


@strawberry.input
class HelpVideoLinksEntryInput:
    """Input for help video links for a route."""
    route_key: str
    links: list[HelpVideoLinkInput]


@strawberry.type
class TenantSettingsType:
    two_factor_enforced: bool = False
    payment_delay_days: int = 60
    fte_snapshot_capture_day: int = 7
    fte_snapshot_notification_email: str | None = None


@strawberry.type
class TenantQuery:
    @strawberry.field
    def tenant_settings(self, info: Info[Context, None]) -> TenantSettingsType | None:
        """Get tenant settings for the current user."""
        user = get_current_user(info)
        if not user or not user.tenant:
            return None
        s = user.tenant.settings or {}
        return TenantSettingsType(
            two_factor_enforced=s.get("two_factor_enforced", False),
            payment_delay_days=s.get("payment_delay_days", 60),
            fte_snapshot_capture_day=s.get("fte_snapshot_capture_day", 7),
            fte_snapshot_notification_email=s.get("fte_snapshot_notification_email"),
        )

    @strawberry.field
    def current_user(self, info: Info[Context, None]) -> UserType | None:
        if info.context.is_authenticated:
            return info.context.user
        return None

    @strawberry.field
    def current_tenant(self, info: Info[Context, None]) -> TenantType | None:
        tenant = getattr(info.context.request, "tenant", None)
        return tenant

    @strawberry.field
    def roles(self, info: Info[Context, None]) -> list[RoleType]:
        """List all roles for the current tenant. Requires settings.read."""
        user = require_perm(info, "settings", "read")
        if not user.tenant:
            return []
        qs = Role.objects.filter(tenant=user.tenant)
        return [
            RoleType(
                id=r.id,
                name=r.name,
                is_system=r.is_system,
                permissions=r.permissions or {},
                user_count=r.users.count(),
            )
            for r in qs
        ]

    @strawberry.field
    def permission_registry(self, info: Info[Context, None]) -> list[PermissionResource]:
        """Return the full permission registry (resources + actions)."""
        get_current_user(info)  # require auth
        return [
            PermissionResource(resource=resource, actions=actions)
            for resource, actions in PERMISSION_REGISTRY.items()
        ]

    @strawberry.field
    def users(self, info: Info[Context, None]) -> list[UserType]:
        """List all users in the current tenant. Requires users.read."""
        user = require_perm(info, "users", "read")
        if not user.tenant:
            return []
        return list(User.objects.prefetch_related("roles").filter(tenant=user.tenant))

    @strawberry.field
    def pending_invitations(self, info: Info[Context, None]) -> list[InvitationType]:
        """List pending invitations for current tenant. Requires users.read."""
        user = require_perm(info, "users", "read")
        if not user.tenant:
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
    def time_tracking_settings(self, info: Info[Context, None]) -> TimeTrackingSettings | None:
        """Get time tracking settings for current tenant."""
        user = get_current_user(info)
        if not user.tenant:
            return None
        config = user.tenant.time_tracking_config or {}
        provider = config.get("provider")
        is_configured = bool(provider and config.get("api_key"))
        show_revenue = config.get("show_revenue", True)
        return TimeTrackingSettings(
            provider=provider,
            is_configured=is_configured,
            show_revenue=show_revenue,
            maintenance_project_template=config.get("maintenance_project_template", ""),
            oneoff_project_template=config.get("oneoff_project_template", ""),
        )

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
            auto_sync_enabled=config.get("auto_sync_enabled", False),
            last_auto_sync_customers=config.get("last_auto_sync_customers"),
            last_auto_sync_products=config.get("last_auto_sync_products"),
            last_auto_sync_deals=config.get("last_auto_sync_deals"),
            billing_contact_label=config.get("billing_contact_label"),
            portal_id=config.get("portal_id"),

            sync_mode=config.get("sync_mode"),
            webhook_last_received=config.get("webhook_last_received"),
        )

    @strawberry.field
    def webhook_event_logs(
        self, info: Info[Context, None], limit: int = 20
    ) -> list[WebhookEventLogType]:
        """Get recent webhook event logs for the current tenant."""
        user = get_current_user(info)
        if not user.tenant:
            return []

        from apps.customers.models import WebhookEventLog

        limit = min(limit, 100)
        qs = WebhookEventLog.objects.filter(tenant=user.tenant)[:limit]
        return [
            WebhookEventLogType(
                id=e.id,
                subscription_type=e.subscription_type,
                object_id=e.object_id,
                object_kind=e.object_kind,
                status=e.status,
                result=e.result,
                error_message=e.error_message,
                received_at=e.received_at.isoformat(),
            )
            for e in qs
        ]

    @strawberry.field
    def activation_checklist_settings(
        self, info: Info[Context, None]
    ) -> ActivationChecklistSettings | None:
        """Get activation checklist configuration for current tenant."""
        user = get_current_user(info)
        if not user.tenant:
            return None
        settings = user.tenant.settings or {}
        return ActivationChecklistSettings(
            available_fields=ACTIVATION_CHECKABLE_FIELDS,
            required_fields=settings.get("activation_required_fields", []),
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

    @strawberry.field
    def check_hubspot_deal(
        self, info: Info[Context, None], deal_id: str
    ) -> HubSpotDealCheckResult:
        """Check a single HubSpot deal and explain sync status."""
        user = get_current_user(info)
        if not user.tenant:
            return HubSpotDealCheckResult(success=False, error="No tenant assigned")

        service = HubSpotService(user.tenant)
        result = service.check_deal(deal_id)

        if not result.get("success"):
            return HubSpotDealCheckResult(success=False, error=result.get("error"))

        associated = result.get("associatedCompany")
        associated_company = None
        if associated:
            associated_company = HubSpotAssociatedCompany(
                hubspot_id=associated["hubspotId"],
                name=associated.get("name"),
                synced=associated.get("synced", False),
            )

        return HubSpotDealCheckResult(
            success=True,
            deal_name=result.get("dealName"),
            deal_stage=result.get("dealStage"),
            deal_stage_id=result.get("dealStageId"),
            pipeline=result.get("pipeline"),
            pipeline_id=result.get("pipelineId"),
            is_closed_won=result.get("isClosedWon"),
            associated_company=associated_company,
            existing_contract_id=result.get("existingContractId"),
            would_sync=result.get("wouldSync"),
            reasons=result.get("reasons"),
        )

    @strawberry.field
    def hubspot_contact_association_labels(
        self, info: Info[Context, None]
    ) -> HubSpotAssociationLabelsResult:
        """List available association labels for company-to-contact relationships."""
        user = get_current_user(info)
        if not user.tenant:
            return HubSpotAssociationLabelsResult(
                success=False,
                error="No tenant assigned",
                labels=None,
            )

        service = HubSpotService(user.tenant)
        result = service.list_contact_association_labels()

        labels = None
        if result.get("labels"):
            labels = [
                HubSpotAssociationLabel(
                    type_id=l["type_id"],
                    label=l["label"],
                    category=l["category"],
                )
                for l in result["labels"]
            ]

        return HubSpotAssociationLabelsResult(
            success=result.get("success", False),
            error=result.get("error"),
            labels=labels,
        )

    @strawberry.field
    def m365_settings(self, info: Info[Context, None]) -> M365Settings | None:
        """Get M365 integration settings for current tenant."""
        user = get_current_user(info)
        if not user.tenant:
            return None
        config = (user.tenant.settings or {}).get("m365", {})
        client_id = config.get("client_id", "")
        azure_tid = config.get("tenant_id", "")
        is_configured = bool(
            config.get("tenant_id") and config.get("client_id") and config.get("client_secret")
        )
        return M365Settings(
            is_configured=is_configured,
            sender_mailbox=config.get("sender_mailbox"),
            client_id_masked=f"...{client_id[-4:]}" if len(client_id) > 4 else client_id or None,
            azure_tenant_id_masked=f"...{azure_tid[-4:]}" if len(azure_tid) > 4 else azure_tid or None,
        )

    @strawberry.field
    def smtp_settings(self, info: Info[Context, None]) -> SmtpSettingsType | None:
        """Get SMTP notification settings for current tenant."""
        user = get_current_user(info)
        if not user.tenant:
            return None
        config = (user.tenant.settings or {}).get("smtp", {})
        is_configured = bool(
            all(config.get(k) for k in ("host", "port", "username", "password", "from_address"))
        )
        return SmtpSettingsType(
            host=config.get("host", ""),
            port=config.get("port", 587),
            username=config.get("username", ""),
            from_name=config.get("from_name", ""),
            from_address=config.get("from_address", ""),
            use_tls=config.get("use_tls", True),
            is_configured=is_configured,
            password_set=bool(config.get("password")),
        )

    @strawberry.field
    def banking_settings(self, info: Info[Context, None]) -> BankingSettingsType | None:
        """Get banking fee tolerance settings for current tenant."""
        user = get_current_user(info)
        if not user.tenant:
            return None
        config = (user.tenant.settings or {}).get("banking", {})
        return BankingSettingsType(
            fee_tolerance_fixed=Decimal(config.get("fee_tolerance_fixed", "0")),
            fee_tolerance_percent=Decimal(config.get("fee_tolerance_percent", "0")),
        )

    @strawberry.field
    def forecast_cache_ttl(self, info: Info[Context, None]) -> int:
        """Get forecast cache TTL in minutes for current tenant."""
        user = get_current_user(info)
        if not user.tenant:
            return 60
        return (user.tenant.settings or {}).get("forecast_cache_ttl", 60)

    @strawberry.field
    def notification_preferences(self, info: Info[Context, None]) -> NotificationPreferencesType | None:
        """Get the current user's notification subscription preferences."""
        user = get_current_user(info)
        prefs = user.notification_preferences or {}
        return NotificationPreferencesType(
            todo_assigned=prefs.get("todo_assigned", True) is not False,
            hubspot_new_contract=prefs.get("hubspot_new_contract", True) is not False,
            hubspot_sync_completed=prefs.get("hubspot_sync_completed", True) is not False,
            time_tracking_sync_completed=prefs.get("time_tracking_sync_completed", True) is not False,
        )

    @strawberry.field
    def dashboard_preferences(self, info: Info[Context, None]) -> DashboardPreferencesType:
        """Get the current user's dashboard section visibility preferences."""
        user = get_current_user(info)
        prefs = user.dashboard_preferences or {}
        return DashboardPreferencesType(
            show_contracts=prefs.get("show_contracts", True) is not False,
            show_revenue_goals=prefs.get("show_revenue_goals", True) is not False,
            show_new_business=prefs.get("show_new_business", True) is not False,
            show_price_increase_impact=prefs.get("show_price_increase_impact", True) is not False,
        )

    @strawberry.field
    def help_video_links(self, info: Info[Context, None]) -> list[HelpVideoLinksEntryType]:
        """Get help video links configured for the current tenant."""
        user = get_current_user(info)
        if not user.tenant:
            return []
        config = (user.tenant.settings or {}).get("help_video_links", {})
        return [
            HelpVideoLinksEntryType(
                route_key=route_key,
                links=[
                    HelpVideoLinkType(url=link["url"], label=link.get("label"))
                    for link in links
                ],
            )
            for route_key, links in config.items()
        ]

    @strawberry.field
    def invoice_email_templates(
        self, info: Info[Context, None]
    ) -> InvoiceEmailTemplatesResult:
        """Get invoice email templates (custom or defaults) for all languages."""
        user = get_current_user(info)
        if not user.tenant:
            return InvoiceEmailTemplatesResult(
                success=False, error="No tenant assigned"
            )

        from apps.invoices.tasks import EMAIL_TEMPLATES

        custom = (user.tenant.settings or {}).get("invoice_email_templates", {})
        templates = []
        for lang in ("de", "en"):
            default = EMAIL_TEMPLATES.get(lang, {})
            custom_lang = custom.get(lang, {})
            is_custom = bool(custom_lang.get("subject") and custom_lang.get("body"))
            templates.append(
                InvoiceEmailTemplate(
                    language=lang,
                    subject=custom_lang.get("subject", "") if is_custom else default.get("subject", ""),
                    body=custom_lang.get("body", "") if is_custom else default.get("body", ""),
                    is_custom=is_custom,
                )
            )

        return InvoiceEmailTemplatesResult(success=True, templates=templates)

    @strawberry.field
    def document_email_bcc(
        self, info: Info[Context, None]
    ) -> list[DocumentEmailBccEntry]:
        """Get BCC recipients for all document types. Requires settings.read."""
        user = get_current_user(info)
        if not user.tenant:
            return []

        bcc_settings = (user.tenant.settings or {}).get("document_email_bcc", {})
        return [
            DocumentEmailBccEntry(
                document_type=doc_type,
                recipients=bcc_settings.get(doc_type, []),
            )
            for doc_type in DOCUMENT_BCC_TYPES
        ]


@strawberry.input
class HubSpotCompanyFilterInput:
    """Input for HubSpot company filter."""
    property_name: str  # e.g., "lifecyclestage"
    values: list[str]   # e.g., ["customer", "evangelist"]


@strawberry.type
class TenantMutation:
    @strawberry.mutation
    def save_time_tracking_settings(
        self,
        info: Info[Context, None],
        provider: str,
        api_email: str = "",
        api_key: str = "",
        show_revenue: bool = True,
    ) -> TimeTrackingTestResult:
        """Save time tracking settings and test connection."""
        user = get_current_user(info)
        if not user.tenant:
            return TimeTrackingTestResult(success=False, error="No tenant assigned")

        tenant = user.tenant
        config = tenant.time_tracking_config or {}
        config.update({
            "provider": provider,
            "api_email": api_email,
            "api_key": api_key,
            "show_revenue": show_revenue,
        })
        tenant.time_tracking_config = config
        tenant.save(update_fields=["time_tracking_config"])

        # Test connection
        from apps.contracts.services.time_tracking import get_provider
        tt_provider = get_provider(tenant)
        if not tt_provider:
            return TimeTrackingTestResult(success=False, error="Unknown provider")

        result = tt_provider.test_connection()
        return TimeTrackingTestResult(
            success=result["success"],
            error=result.get("error"),
        )

    @strawberry.mutation
    def update_time_tracking_display(
        self,
        info: Info[Context, None],
        show_revenue: bool,
    ) -> bool:
        """Update time tracking display settings (no credentials required)."""
        user = get_current_user(info)
        if not user.tenant:
            return False

        tenant = user.tenant
        config = tenant.time_tracking_config or {}
        config["show_revenue"] = show_revenue
        tenant.time_tracking_config = config
        tenant.save(update_fields=["time_tracking_config"])
        return True

    @strawberry.mutation
    def save_time_tracking_project_templates(
        self,
        info: Info[Context, None],
        maintenance_template: str = "",
        oneoff_template: str = "",
    ) -> bool:
        """Save project naming templates for time tracking."""
        user = get_current_user(info)
        if not user.tenant:
            return False

        tenant = user.tenant
        config = tenant.time_tracking_config or {}
        config["maintenance_project_template"] = maintenance_template
        config["oneoff_project_template"] = oneoff_template
        tenant.time_tracking_config = config
        tenant.save(update_fields=["time_tracking_config"])
        return True

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
    def sync_hubspot_customers(
        self, info: Info[Context, None], date_range: HubSpotDateRangeInput | None = None,
    ) -> HubSpotSyncResult:
        """Sync customers from HubSpot."""
        user = get_current_user(info)
        if not user.tenant:
            return HubSpotSyncResult(
                success=False, error="No tenant assigned", created=0, updated=0
            )

        service = HubSpotService(user.tenant)
        kwargs = {}
        if date_range:
            kwargs["modified_since"] = date_range.modified_since
            kwargs["modified_until"] = date_range.modified_until
        result = service.sync_companies(**kwargs)

        return HubSpotSyncResult(
            success=result["success"],
            error=result.get("error"),
            created=result.get("created", 0),
            updated=result.get("updated", 0),
            warnings=result.get("errors") or None,
        )

    @strawberry.mutation
    def sync_hubspot_products(
        self, info: Info[Context, None], date_range: HubSpotDateRangeInput | None = None,
    ) -> HubSpotSyncResult:
        """Sync products from HubSpot."""
        user = get_current_user(info)
        if not user.tenant:
            return HubSpotSyncResult(
                success=False, error="No tenant assigned", created=0, updated=0
            )

        service = HubSpotService(user.tenant)
        kwargs = {}
        if date_range:
            kwargs["modified_since"] = date_range.modified_since
            kwargs["modified_until"] = date_range.modified_until
        result = service.sync_products(**kwargs)

        return HubSpotSyncResult(
            success=result["success"],
            error=result.get("error"),
            created=result.get("created", 0),
            updated=result.get("updated", 0),
            warnings=result.get("errors") or None,
        )

    @strawberry.mutation
    def sync_hubspot_deals(
        self, info: Info[Context, None], date_range: HubSpotDateRangeInput | None = None,
    ) -> HubSpotDealSyncResult:
        """Sync closed won deals from HubSpot as contract drafts."""
        user = get_current_user(info)
        if not user.tenant:
            return HubSpotDealSyncResult(
                success=False, error="No tenant assigned", created=0, skipped=0
            )

        service = HubSpotService(user.tenant)
        kwargs = {}
        if date_range:
            kwargs["modified_since"] = date_range.modified_since
            kwargs["modified_until"] = date_range.modified_until
        result = service.sync_deals(**kwargs)

        return HubSpotDealSyncResult(
            success=result["success"],
            error=result.get("error"),
            created=result.get("created", 0),
            skipped=result.get("skipped", 0),
            warnings=result.get("errors") or None,
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
    def set_hubspot_auto_sync(
        self,
        info: Info[Context, None],
        enabled: bool,
    ) -> HubSpotTestResult:
        """Enable or disable automatic HubSpot sync."""
        user = get_current_user(info)
        if not user.tenant:
            return HubSpotTestResult(success=False, error="No tenant assigned")

        tenant = user.tenant
        if not tenant.hubspot_config:
            tenant.hubspot_config = {}

        tenant.hubspot_config["auto_sync_enabled"] = enabled
        tenant.save(update_fields=["hubspot_config"])

        return HubSpotTestResult(success=True, error=None)

    @strawberry.mutation
    def set_hubspot_billing_contact_label(
        self,
        info: Info[Context, None],
        label: str | None,
    ) -> HubSpotTestResult:
        """Set the association label used to identify billing contacts."""
        user = get_current_user(info)
        if not user.tenant:
            return HubSpotTestResult(success=False, error="No tenant assigned")

        tenant = user.tenant
        if not tenant.hubspot_config:
            tenant.hubspot_config = {}

        if label:
            tenant.hubspot_config["billing_contact_label"] = label
        else:
            tenant.hubspot_config.pop("billing_contact_label", None)
        tenant.save(update_fields=["hubspot_config"])

        return HubSpotTestResult(success=True, error=None)

    @strawberry.mutation
    def save_webhook_settings(
        self,
        info: Info[Context, None],
        portal_id: str | None = None,
        sync_mode: str | None = None,
    ) -> HubSpotTestResult:
        """Save HubSpot webhook settings (portal ID, sync mode)."""
        user = get_current_user(info)
        if not user.tenant:
            return HubSpotTestResult(success=False, error="No tenant assigned")

        tenant = user.tenant
        if not tenant.hubspot_config:
            tenant.hubspot_config = {}

        if portal_id is not None:
            tenant.hubspot_config["portal_id"] = portal_id.strip()

        if sync_mode is not None:
            if sync_mode not in ("polling", "webhooks"):
                return HubSpotTestResult(
                    success=False, error="Invalid sync mode. Must be 'polling' or 'webhooks'."
                )
            # Require portal_id to enable webhook mode
            if sync_mode == "webhooks":
                pid = tenant.hubspot_config.get("portal_id", "")
                if not pid:
                    return HubSpotTestResult(
                        success=False,
                        error="Portal ID is required for webhook mode.",
                    )
            tenant.hubspot_config["sync_mode"] = sync_mode

        tenant.save(update_fields=["hubspot_config"])
        return HubSpotTestResult(success=True, error=None)

    @strawberry.mutation
    def set_activation_required_fields(
        self,
        info: Info[Context, None],
        fields: list[str],
    ) -> HubSpotTestResult:
        """Set which contract fields are required before activation."""
        user = get_current_user(info)
        if not user.tenant:
            return HubSpotTestResult(success=False, error="No tenant assigned")

        # Validate field names
        invalid = [f for f in fields if f not in ACTIVATION_CHECKABLE_FIELDS]
        if invalid:
            return HubSpotTestResult(
                success=False,
                error=f"Invalid field names: {', '.join(invalid)}",
            )

        tenant = user.tenant
        if not tenant.settings:
            tenant.settings = {}
        tenant.settings["activation_required_fields"] = fields
        tenant.save(update_fields=["settings"])

        return HubSpotTestResult(success=True, error=None)

    @strawberry.mutation
    def update_help_video_links(
        self,
        info: Info[Context, None],
        entries: list[HelpVideoLinksEntryInput],
    ) -> list[HelpVideoLinksEntryType]:
        """Update help video links for the tenant. Requires settings.write."""
        user = require_perm(info, "settings", "write")
        tenant = user.tenant

        if not tenant.settings:
            tenant.settings = {}

        if not entries:
            tenant.settings.pop("help_video_links", None)
        else:
            tenant.settings["help_video_links"] = {
                entry.route_key: [
                    {"url": link.url, "label": link.label}
                    for link in entry.links
                ]
                for entry in entries
            }
        tenant.save(update_fields=["settings"])

        # Return updated config
        config = tenant.settings.get("help_video_links", {})
        return [
            HelpVideoLinksEntryType(
                route_key=route_key,
                links=[
                    HelpVideoLinkType(url=link["url"], label=link.get("label"))
                    for link in links
                ],
            )
            for route_key, links in config.items()
        ]

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
        """Deactivate a user. Requires users.write."""
        admin, err = check_perm(info, "users", "write")
        if err:
            return OperationResult(success=False, error=err)
        if not admin.tenant:
            return OperationResult(success=False, error="No tenant assigned")

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
        """Reactivate a user. Requires users.write."""
        admin, err = check_perm(info, "users", "write")
        if err:
            return OperationResult(success=False, error=err)
        if not admin.tenant:
            return OperationResult(success=False, error="No tenant assigned")

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
        self,
        info: Info[Context, None],
        email: str,
        base_url: str | None = None,
        role_ids: list[strawberry.ID] | None = None,
    ) -> InvitationResult:
        """Create an invitation for a new user. Requires users.write."""
        admin, err = check_perm(info, "users", "write")
        if err:
            return InvitationResult(success=False, error=err)
        if not admin.tenant:
            return InvitationResult(success=False, error="No tenant assigned")

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

        # Resolve role IDs (default to Manager role if none provided)
        if role_ids:
            roles = list(Role.objects.filter(id__in=role_ids, tenant=admin.tenant))
            if len(roles) != len(role_ids):
                return InvitationResult(success=False, error="One or more roles not found")
            stored_role_ids = [r.id for r in roles]
        else:
            manager_role = Role.objects.filter(tenant=admin.tenant, name="Manager").first()
            stored_role_ids = [manager_role.id] if manager_role else []

        invitation = UserInvitation.create_invitation(
            tenant=admin.tenant,
            email=email,
            created_by=admin,
        )
        invitation.role_ids = stored_role_ids
        invitation.save(update_fields=["role_ids"])

        request = info.context.request
        origin = request.headers.get("Origin") or request.headers.get("Referer", "").rstrip("/")
        url_base = base_url or origin or getattr(settings, "FRONTEND_URL", "http://localhost:5173")
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
        """Revoke a pending invitation. Requires users.write."""
        admin, err = check_perm(info, "users", "write")
        if err:
            return OperationResult(success=False, error=err)
        if not admin.tenant:
            return OperationResult(success=False, error="No tenant assigned")

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
        new_user = User.objects.create_user(
            email=invitation.email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            tenant=invitation.tenant,
            is_active=True,
        )

        # Assign roles from invitation
        if invitation.role_ids:
            roles = Role.objects.filter(id__in=invitation.role_ids, tenant=invitation.tenant)
            new_user.roles.set(roles)

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
        """Create a password reset link for a user. Requires users.write."""
        admin, err = check_perm(info, "users", "write")
        if err:
            return ResetLinkResult(success=False, error=err)
        if not admin.tenant:
            return ResetLinkResult(success=False, error="No tenant assigned")

        try:
            target_user = User.objects.get(id=user_id, tenant=admin.tenant)
        except User.DoesNotExist:
            return ResetLinkResult(success=False, error="User not found")

        reset_token = PasswordResetToken.create_token(target_user)
        request = info.context.request
        origin = request.headers.get("Origin") or request.headers.get("Referer", "").rstrip("/")
        url_base = base_url or origin or getattr(settings, "FRONTEND_URL", "http://localhost:5173")
        reset_url = f"{url_base}/reset-password/{reset_token.token}"

        # Also send email if SMTP is configured (non-blocking)
        try:
            from apps.tenants.tasks import send_password_reset_email
            send_password_reset_email.delay(target_user.id, reset_url)
        except Exception:
            pass  # Admin still gets the copyable link

        return ResetLinkResult(success=True, reset_url=reset_url)

    @strawberry.mutation
    def request_password_reset(self, info: Info[Context, None], email: str) -> OperationResult:
        """Request a password reset email. Public (no auth required)."""
        from django.core.cache import cache
        from apps.tenants.tasks import send_password_reset_email

        # Rate limiting: max 5 requests per email per 15 minutes
        cache_key = f"password_reset:{email.lower()}"
        request_count = cache.get(cache_key, 0)
        if request_count >= 5:
            return OperationResult(success=True)  # Silent discard

        cache.set(cache_key, request_count + 1, timeout=900)  # 15 min TTL

        try:
            user = User.objects.select_related("tenant").get(email__iexact=email, is_active=True)
        except User.DoesNotExist:
            return OperationResult(success=True)  # Prevent enumeration

        reset_token = PasswordResetToken.create_token(user)
        request = info.context.request
        origin = request.headers.get("Origin") or request.headers.get("Referer", "").rstrip("/")
        url_base = origin or getattr(settings, "FRONTEND_URL", "http://localhost:5173")
        reset_url = f"{url_base}/reset-password/{reset_token.token}"

        send_password_reset_email.delay(user.id, reset_url)
        return OperationResult(success=True)

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

    # Two-Factor Authentication Mutations

    @strawberry.mutation
    def setup_totp(self, info: Info[Context, None]) -> TotpSetupResult:
        """Initiate TOTP 2FA setup. Returns secret and provisioning URI."""
        import pyotp
        user = get_current_user(info, allow_2fa_setup=True)
        if not user:
            return TotpSetupResult(success=False, error="Not authenticated")

        secret = pyotp.random_base32()
        totp = pyotp.TOTP(secret)
        provisioning_uri = totp.provisioning_uri(
            name=user.email,
            issuer_name=user.tenant.name if user.tenant else "Contract Manager",
        )

        # Store pending config (not yet active)
        config, _ = TwoFactorConfig.objects.get_or_create(
            user=user, defaults={"method": "totp"}
        )
        config.method = "totp"
        config.set_totp_secret(secret)
        config.is_active = False
        config.save()

        return TotpSetupResult(
            success=True,
            secret=secret,
            provisioning_uri=provisioning_uri,
        )

    @strawberry.mutation
    def confirm_totp(self, info: Info[Context, None], code: str) -> TwoFactorConfirmResult:
        """Confirm TOTP setup with a verification code. Activates 2FA and returns recovery codes."""
        import pyotp
        user = get_current_user(info, allow_2fa_setup=True)
        if not user:
            return TwoFactorConfirmResult(success=False, error="Not authenticated")

        try:
            config = user.two_factor_config
        except TwoFactorConfig.DoesNotExist:
            return TwoFactorConfirmResult(success=False, error="No TOTP setup in progress")

        if config.is_active:
            return TwoFactorConfirmResult(success=False, error="2FA is already active")

        if not config.totp_secret_encrypted:
            return TwoFactorConfirmResult(success=False, error="No TOTP setup in progress")

        secret = config.get_totp_secret()
        totp = pyotp.TOTP(secret)
        if not totp.verify(code.strip(), valid_window=1):
            return TwoFactorConfirmResult(success=False, error="Invalid verification code")

        # Activate and generate recovery codes
        plaintext_codes, hashed_codes = TwoFactorConfig.generate_recovery_codes()
        config.is_active = True
        config.recovery_codes_hashed = hashed_codes
        config.save()

        return TwoFactorConfirmResult(success=True, recovery_codes=plaintext_codes)

    @strawberry.mutation
    def enable_email_2fa(self, info: Info[Context, None]) -> TwoFactorConfirmResult:
        """Enable email-based 2FA."""
        from apps.core.smtp import SmtpError, _get_config
        user = get_current_user(info, allow_2fa_setup=True)
        if not user:
            return TwoFactorConfirmResult(success=False, error="Not authenticated")
        if not user.tenant:
            return TwoFactorConfirmResult(success=False, error="No tenant assigned")

        # Check SMTP is configured
        try:
            _get_config(user.tenant)
        except SmtpError:
            return TwoFactorConfirmResult(success=False, error="Email 2FA not available — SMTP not configured")

        config, _ = TwoFactorConfig.objects.get_or_create(
            user=user, defaults={"method": "email"}
        )
        config.method = "email"
        config.totp_secret_encrypted = ""
        config.is_active = True

        # Generate recovery codes
        plaintext_codes, hashed_codes = TwoFactorConfig.generate_recovery_codes()
        config.recovery_codes_hashed = hashed_codes
        config.save()

        return TwoFactorConfirmResult(success=True, recovery_codes=plaintext_codes)

    @strawberry.mutation
    def disable_2fa(self, info: Info[Context, None], password: str) -> OperationResult:
        """Disable 2FA for the current user. Requires password confirmation."""
        user = get_current_user(info)
        if not user:
            return OperationResult(success=False, error="Not authenticated")

        if not check_password(password, user.password):
            return OperationResult(success=False, error="Incorrect password")

        # Check enforcement
        if user.tenant and (user.tenant.settings or {}).get("two_factor_enforced"):
            return OperationResult(success=False, error="2FA is required by your organization")

        try:
            user.two_factor_config.delete()
        except TwoFactorConfig.DoesNotExist:
            pass

        return OperationResult(success=True)

    @strawberry.mutation
    def regenerate_recovery_codes(self, info: Info[Context, None], password: str) -> TwoFactorConfirmResult:
        """Regenerate recovery codes. Requires password confirmation."""
        user = get_current_user(info)
        if not user:
            return TwoFactorConfirmResult(success=False, error="Not authenticated")

        if not check_password(password, user.password):
            return TwoFactorConfirmResult(success=False, error="Incorrect password")

        try:
            config = user.two_factor_config
        except TwoFactorConfig.DoesNotExist:
            return TwoFactorConfirmResult(success=False, error="2FA not enabled")

        if not config.is_active:
            return TwoFactorConfirmResult(success=False, error="2FA not active")

        plaintext_codes, hashed_codes = TwoFactorConfig.generate_recovery_codes()
        config.recovery_codes_hashed = hashed_codes
        config.save(update_fields=["recovery_codes_hashed"])

        return TwoFactorConfirmResult(success=True, recovery_codes=plaintext_codes)

    @strawberry.mutation
    def update_tenant_name(self, info: Info[Context, None], name: str) -> OperationResult:
        """Update the tenant name. Requires settings.write."""
        user, err = check_perm(info, "settings", "write")
        if err:
            return OperationResult(success=False, error=err)
        if not user.tenant:
            return OperationResult(success=False, error="No tenant assigned")

        name = name.strip()
        if not name:
            return OperationResult(success=False, error="Name cannot be empty")

        tenant = user.tenant
        tenant.name = name
        tenant.save(update_fields=["name"])

        return OperationResult(success=True)

    @strawberry.mutation
    def set_payment_delay_days(self, info: Info[Context, None], days: int) -> OperationResult:
        """Set the expected payment delay (days between invoice and payment arrival). Requires settings.write."""
        user, err = check_perm(info, "settings", "write")
        if err:
            return OperationResult(success=False, error=err)
        if not user.tenant:
            return OperationResult(success=False, error="No tenant assigned")
        if days < 0 or days > 365:
            return OperationResult(success=False, error="Days must be between 0 and 365")

        tenant = user.tenant
        s = tenant.settings or {}
        s["payment_delay_days"] = days
        tenant.settings = s
        tenant.save(update_fields=["settings"])

        return OperationResult(success=True)

    @strawberry.mutation
    def set_tenant_2fa_enforcement(self, info: Info[Context, None], enforced: bool) -> OperationResult:
        """Enable or disable 2FA enforcement for the tenant. Requires settings.write."""
        user, err = check_perm(info, "settings", "write")
        if err:
            return OperationResult(success=False, error=err)
        if not user.tenant:
            return OperationResult(success=False, error="No tenant assigned")

        tenant = user.tenant
        s = tenant.settings or {}
        s["two_factor_enforced"] = enforced
        tenant.settings = s
        tenant.save(update_fields=["settings"])

        return OperationResult(success=True)

    @strawberry.mutation
    def update_fte_snapshot_settings(
        self,
        info: Info[Context, None],
        capture_day: int | None = None,
        notification_email: str | None = strawberry.UNSET,
    ) -> OperationResult:
        """Update FTE snapshot settings. Requires cost_centers.config."""
        user, err = check_perm(info, "cost_centers", "config")
        if err:
            return OperationResult(success=False, error=err)
        if not user.tenant:
            return OperationResult(success=False, error="No tenant assigned")

        tenant = user.tenant
        s = tenant.settings or {}

        if capture_day is not None:
            if capture_day < 1 or capture_day > 28:
                return OperationResult(success=False, error="Capture day must be between 1 and 28")
            s["fte_snapshot_capture_day"] = capture_day

        if notification_email is not strawberry.UNSET:
            s["fte_snapshot_notification_email"] = notification_email

        tenant.settings = s
        tenant.save(update_fields=["settings"])
        return OperationResult(success=True)

    @strawberry.mutation
    def reset_user_2fa(self, info: Info[Context, None], user_id: strawberry.ID) -> OperationResult:
        """Reset 2FA for a user. Requires users.write."""
        admin, err = check_perm(info, "users", "write")
        if err:
            return OperationResult(success=False, error=err)
        if not admin.tenant:
            return OperationResult(success=False, error="No tenant assigned")

        try:
            target_user = User.objects.get(id=user_id, tenant=admin.tenant)
        except User.DoesNotExist:
            return OperationResult(success=False, error="User not found")

        try:
            target_user.two_factor_config.delete()
        except TwoFactorConfig.DoesNotExist:
            pass

        return OperationResult(success=True)

    # Role Management Mutations

    @strawberry.mutation
    def create_role(
        self, info: Info[Context, None], name: str, permissions: strawberry.scalars.JSON | None = None
    ) -> RoleResult:
        """Create a new custom role. Requires settings.write."""
        user, err = check_perm(info, "settings", "write")
        if err:
            return RoleResult(success=False, error=err)
        if not user.tenant:
            return RoleResult(success=False, error="No tenant assigned")

        name = name.strip()
        if not name:
            return RoleResult(success=False, error="Role name is required")

        if Role.objects.filter(tenant=user.tenant, name=name).exists():
            return RoleResult(success=False, error="A role with this name already exists")

        # Normalize and validate permission keys
        perms = normalize_permissions(permissions or {})

        role = Role.objects.create(
            tenant=user.tenant,
            name=name,
            permissions=perms,
            is_system=False,
        )
        return RoleResult(
            success=True,
            role=RoleType(
                id=role.id,
                name=role.name,
                is_system=role.is_system,
                permissions=role.permissions or {},
                user_count=0,
            ),
        )

    @strawberry.mutation
    def update_role_permissions(
        self, info: Info[Context, None], role_id: strawberry.ID, permissions: strawberry.scalars.JSON
    ) -> RoleResult:
        """Update permissions for a role. Requires settings.write."""
        user, err = check_perm(info, "settings", "write")
        if err:
            return RoleResult(success=False, error=err)
        if not user.tenant:
            return RoleResult(success=False, error="No tenant assigned")

        try:
            role = Role.objects.get(id=role_id, tenant=user.tenant)
        except Role.DoesNotExist:
            return RoleResult(success=False, error="Role not found")

        # Normalize and validate permission keys
        perms = normalize_permissions(permissions)

        # Protect Admin role: cannot remove protected permissions
        if role.name == "Admin" and role.is_system:
            for perm in ADMIN_PROTECTED_PERMISSIONS:
                if not perms.get(perm, False):
                    return RoleResult(
                        success=False,
                        error=f"Cannot remove protected permission '{perm}' from Admin role",
                    )

        role.permissions = perms
        role.save(update_fields=["permissions"])

        return RoleResult(
            success=True,
            role=RoleType(
                id=role.id,
                name=role.name,
                is_system=role.is_system,
                permissions=role.permissions or {},
                user_count=role.users.count(),
            ),
        )

    @strawberry.mutation
    def delete_role(
        self, info: Info[Context, None], role_id: strawberry.ID
    ) -> OperationResult:
        """Delete a custom role. Requires settings.write."""
        user, err = check_perm(info, "settings", "write")
        if err:
            return OperationResult(success=False, error=err)
        if not user.tenant:
            return OperationResult(success=False, error="No tenant assigned")

        try:
            role = Role.objects.get(id=role_id, tenant=user.tenant)
        except Role.DoesNotExist:
            return OperationResult(success=False, error="Role not found")

        if role.is_system:
            return OperationResult(success=False, error="Cannot delete a system role")

        if role.users.exists():
            return OperationResult(success=False, error="Cannot delete a role that has assigned users")

        role.delete()
        return OperationResult(success=True)

    @strawberry.mutation
    def assign_user_roles(
        self, info: Info[Context, None], user_id: strawberry.ID, role_ids: list[strawberry.ID]
    ) -> OperationResult:
        """Set roles for a user. Requires users.write."""
        admin, err = check_perm(info, "users", "write")
        if err:
            return OperationResult(success=False, error=err)
        if not admin.tenant:
            return OperationResult(success=False, error="No tenant assigned")

        try:
            target_user = User.objects.prefetch_related("roles").get(id=user_id, tenant=admin.tenant)
        except User.DoesNotExist:
            return OperationResult(success=False, error="User not found")

        # Validate all role IDs belong to the tenant
        new_roles = list(Role.objects.filter(id__in=role_ids, tenant=admin.tenant))
        if len(new_roles) != len(role_ids):
            return OperationResult(success=False, error="One or more roles not found")

        # Prevent removing Admin role from the last admin
        admin_role = Role.objects.filter(tenant=admin.tenant, name="Admin", is_system=True).first()
        if admin_role:
            has_admin_now = target_user.roles.filter(id=admin_role.id).exists()
            will_have_admin = admin_role.id in [r.id for r in new_roles]
            if has_admin_now and not will_have_admin:
                # Count other users who still have Admin role
                other_admins = admin_role.users.exclude(id=target_user.id).filter(is_active=True).count()
                if other_admins == 0:
                    return OperationResult(
                        success=False,
                        error="Cannot remove Admin role from the last admin user",
                    )

        target_user.roles.set(new_roles)
        return OperationResult(success=True)

    # M365 Integration Mutations

    @strawberry.mutation
    def save_m365_settings(
        self,
        info: Info[Context, None],
        azure_tenant_id: str,
        client_id: str,
        client_secret: str,
    ) -> OperationResult:
        """Save M365 credentials. Requires settings.write."""
        user = require_perm(info, "settings", "write")
        tenant = user.tenant
        if not tenant:
            return OperationResult(success=False, error="No tenant assigned")

        if not tenant.settings:
            tenant.settings = {}

        existing = tenant.settings.get("m365", {})
        tenant.settings["m365"] = {
            "tenant_id": azure_tenant_id.strip() or existing.get("tenant_id", ""),
            "client_id": client_id.strip() or existing.get("client_id", ""),
            "client_secret": client_secret.strip() or existing.get("client_secret", ""),
            "sender_mailbox": existing.get("sender_mailbox", ""),
        }
        tenant.save(update_fields=["settings"])
        return OperationResult(success=True)

    @strawberry.mutation
    def test_m365_connection(self, info: Info[Context, None]) -> M365TestResult:
        """Test M365 connection with stored credentials."""
        user = get_current_user(info)
        if not user.tenant:
            return M365TestResult(success=False, error="No tenant assigned")

        from apps.core.m365 import M365Error, test_connection
        try:
            result = test_connection(user.tenant)
            return M365TestResult(
                success=True,
                organization=result.get("organization"),
            )
        except M365Error as e:
            return M365TestResult(success=False, error=str(e))

    @strawberry.mutation
    def discover_m365_mailboxes(self, info: Info[Context, None]) -> M365MailboxesResult:
        """Discover available mailboxes from M365."""
        user = get_current_user(info)
        if not user.tenant:
            return M365MailboxesResult(success=False, error="No tenant assigned")

        from apps.core.m365 import M365Error, list_mailboxes
        try:
            mailboxes = list_mailboxes(user.tenant)
            return M365MailboxesResult(
                success=True,
                mailboxes=[
                    M365MailboxType(email=m["email"], display_name=m["display_name"])
                    for m in mailboxes
                ],
            )
        except M365Error as e:
            return M365MailboxesResult(success=False, error=str(e))

    @strawberry.mutation
    def send_m365_test_email(self, info: Info[Context, None]) -> OperationResult:
        """Send a test email via M365 to verify end-to-end configuration."""
        user = require_perm(info, "settings", "write")
        if not user.tenant:
            return OperationResult(success=False, error="No tenant assigned")

        from apps.core.m365 import M365Error, send_mail
        try:
            send_mail(
                user.tenant,
                to=[user.email],
                subject="Test Email from Contract Manager",
                body_html="<p>This is a test email sent from Contract Manager via Microsoft 365.</p>"
                          "<p>If you received this, your M365 email integration is working correctly.</p>",
            )
            return OperationResult(success=True)
        except M365Error as e:
            return OperationResult(success=False, error=str(e))

    @strawberry.mutation
    def select_m365_mailbox(
        self,
        info: Info[Context, None],
        mailbox: str,
    ) -> OperationResult:
        """Select a sender mailbox for M365 email sending."""
        user = require_perm(info, "settings", "write")
        tenant = user.tenant
        if not tenant:
            return OperationResult(success=False, error="No tenant assigned")

        config = (tenant.settings or {}).get("m365", {})
        if not config.get("client_id"):
            return OperationResult(success=False, error="M365 not configured")

        config["sender_mailbox"] = mailbox.strip()
        if not tenant.settings:
            tenant.settings = {}
        tenant.settings["m365"] = config
        tenant.save(update_fields=["settings"])
        return OperationResult(success=True)

    @strawberry.mutation
    def save_smtp_settings(
        self,
        info: Info[Context, None],
        host: str,
        port: int,
        username: str,
        password: str,
        from_name: str,
        from_address: str,
        use_tls: bool = True,
    ) -> OperationResult:
        """Save SMTP notification settings. Requires settings.write."""
        user = require_perm(info, "settings", "write")
        tenant = user.tenant
        if not tenant:
            return OperationResult(success=False, error="No tenant assigned")

        if not tenant.settings:
            tenant.settings = {}

        existing = tenant.settings.get("smtp", {})
        tenant.settings["smtp"] = {
            "host": host.strip(),
            "port": port,
            "username": username.strip(),
            "password": password.strip() or existing.get("password", ""),
            "from_name": from_name.strip(),
            "from_address": from_address.strip(),
            "use_tls": use_tls,
        }
        tenant.save(update_fields=["settings"])
        return OperationResult(success=True)

    @strawberry.mutation
    def save_banking_settings(
        self,
        info: Info[Context, None],
        fee_tolerance_fixed: Decimal,
        fee_tolerance_percent: Decimal,
    ) -> OperationResult:
        """Save banking fee tolerance settings. Requires settings.write."""
        user = require_perm(info, "settings", "write")
        tenant = user.tenant
        if not tenant:
            return OperationResult(success=False, error="No tenant assigned")
        if fee_tolerance_fixed < 0 or fee_tolerance_percent < 0:
            return OperationResult(success=False, error="Tolerance values must be >= 0")
        if not tenant.settings:
            tenant.settings = {}
        tenant.settings["banking"] = {
            "fee_tolerance_fixed": str(fee_tolerance_fixed),
            "fee_tolerance_percent": str(fee_tolerance_percent),
        }
        tenant.save(update_fields=["settings"])
        return OperationResult(success=True)

    @strawberry.mutation
    def save_forecast_cache_ttl(
        self,
        info: Info[Context, None],
        minutes: int,
    ) -> OperationResult:
        """Save forecast cache TTL in minutes. Requires settings.write."""
        user = require_perm(info, "settings", "write")
        tenant = user.tenant
        if not tenant:
            return OperationResult(success=False, error="No tenant assigned")
        if minutes < 1:
            return OperationResult(success=False, error="TTL must be at least 1 minute")
        if not tenant.settings:
            tenant.settings = {}
        tenant.settings["forecast_cache_ttl"] = minutes
        tenant.save(update_fields=["settings"])
        return OperationResult(success=True)

    @strawberry.mutation
    def test_smtp_connection(self, info: Info[Context, None]) -> OperationResult:
        """Test SMTP connection with stored credentials."""
        user = require_perm(info, "settings", "write")
        if not user.tenant:
            return OperationResult(success=False, error="No tenant assigned")

        from apps.core.smtp import SmtpError, test_connection
        try:
            test_connection(user.tenant)
            return OperationResult(success=True)
        except SmtpError as e:
            return OperationResult(success=False, error=str(e))

    @strawberry.mutation
    def send_smtp_test_email(self, info: Info[Context, None]) -> OperationResult:
        """Send a test notification email via SMTP to the current user."""
        user = require_perm(info, "settings", "write")
        if not user.tenant:
            return OperationResult(success=False, error="No tenant assigned")

        from apps.core.smtp import SmtpError, send_notification
        try:
            send_notification(
                user.tenant,
                to=[user.email],
                subject="Test Notification from Contract Manager",
                body_html="<p>This is a test notification sent from Contract Manager via SMTP.</p>"
                          "<p>If you received this, your SMTP notification service is working correctly.</p>",
            )
            return OperationResult(success=True)
        except SmtpError as e:
            return OperationResult(success=False, error=str(e))

    @strawberry.mutation
    def update_notification_preferences(
        self,
        info: Info[Context, None],
        todo_assigned: bool | None = None,
        hubspot_new_contract: bool | None = None,
        hubspot_sync_completed: bool | None = None,
        time_tracking_sync_completed: bool | None = None,
    ) -> OperationResult:
        """Update the current user's notification preferences."""
        user = get_current_user(info)
        prefs = user.notification_preferences or {}

        if todo_assigned is not None:
            prefs["todo_assigned"] = todo_assigned
        if hubspot_new_contract is not None:
            prefs["hubspot_new_contract"] = hubspot_new_contract
        if hubspot_sync_completed is not None:
            prefs["hubspot_sync_completed"] = hubspot_sync_completed
        if time_tracking_sync_completed is not None:
            prefs["time_tracking_sync_completed"] = time_tracking_sync_completed

        user.notification_preferences = prefs
        user.save(update_fields=["notification_preferences"])
        return OperationResult(success=True)

    @strawberry.mutation
    def update_dashboard_preferences(
        self,
        info: Info[Context, None],
        show_contracts: bool | None = None,
        show_revenue_goals: bool | None = None,
        show_new_business: bool | None = None,
        show_price_increase_impact: bool | None = None,
    ) -> OperationResult:
        """Update the current user's dashboard section visibility preferences."""
        user = get_current_user(info)
        prefs = user.dashboard_preferences or {}

        if show_contracts is not None:
            prefs["show_contracts"] = show_contracts
        if show_revenue_goals is not None:
            prefs["show_revenue_goals"] = show_revenue_goals
        if show_new_business is not None:
            prefs["show_new_business"] = show_new_business
        if show_price_increase_impact is not None:
            prefs["show_price_increase_impact"] = show_price_increase_impact

        user.dashboard_preferences = prefs
        user.save(update_fields=["dashboard_preferences"])
        return OperationResult(success=True)

    @strawberry.mutation
    def set_invoice_email_template(
        self,
        info: Info[Context, None],
        input: SetInvoiceEmailTemplateInput,
    ) -> OperationResult:
        """Save or clear a custom invoice email template for a language. Requires settings.write."""
        user = require_perm(info, "settings", "write")
        tenant = user.tenant
        if not tenant:
            return OperationResult(success=False, error="No tenant assigned")

        if input.language not in ("de", "en"):
            return OperationResult(success=False, error="Unsupported language")

        if not tenant.settings:
            tenant.settings = {}

        templates = tenant.settings.get("invoice_email_templates", {})

        if input.subject.strip() and input.body.strip():
            templates[input.language] = {
                "subject": input.subject.strip(),
                "body": input.body.strip(),
            }
        else:
            templates.pop(input.language, None)

        if templates:
            tenant.settings["invoice_email_templates"] = templates
        else:
            tenant.settings.pop("invoice_email_templates", None)

        tenant.save(update_fields=["settings"])
        return OperationResult(success=True)

    @strawberry.mutation
    def set_document_email_bcc(
        self,
        info: Info[Context, None],
        input: SetDocumentEmailBccInput,
    ) -> OperationResult:
        """Set BCC recipients for a document type. Requires settings.write."""
        user = require_perm(info, "settings", "write")
        tenant = user.tenant
        if not tenant:
            return OperationResult(success=False, error="No tenant assigned")

        if input.document_type not in DOCUMENT_BCC_TYPES:
            return OperationResult(
                success=False,
                error=f"Invalid document type. Must be one of: {', '.join(DOCUMENT_BCC_TYPES)}",
            )

        if not tenant.settings:
            tenant.settings = {}

        bcc_settings = tenant.settings.get("document_email_bcc", {})
        cleaned = [addr.strip().lower() for addr in input.recipients if addr.strip()]
        if cleaned:
            bcc_settings[input.document_type] = cleaned
        else:
            bcc_settings.pop(input.document_type, None)

        if bcc_settings:
            tenant.settings["document_email_bcc"] = bcc_settings
        else:
            tenant.settings.pop("document_email_bcc", None)

        tenant.save(update_fields=["settings"])
        return OperationResult(success=True)

    @strawberry.mutation
    def sign_up(
        self,
        company_name: str,
        email: str,
        first_name: str,
        last_name: str,
        password: str,
        base_url: str = "",
    ) -> OperationResult:
        """Create a new tenant and user, send verification email."""
        from django.conf import settings as django_settings
        from django.core.cache import cache
        from django.core.validators import validate_email
        from django.core.exceptions import ValidationError
        from django.db import transaction

        if not django_settings.SIGNUP_ENABLED:
            return OperationResult(success=False, error="Signup is currently disabled")

        # Validate inputs
        company_name = company_name.strip()
        email = email.strip().lower()
        first_name = first_name.strip()
        last_name = last_name.strip()

        if not company_name:
            return OperationResult(success=False, error="Company name is required")

        try:
            validate_email(email)
        except ValidationError:
            return OperationResult(success=False, error="Invalid email address")

        if len(password) < 8:
            return OperationResult(success=False, error="Password must be at least 8 characters")

        # Rate limit: 5 per email per hour
        rate_key = f"signup_rate:{email}"
        attempts = cache.get(rate_key, 0)
        if attempts >= 5:
            return OperationResult(success=False, error="Too many signup attempts. Please try again later.")
        cache.set(rate_key, attempts + 1, timeout=3600)

        # Check email uniqueness (generic error to avoid leaking info)
        if User.objects.filter(email=email).exists():
            return OperationResult(success=False, error="Unable to create account. Please try again or sign in.")

        try:
            with transaction.atomic():
                # Create inactive tenant (roles seeded by post_save signal)
                tenant = Tenant.objects.create(
                    name=company_name,
                    is_active=False,
                )

                # Create inactive user
                user = User.objects.create_user(
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                    tenant=tenant,
                    is_active=False,
                )

                # Assign Admin role
                admin_role = Role.objects.filter(tenant=tenant, name="Admin").first()
                if admin_role:
                    user.roles.add(admin_role)

                # Create verification token
                verification = SignupVerification.create_token(tenant=tenant, user=user)

            # Send verification email (outside transaction)
            from apps.tenants.tasks import send_signup_verification_email
            send_signup_verification_email.delay(verification.id, base_url or "")

            return OperationResult(success=True)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error("Signup failed: %s", e)
            return OperationResult(success=False, error="Unable to create account. Please try again.")

    @strawberry.mutation
    def verify_signup(self, token: str) -> "SignupVerifyResult":
        """Verify a signup token and activate tenant + user."""
        from apps.core.auth import create_access_token, create_refresh_token

        try:
            verification = SignupVerification.objects.select_related("tenant", "user").get(token=token)
        except SignupVerification.DoesNotExist:
            return SignupVerifyResult(success=False, error="Invalid verification link")

        if verification.used:
            return SignupVerifyResult(success=False, error="This link has already been used. Please sign in.")

        if verification.is_expired:
            return SignupVerifyResult(success=False, error="This verification link has expired. Please sign up again.")

        # Activate tenant and user
        verification.tenant.is_active = True
        verification.tenant.save(update_fields=["is_active"])

        verification.user.is_active = True
        verification.user.save(update_fields=["is_active"])

        verification.used = True
        verification.save(update_fields=["used"])

        # Auto-login: return tokens
        access_token = create_access_token(verification.user)
        refresh_token = create_refresh_token(verification.user)

        return SignupVerifyResult(
            success=True,
            access_token=access_token,
            refresh_token=refresh_token,
        )
