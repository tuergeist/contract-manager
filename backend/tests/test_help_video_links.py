"""Tests for help video links query and mutation."""
import pytest
from unittest.mock import Mock

from config.schema import schema
from apps.tenants.models import Role, Tenant, User
from apps.core.context import Context


def run_graphql(query, variables, context):
    return schema.execute_sync(query, variable_values=variables, context_value=context)


def make_context(user=None):
    request = Mock()
    return Context(request=request, user=user)


@pytest.fixture
def tenant(db):
    return Tenant.objects.create(name="Test Company", currency="EUR")


@pytest.fixture
def admin_user(db, tenant):
    u = User.objects.create_user(
        email="admin@example.com", password="admin123", tenant=tenant, is_admin=True
    )
    admin_role = Role.objects.get(tenant=tenant, name="Admin")
    u.roles.add(admin_role)
    return u


@pytest.fixture
def viewer_user(db, tenant):
    u = User.objects.create_user(
        email="viewer@example.com", password="view123", tenant=tenant
    )
    viewer_role = Role.objects.get(tenant=tenant, name="Viewer")
    u.roles.add(viewer_role)
    return u


QUERY = """
    query {
        helpVideoLinks {
            routeKey
            links {
                url
                label
            }
        }
    }
"""

MUTATION = """
    mutation UpdateHelpVideoLinks($entries: [HelpVideoLinksEntryInput!]!) {
        updateHelpVideoLinks(entries: $entries) {
            routeKey
            links {
                url
                label
            }
        }
    }
"""


class TestHelpVideoLinksQuery:
    def test_empty_config(self, admin_user):
        ctx = make_context(admin_user)
        result = run_graphql(QUERY, {}, ctx)
        assert result.errors is None
        assert result.data["helpVideoLinks"] == []

    def test_populated_config(self, admin_user, tenant):
        tenant.settings = {
            "help_video_links": {
                "/customers": [
                    {"url": "https://example.com/vid1", "label": "Customer Help"}
                ],
                "/contracts/:id": [
                    {"url": "https://example.com/vid2", "label": "Contract Help"},
                    {"url": "https://example.com/vid3"},
                ],
            }
        }
        tenant.save(update_fields=["settings"])

        ctx = make_context(admin_user)
        result = run_graphql(QUERY, {}, ctx)
        assert result.errors is None
        entries = result.data["helpVideoLinks"]
        assert len(entries) == 2

        by_key = {e["routeKey"]: e["links"] for e in entries}
        assert len(by_key["/customers"]) == 1
        assert by_key["/customers"][0]["url"] == "https://example.com/vid1"
        assert by_key["/customers"][0]["label"] == "Customer Help"
        assert len(by_key["/contracts/:id"]) == 2
        assert by_key["/contracts/:id"][1]["label"] is None


class TestUpdateHelpVideoLinksMutation:
    def test_add_links(self, admin_user, tenant):
        ctx = make_context(admin_user)
        variables = {
            "entries": [
                {
                    "routeKey": "/customers",
                    "links": [
                        {"url": "https://example.com/vid1", "label": "Help Video"}
                    ],
                }
            ]
        }
        result = run_graphql(MUTATION, variables, ctx)
        assert result.errors is None
        entries = result.data["updateHelpVideoLinks"]
        assert len(entries) == 1
        assert entries[0]["routeKey"] == "/customers"
        assert entries[0]["links"][0]["url"] == "https://example.com/vid1"

        tenant.refresh_from_db()
        assert "/customers" in tenant.settings["help_video_links"]

    def test_clear_links(self, admin_user, tenant):
        tenant.settings = {
            "help_video_links": {
                "/customers": [{"url": "https://example.com/vid1"}]
            }
        }
        tenant.save(update_fields=["settings"])

        ctx = make_context(admin_user)
        result = run_graphql(MUTATION, {"entries": []}, ctx)
        assert result.errors is None
        assert result.data["updateHelpVideoLinks"] == []

        tenant.refresh_from_db()
        assert "help_video_links" not in tenant.settings

    def test_permission_required(self, viewer_user):
        ctx = make_context(viewer_user)
        variables = {
            "entries": [
                {
                    "routeKey": "/customers",
                    "links": [{"url": "https://example.com/vid1"}],
                }
            ]
        }
        result = run_graphql(MUTATION, variables, ctx)
        assert result.errors is not None
