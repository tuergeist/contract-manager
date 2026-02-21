"""OAuth 2.1 metadata and dynamic registration views for MCP."""

import json

from django.http import JsonResponse
from django.views import View
from oauth2_provider.models import Application


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
