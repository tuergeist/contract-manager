"""URL configuration for contract-manager project."""
from django.contrib import admin
from django.http import JsonResponse
from django.urls import path
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


from apps.invoices.views import InvoiceExportView
from apps.contracts.views import AttachmentDownloadView
from apps.customers.views import CustomerAttachmentDownloadView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("graphql", csrf_exempt(AuthenticatedGraphQLView.as_view(schema=schema))),
    path("api/health", health_check),
    path("api/invoices/export/", InvoiceExportView.as_view(), name="invoice-export"),
    path("api/attachments/<int:attachment_id>/download/", AttachmentDownloadView.as_view(), name="attachment-download"),
    path("api/customer-attachments/<int:attachment_id>/download/", CustomerAttachmentDownloadView.as_view(), name="customer-attachment-download"),
]
