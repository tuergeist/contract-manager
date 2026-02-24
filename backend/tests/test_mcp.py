"""Tests for the MCP server, OAuth endpoints, and MCP tools."""

import json

import pytest
from django.test import RequestFactory
from oauth2_provider.models import Application

from apps.mcp.views import DynamicClientRegistrationView, OAuthMetadataView, ProtectedResourceMetadataView


# ── Helpers ───────────────────────────────────────────────────────


def _make_tool(tool_cls, user):
    """Instantiate a tool class and attach a fake request with the user."""
    factory = RequestFactory()
    request = factory.get("/mcp")
    request.user = user
    tool = tool_cls()
    tool.request = request
    return tool


@pytest.fixture
def tenant(db):
    from apps.tenants.models import Tenant
    return Tenant.objects.create(name="MCP Test Tenant", is_active=True)


@pytest.fixture
def admin_user(tenant):
    from apps.tenants.models import Role, User
    user = User.objects.create_user(
        email="mcpadmin@test.local", password="admin123", tenant=tenant, is_admin=True,
    )
    admin_role = Role.objects.get(tenant=tenant, name="Admin")
    user.roles.add(admin_role)
    return user


@pytest.fixture
def viewer_user(tenant):
    from apps.tenants.models import Role, User
    user = User.objects.create_user(
        email="mcpviewer@test.local", password="viewer123", tenant=tenant,
    )
    viewer_role = Role.objects.get(tenant=tenant, name="Viewer")
    user.roles.add(viewer_role)
    return user


# ── OAuth Metadata ───────────────────────────────────────────────


class TestOAuthMetadata:
    def test_metadata_returns_required_fields(self):
        factory = RequestFactory()
        request = factory.get("/.well-known/oauth-authorization-server")
        response = OAuthMetadataView.as_view()(request)
        assert response.status_code == 200
        data = json.loads(response.content)
        assert "authorization_endpoint" in data
        assert "token_endpoint" in data
        assert "registration_endpoint" in data
        assert data["code_challenge_methods_supported"] == ["S256"]
        assert "authorization_code" in data["grant_types_supported"]


# ── Protected Resource Metadata (RFC 9728) ───────────────────────


class TestProtectedResourceMetadata:
    def test_metadata_returns_required_fields(self):
        factory = RequestFactory()
        request = factory.get("/.well-known/oauth-protected-resource")
        response = ProtectedResourceMetadataView.as_view()(request)
        assert response.status_code == 200
        data = json.loads(response.content)
        assert "resource" in data
        assert "authorization_servers" in data
        assert len(data["authorization_servers"]) >= 1
        assert "scopes_supported" in data
        assert "read" in data["scopes_supported"]
        assert "write" in data["scopes_supported"]


# ── Dynamic Client Registration ──────────────────────────────────


@pytest.mark.django_db
class TestDynamicClientRegistration:
    def test_register_creates_application(self):
        factory = RequestFactory()
        request = factory.post(
            "/oauth/register/",
            data=json.dumps({
                "client_name": "Test MCP Client",
                "redirect_uris": ["http://localhost:3000/callback"],
            }),
            content_type="application/json",
        )
        response = DynamicClientRegistrationView.as_view()(request)
        assert response.status_code == 201
        data = json.loads(response.content)
        assert "client_id" in data
        assert data["client_name"] == "Test MCP Client"
        assert Application.objects.filter(client_id=data["client_id"]).exists()

    def test_register_requires_redirect_uris(self):
        factory = RequestFactory()
        request = factory.post(
            "/oauth/register/",
            data=json.dumps({"client_name": "No URIs"}),
            content_type="application/json",
        )
        response = DynamicClientRegistrationView.as_view()(request)
        assert response.status_code == 400

    def test_register_rejects_invalid_json(self):
        factory = RequestFactory()
        request = factory.post(
            "/oauth/register/", data="not json", content_type="application/json",
        )
        response = DynamicClientRegistrationView.as_view()(request)
        assert response.status_code == 400


# ── Permission Checks ─────────────────────────────────────────────


@pytest.mark.django_db
class TestMCPToolPermissions:
    def test_admin_can_list_customers(self, admin_user):
        from apps.mcp.tools import CustomerTools
        result = _make_tool(CustomerTools, admin_user).list_customers()
        assert "Permission denied" not in result

    def test_viewer_cannot_generate_invoices(self, viewer_user):
        from apps.mcp.tools import WriteTools
        result = _make_tool(WriteTools, viewer_user).generate_invoices(
            contract_id=1, billing_date="2025-01-01",
        )
        assert "Permission denied" in result

    def test_unauthenticated_denied(self):
        from django.contrib.auth.models import AnonymousUser
        from apps.mcp.tools import CustomerTools
        result = _make_tool(CustomerTools, AnonymousUser()).list_customers()
        assert "Authentication required" in result

    def test_inactive_tenant_denied(self, admin_user):
        admin_user.tenant.is_active = False
        admin_user.tenant.save()
        from apps.mcp.tools import CustomerTools
        result = _make_tool(CustomerTools, admin_user).list_customers()
        assert "No active tenant" in result


