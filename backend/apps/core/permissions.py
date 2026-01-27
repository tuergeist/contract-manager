"""Permission utilities for GraphQL."""
from functools import wraps
from typing import Any, Callable

from strawberry.types import Info

from apps.core.context import Context


class PermissionError(Exception):
    """Raised when user lacks required permissions."""

    pass


def login_required(func: Callable) -> Callable:
    """Decorator to require authentication for a resolver."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        # Find the Info object in args
        info = None
        for arg in args:
            if isinstance(arg, Info):
                info = arg
                break

        if info is None:
            # Check kwargs
            info = kwargs.get("info")

        if info is None or not hasattr(info, "context"):
            raise PermissionError("Authentication required")

        context: Context = info.context
        if not context.is_authenticated:
            raise PermissionError("Authentication required")

        return func(*args, **kwargs)

    return wrapper


def is_authenticated(info: Info[Context, None]) -> bool:
    """Check if the current request is authenticated."""
    return info.context.is_authenticated


def get_current_user(info: Info[Context, None]):
    """Get the current authenticated user or raise error."""
    if not info.context.is_authenticated:
        raise PermissionError("Authentication required")
    return info.context.user


def get_current_tenant_id(info: Info[Context, None]) -> int:
    """Get the current user's tenant ID or raise error."""
    user = get_current_user(info)
    if user.tenant_id is None:
        raise PermissionError("User has no tenant assigned")
    return user.tenant_id
