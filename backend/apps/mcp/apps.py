from django.apps import AppConfig


class McpConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.mcp"
    verbose_name = "MCP Server"

    def ready(self):
        import apps.mcp.tools  # noqa: F401 — registers MCP toolsets via metaclass
