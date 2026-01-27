"""GraphQL context for request handling."""
from dataclasses import dataclass

from django.http import HttpRequest
from strawberry.django.views import AsyncGraphQLView

from apps.core.auth import get_user_from_token
from apps.tenants.models import User


@dataclass
class Context:
    """GraphQL request context."""

    request: HttpRequest
    user: User | None = None

    @property
    def is_authenticated(self) -> bool:
        return self.user is not None


def get_context(request: HttpRequest) -> Context:
    """Extract context from request, including authenticated user."""
    user = None

    # Try to get token from Authorization header
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        user = get_user_from_token(token)

    return Context(request=request, user=user)


class AuthenticatedGraphQLView(AsyncGraphQLView):
    """GraphQL view with authentication context."""

    def get_context(self, request, response):
        return get_context(request)
