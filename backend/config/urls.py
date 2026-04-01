"""URL configuration for contract-manager project."""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from django.views.decorators.csrf import csrf_exempt

from apps.core.context import get_context
from .schema import schema


def health_check(request):
    return JsonResponse({"status": "ok"})


# Import GraphQLView and create custom view with context
from strawberry.django.views import GraphQLView


class AuthenticatedGraphQLView(GraphQLView):
    def get_context(self, request, response):
        return get_context(request)


from apps.core.version_views import VersionView, BackendLicensesView
from apps.invoices.views import InvoiceExportView, InvoicePreviewHtmlView, InvoicePreviewView, InvoiceRecordPdfView
from apps.offers.views import OfferRecordPdfView
from apps.contracts.views import AttachmentDownloadView, AttachmentPermalinkView, ContractExportView
from apps.customers.views import CustomerAttachmentDownloadView
from apps.banking.views import UploadStatementView
from apps.customers.webhooks import HubSpotWebhookView
from apps.mcp.views import DynamicClientRegistrationView, McpAuthorizationView, OAuthMetadataView, ProtectedResourceMetadataView

urlpatterns = [
    path("accounts/", include("django.contrib.auth.urls")),
    path("admin/", admin.site.urls),
    path("graphql", csrf_exempt(AuthenticatedGraphQLView.as_view(schema=schema))),
    # OAuth 2.1 endpoints (django-oauth-toolkit)
    # Custom authorize view handles URL-based client_id (MCP metadata document flow)
    path("oauth/authorize/", McpAuthorizationView.as_view(), name="oauth-authorize"),
    path("oauth/", include("oauth2_provider.urls", namespace="oauth2_provider")),
    path("oauth/register/", csrf_exempt(DynamicClientRegistrationView.as_view()), name="oauth-register"),
    # OAuth metadata discovery (RFC 8414 + RFC 9728)
    path(".well-known/oauth-authorization-server", OAuthMetadataView.as_view(), name="oauth-metadata"),
    path(".well-known/oauth-protected-resource", ProtectedResourceMetadataView.as_view(), name="oauth-protected-resource"),
    path(".well-known/oauth-protected-resource/mcp", ProtectedResourceMetadataView.as_view(), name="oauth-protected-resource-mcp"),
    # MCP server endpoint
    path("", include("mcp_server.urls")),
    path("api/health", health_check),
    path("api/version/", VersionView.as_view(), name="version"),
    path("api/version/licenses/", BackendLicensesView.as_view(), name="version-licenses"),
    path("api/invoices/export/", InvoiceExportView.as_view(), name="invoice-export"),
    path("api/invoices/preview/", InvoicePreviewView.as_view(), name="invoice-preview"),
    path("api/invoices/preview-html/", InvoicePreviewHtmlView.as_view(), name="invoice-preview-html"),
    path("api/invoices/<int:record_id>/pdf/", InvoiceRecordPdfView.as_view(), name="invoice-record-pdf"),
    path("api/offers/<int:record_id>/pdf/", OfferRecordPdfView.as_view(), name="offer-record-pdf"),
    path("api/contracts/export/", ContractExportView.as_view(), name="contract-export"),
    path("api/attachments/<int:attachment_id>/download/", AttachmentDownloadView.as_view(), name="attachment-download"),
    path("api/attachments/<int:attachment_id>/permalink/", AttachmentPermalinkView.as_view(), name="attachment-permalink"),
    path("api/customer-attachments/<int:attachment_id>/download/", CustomerAttachmentDownloadView.as_view(), name="customer-attachment-download"),
    path("api/banking/upload/<int:account_id>/", UploadStatementView.as_view(), name="banking-upload"),
    path("api/hubspot/webhook/", HubSpotWebhookView.as_view(), name="hubspot-webhook"),
    path("api/assistant/", include("apps.assistant.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