# ── Read Tools ────────────────────────────────────────────────────


@pytest.mark.django_db
class TestReadTools:
    @pytest.fixture(autouse=True)
    def setup(self, tenant, admin_user):
        from apps.customers.models import Customer
        from apps.products.models import Product
        from apps.contracts.models import Contract
        self.user = admin_user
        self.tenant = tenant
        self.customer = Customer.objects.create(
            tenant=tenant, name="Acme Corp", billing_emails=["acme@test.com"],
        )
        self.product = Product.objects.create(
            tenant=tenant, name="Widget", billing_frequency="monthly",
        )
        self.contract = Contract.objects.create(
            tenant=tenant, customer=self.customer, name="Acme Contract",
            billing_interval="monthly", status="active",
            start_date="2025-01-01", billing_start_date="2025-01-01",
        )

    def test_list_customers(self):
        from apps.mcp.tools import CustomerTools
        result = _make_tool(CustomerTools, self.user).list_customers()
        assert "Acme Corp" in result

    def test_list_customers_search_no_match(self):
        from apps.mcp.tools import CustomerTools
        result = _make_tool(CustomerTools, self.user).list_customers(search="zzz")
        assert "No customers found" in result

    def test_get_customer(self):
        from apps.mcp.tools import CustomerTools
        result = _make_tool(CustomerTools, self.user).get_customer(self.customer.id)
        assert "Acme Corp" in result
        assert "acme@test.com" in result  # billing_emails

    def test_get_customer_not_found(self):
        from apps.mcp.tools import CustomerTools
        result = _make_tool(CustomerTools, self.user).get_customer(99999)
        assert "not found" in result

    def test_list_products(self):
        from apps.mcp.tools import ProductTools
        result = _make_tool(ProductTools, self.user).list_products()
        assert "Widget" in result

    def test_get_product(self):
        from apps.mcp.tools import ProductTools
        result = _make_tool(ProductTools, self.user).get_product(self.product.id)
        assert "Widget" in result
        assert "monthly" in result

    def test_list_contracts(self):
        from apps.mcp.tools import ContractTools
        result = _make_tool(ContractTools, self.user).list_contracts()
        assert "Acme Contract" in result

    def test_list_contracts_filter_status(self):
        from apps.mcp.tools import ContractTools
        result = _make_tool(ContractTools, self.user).list_contracts(status="draft")
        assert "No contracts found" in result

    def test_get_contract(self):
        from apps.mcp.tools import ContractTools
        result = _make_tool(ContractTools, self.user).get_contract(self.contract.id)
        assert "Acme Contract" in result
        assert "active" in result

    def test_list_invoices_empty(self):
        from apps.mcp.tools import InvoiceTools
        result = _make_tool(InvoiceTools, self.user).list_invoices()
        assert "No invoices found" in result


# ── Write Tools ───────────────────────────────────────────────────


@pytest.mark.django_db
class TestWriteTools:
    @pytest.fixture(autouse=True)
    def setup(self, tenant, admin_user):
        from apps.customers.models import Customer
        from apps.contracts.models import Contract
        self.user = admin_user
        self.tenant = tenant
        self.customer = Customer.objects.create(tenant=tenant, name="Write Corp")
        self.contract = Contract.objects.create(
            tenant=tenant, customer=self.customer, name="Write Contract",
            billing_interval="monthly", status="draft",
            start_date="2025-01-01", billing_start_date="2025-01-01",
        )

    def test_create_contract(self):
        from apps.mcp.tools import WriteTools
        result = _make_tool(WriteTools, self.user).create_contract(
            customer_id=self.customer.id, name="New Contract", billing_cycle="quarterly",
        )
        assert "New Contract" in result
        assert "draft" in result

    def test_create_contract_invalid_customer(self):
        from apps.mcp.tools import WriteTools
        result = _make_tool(WriteTools, self.user).create_contract(
            customer_id=99999, name="Bad",
        )
        assert "not found" in result

    def test_update_contract_status(self):
        from apps.mcp.tools import WriteTools
        result = _make_tool(WriteTools, self.user).update_contract(
            contract_id=self.contract.id, status="active",
        )
        assert "active" in result

    def test_update_contract_invalid_transition(self):
        from apps.mcp.tools import WriteTools
        result = _make_tool(WriteTools, self.user).update_contract(
            contract_id=self.contract.id, status="cancelled",
        )
        assert "Invalid status transition" in result

    def test_void_invoice_not_found(self):
        from apps.mcp.tools import WriteTools
        result = _make_tool(WriteTools, self.user).void_invoice(invoice_id=99999)
        assert "not found" in result

    def test_send_invoice_email_not_found(self):
        from apps.mcp.tools import WriteTools
        result = _make_tool(WriteTools, self.user).send_invoice_email(invoice_id=99999)
        assert "not found" in result
