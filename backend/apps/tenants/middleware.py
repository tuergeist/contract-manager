"""Tenant middleware for multi-tenant support."""
from django.utils.deprecation import MiddlewareMixin


class TenantMiddleware(MiddlewareMixin):
    """Middleware to set current tenant on request."""

    def process_request(self, request):
        """Add tenant to request based on authenticated user."""
        if hasattr(request, "user") and request.user.is_authenticated:
            request.tenant = getattr(request.user, "tenant", None)
        else:
            request.tenant = None
