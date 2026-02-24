"""Middleware to add RFC 9728 resource_metadata to MCP 401 responses."""


class McpResourceMetadataMiddleware:
    """Add resource_metadata to WWW-Authenticate header on 401 from /mcp.

    Per the MCP spec, servers SHOULD include resource_metadata in the
    WWW-Authenticate header so clients can discover the authorization server.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if (
            request.path == "/mcp"
            and response.status_code == 401
            and "WWW-Authenticate" in response
        ):
            base_url = request.build_absolute_uri("/").rstrip("/")
            resource_metadata_url = f"{base_url}/.well-known/oauth-protected-resource"
            response["WWW-Authenticate"] = (
                f'Bearer resource_metadata="{resource_metadata_url}", scope="read write"'
            )
        return response
