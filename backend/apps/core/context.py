"""GraphQL context for request handling."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from django.http import HttpRequest
from django.utils import timezone
from strawberry.django.views import AsyncGraphQLView

from apps.core.auth import decode_token, get_user_from_token
from apps.tenants.models import User

if TYPE_CHECKING:
    from apps.tenants.models import APIKey


@dataclass
class Context:
    """GraphQL request context."""

    request: HttpRequest
    user: User | None = None
    token_scope: str | None = None
    api_key: APIKey | None = None

    @property
    def is_authenticated(self) -> bool:
        return self.user is not None

    @property
    def is_2fa_setup_restricted(self) -> bool:
        """True when user has a restricted 2FA-setup-only token."""
        return self.token_scope == "2fa_setup"


def get_context(request: HttpRequest) -> Context:
    """Extract context from request, including authenticated user."""
    user = None
    token_scope = None
    api_key_obj = None

    # Try to get token from Authorization header
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        user = get_user_from_token(token)
        if user:
            payload = decode_token(token)
            if payload:
                token_scope = payload.get("scope")

    # Try API Key from X-API-Key header
    if not user:
        api_key_raw = request.headers.get("X-API-Key", "")
        if api_key_raw:
            from apps.tenants.models import APIKey

            key_hash = APIKey.hash_key(api_key_raw)
            try:
                api_key = APIKey.objects.select_related("user", "tenant").get(
                    key_hash=key_hash, is_active=True
                )
                if api_key.is_valid:
                    user = api_key.user
                    token_scope = "api_key"
                    api_key_obj = api_key
                    # Update last_used timestamp
                    APIKey.objects.filter(pk=api_key.pk).update(
                        last_used_at=timezone.now()
                    )
            except APIKey.DoesNotExist:
                pass

    return Context(
        request=request, user=user, token_scope=token_scope, api_key=api_key_obj
    )


class AuthenticatedGraphQLView(AsyncGraphQLView):
    """GraphQL view with authentication context."""

    def get_context(self, request, response):
        return get_context(request)
