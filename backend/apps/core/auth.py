"""JWT Authentication utilities."""
from datetime import datetime, timedelta, timezone

import jwt
from django.conf import settings

from apps.tenants.models import User


def create_access_token(user: User, expires_delta: timedelta | None = None) -> str:
    """Create a JWT access token for a user."""
    if expires_delta is None:
        expires_delta = timedelta(hours=24)

    expire = datetime.now(timezone.utc) + expires_delta
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "tenant_id": user.tenant_id,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access",
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


def create_refresh_token(user: User, expires_delta: timedelta | None = None) -> str:
    """Create a JWT refresh token for a user."""
    if expires_delta is None:
        expires_delta = timedelta(days=7)

    expire = datetime.now(timezone.utc) + expires_delta
    payload = {
        "sub": str(user.id),
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "refresh",
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


def decode_token(token: str) -> dict | None:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def get_user_from_token(token: str) -> User | None:
    """Get user from a valid JWT token."""
    payload = decode_token(token)
    if payload is None:
        return None

    try:
        user_id = payload.get("sub")
        if user_id is None:
            return None
        return User.objects.select_related("tenant", "role").get(id=int(user_id), is_active=True)
    except (User.DoesNotExist, ValueError):
        return None
