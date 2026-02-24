"""OAuth 2.1 metadata and dynamic registration views for MCP."""

import json
import logging
from urllib.parse import urlparse

import requests
from django.http import JsonResponse
from django.views import View
from oauth2_provider.models import Application
from oauth2_provider.views import AuthorizationView

logger = logging.getLogger(__name__)


class ProtectedResourceMetadataView(View):
    """RFC 9728 - OAuth 2.0 Protected Resource Metadata.

    MCP clients use this to discover which authorization server to use.
    """

    def get(self, request):
        base_url = request.build_absolute_uri("/").rstrip("/")
        return JsonResponse({
            "resource": f"{base_url}/mcp",
            "authorization_servers": [base_url],
            "scopes_supported": ["read", "write"],
            "bearer_methods_supported": ["header"],
        })


class OAuthMetadataView(View):
    """RFC 8414 - OAuth 2.0 Authorization Server Metadata."""

    def get(self, request):
        base_url = request.build_absolute_uri("/").rstrip("/")
        return JsonResponse({
            "issuer": base_url,
            "authorization_endpoint": f"{base_url}/oauth/authorize/",
            "token_endpoint": f"{base_url}/oauth/token/",
            "registration_endpoint": f"{base_url}/oauth/register/",
            "revocation_endpoint": f"{base_url}/oauth/revoke_token/",
            "response_types_supported": ["code"],
            "grant_types_supported": ["authorization_code", "refresh_token"],
            "code_challenge_methods_supported": ["S256"],
            "token_endpoint_auth_methods_supported": ["none", "client_secret_post"],
            "scopes_supported": ["read", "write"],
            "client_id_metadata_document_supported": True,
        })


class DynamicClientRegistrationView(View):
    """RFC 7591 - OAuth 2.0 Dynamic Client Registration."""

    def post(self, request):
        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return JsonResponse({"error": "invalid_client_metadata"}, status=400)

        redirect_uris = data.get("redirect_uris", [])
        client_name = data.get("client_name", "MCP Client")

        if not redirect_uris:
            return JsonResponse(
                {"error": "invalid_redirect_uri", "error_description": "redirect_uris required"},
                status=400,
            )

        app = Application.objects.create(
            name=client_name,
            client_type=Application.CLIENT_PUBLIC,
            authorization_grant_type=Application.GRANT_AUTHORIZATION_CODE,
            redirect_uris=" ".join(redirect_uris),
            skip_authorization=False,
        )

        return JsonResponse({
            "client_id": app.client_id,
            "client_name": app.name,
            "redirect_uris": redirect_uris,
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
            "token_endpoint_auth_method": "none",
        }, status=201)


def _is_url(value: str) -> bool:
    """Check if a string looks like an HTTP(S) URL."""
    try:
        parsed = urlparse(value)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except Exception:
        return False


def _resolve_metadata_client(client_id_url: str) -> Application | None:
    """Resolve a client_id metadata document URL to an Application.

    MCP OAuth spec: when client_id is a URL, the server fetches the
    client metadata from that URL, registers the client, and uses
    the URL as the stored client_id for future lookups.
    """
    # Look up existing application by metadata URL
    try:
        return Application.objects.get(client_id=client_id_url)
    except Application.DoesNotExist:
        pass

    # Fetch metadata from the URL
    try:
        resp = requests.get(client_id_url, timeout=10)
        resp.raise_for_status()
        metadata = resp.json()
    except Exception:
        logger.warning("Failed to fetch client metadata from %s", client_id_url)
        return None

    redirect_uris = metadata.get("redirect_uris", [])
    client_name = metadata.get("client_name", "MCP Client")

    if not redirect_uris:
        logger.warning("Client metadata at %s has no redirect_uris", client_id_url)
        return None

    # Create application with the metadata URL as client_id
    app = Application(
        name=client_name,
        client_id=client_id_url,
        client_type=Application.CLIENT_PUBLIC,
        authorization_grant_type=Application.GRANT_AUTHORIZATION_CODE,
        redirect_uris=" ".join(redirect_uris),
        skip_authorization=False,
    )
    app.save()
    logger.info("Auto-registered MCP client '%s' from %s", client_name, client_id_url)
    return app


class McpAuthorizationView(AuthorizationView):
    """Custom authorize view that supports URL-based client_id.

    MCP clients (e.g. Claude) send their metadata document URL as client_id.
    This view resolves it to a registered Application before passing to
    django-oauth-toolkit's standard authorization flow.
    """

    def dispatch(self, request, *args, **kwargs):
        client_id = request.GET.get("client_id", "")
        if client_id and _is_url(client_id):
            app = _resolve_metadata_client(client_id)
            if app is None:
                return JsonResponse(
                    {"error": "invalid_request", "error_description": "Could not resolve client metadata"},
                    status=400,
                )
        return super().dispatch(request, *args, **kwargs)
