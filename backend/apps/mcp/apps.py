from django.apps import AppConfig


class McpConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.mcp"
    verbose_name = "MCP Server"

    def ready(self):
        from mcp_server.djangomcp import global_mcp_server, ToolsetMeta

        import apps.mcp.tools  # noqa: F401 — populates ToolsetMeta registry

        for name, cls in ToolsetMeta.iter_all():
            if name.startswith("_"):
                continue
            global_mcp_server.register_mcptoolset(cls())
