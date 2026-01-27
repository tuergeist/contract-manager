"""Core GraphQL schema for authentication."""
import strawberry
from django.contrib.auth import authenticate
from strawberry.types import Info

from apps.core.auth import create_access_token, create_refresh_token, get_user_from_token
from apps.core.context import Context


@strawberry.type
class AuthPayload:
    """Authentication response with tokens."""

    access_token: str
    refresh_token: str
    user_id: int
    email: str
    tenant_id: int | None


@strawberry.type
class AuthError:
    """Authentication error."""

    message: str


AuthResult = strawberry.union("AuthResult", [AuthPayload, AuthError])


@strawberry.type
class CurrentUser:
    """Current authenticated user info."""

    id: int
    email: str
    first_name: str
    last_name: str
    tenant_id: int | None
    tenant_name: str | None
    role_name: str | None


@strawberry.type
class CoreQuery:
    """Core queries including auth status."""

    @strawberry.field
    def me(self, info: Info[Context, None]) -> CurrentUser | None:
        """Get current authenticated user."""
        user = info.context.user
        if user is None:
            return None

        return CurrentUser(
            id=user.id,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            tenant_id=user.tenant_id,
            tenant_name=user.tenant.name if user.tenant else None,
            role_name=user.role.name if user.role else None,
        )


@strawberry.type
class AuthMutation:
    """Authentication mutations."""

    @strawberry.mutation
    def login(self, email: str, password: str) -> AuthResult:
        """Authenticate user and return tokens."""
        user = authenticate(username=email, password=password)

        if user is None or not user.is_active:
            return AuthError(message="Invalid email or password")

        if user.tenant and not user.tenant.is_active:
            return AuthError(message="Tenant is inactive")

        access_token = create_access_token(user)
        refresh_token = create_refresh_token(user)

        return AuthPayload(
            access_token=access_token,
            refresh_token=refresh_token,
            user_id=user.id,
            email=user.email,
            tenant_id=user.tenant_id,
        )

    @strawberry.mutation
    def refresh_token(self, refresh_token: str) -> AuthResult:
        """Get new access token using refresh token."""
        user = get_user_from_token(refresh_token)

        if user is None:
            return AuthError(message="Invalid or expired refresh token")

        if user.tenant and not user.tenant.is_active:
            return AuthError(message="Tenant is inactive")

        access_token = create_access_token(user)
        new_refresh_token = create_refresh_token(user)

        return AuthPayload(
            access_token=access_token,
            refresh_token=new_refresh_token,
            user_id=user.id,
            email=user.email,
            tenant_id=user.tenant_id,
        )
