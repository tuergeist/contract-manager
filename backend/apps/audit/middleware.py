"""Middleware for audit logging."""

from apps.audit.services import clear_current_user, set_current_user
from apps.core.auth import get_user_from_token


class AuditUserMiddleware:
    """Middleware to set the current user for audit logging from request context."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Try to get user from Authorization header (JWT)
        user = None
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            user = get_user_from_token(token)

        # Set the user in thread-local storage
        if user:
            set_current_user(user)

        try:
            response = self.get_response(request)
            return response
        finally:
            # Always clear the user after the request
            clear_current_user()
