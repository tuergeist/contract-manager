"""Permission utilities for GraphQL."""
from functools import wraps
from typing import Any, Callable

from strawberry.types import Info

from apps.core.context import Context


# --- Permission Registry ---
# Single source of truth for all grantable permissions.
# Each key is a resource, value is a list of valid actions.
PERMISSION_REGISTRY = {
    "contracts": ["read", "write", "delete"],
    "customers": ["read", "write", "delete"],
    "products": ["read", "write", "delete"],
    "users": ["read", "write", "delete"],
    "settings": ["read", "write"],
    "todos": ["read", "write"],
    "notes": ["read", "write"],
    "invoices": ["read", "export", "generate", "settings"],
}

# All permissions as flat "resource.action" strings
ALL_PERMISSIONS = {
    f"{resource}.{action}"
    for resource, actions in PERMISSION_REGISTRY.items()
    for action in actions
}

# Default role definitions: role name -> set of granted permissions
DEFAULT_ROLES = {
    "Admin": {perm: True for perm in ALL_PERMISSIONS},
    "Manager": {
        perm: True
        for perm in ALL_PERMISSIONS
        if not perm.startswith("users.")
        and not perm.startswith("settings.")
        and perm != "invoices.settings"
    },
    "Viewer": {
        "contracts.read": True,
        "customers.read": True,
        "products.read": True,
        "todos.read": True,
        "todos.write": True,
        "notes.read": True,
        "notes.write": True,
        "invoices.read": True,
    },
}

# Permissions that cannot be removed from the Admin role
ADMIN_PROTECTED_PERMISSIONS = {
    "users.read", "users.write", "users.delete",
    "settings.read", "settings.write",
}


def normalize_permissions(raw: dict) -> dict:
    """Normalize a permissions dict to flat {resource.action: True} format.

    Handles old-format entries like {"products": ["read"]} by converting them
    to {"products.read": True}. Strips any keys not in ALL_PERMISSIONS.
    """
    result = {}
    for key, value in raw.items():
        if key in ALL_PERMISSIONS:
            if value:
                result[key] = True
        elif key in PERMISSION_REGISTRY and isinstance(value, list):
            for action in value:
                flat_key = f"{key}.{action}"
                if flat_key in ALL_PERMISSIONS:
                    result[flat_key] = True
    return result


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


def require_perm(info: Info[Context, None], resource: str, action: str):
    """Get the current user and verify they have the required permission.

    Raises PermissionError if not authenticated or permission denied.
    Returns the user on success. Use in queries.
    """
    user = get_current_user(info)
    if not user.has_perm_check(resource, action):
        raise PermissionError(f"Permission denied: {resource}.{action}")
    return user


def check_perm(info: Info[Context, None], resource: str, action: str):
    """Get the current user and check permission without raising.

    Returns (user, None) on success or (None, error_string) on failure.
    Use in mutations that return result types.
    """
    user = get_current_user(info)
    if not user.has_perm_check(resource, action):
        return None, "Permission denied"
    return user, None


def get_current_user_from_request(request):
    """Get the current authenticated user from a Django request.

    Uses the same authentication logic as the GraphQL context.
    Returns None if not authenticated.
    """
    from apps.core.context import get_context

    context = get_context(request)
    if context.is_authenticated:
        return context.user
    return None
