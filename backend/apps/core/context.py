"""GraphQL context for request handling."""
from dataclasses import dataclass, field

from django.http import HttpRequest
from strawberry.django.views import AsyncGraphQLView

from apps.core.auth import decode_token, get_user_from_token
from apps.tenants.models import User


@dataclass
class Context:
    """GraphQL request context."""

    request: HttpRequest
    user: User | None = None
    token_scope: str | None = None

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

    # Try to get token from Authorization header
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        user = get_user_from_token(token)
        if user:
            payload = decode_token(token)
            if payload:
                token_scope = payload.get("scope")

    return Context(request=request, user=user, token_scope=token_scope)


class AuthenticatedGraphQLView(AsyncGraphQLView):
    """GraphQL view with authentication context."""

    def get_context(self, request, response):
        return get_context(request)
