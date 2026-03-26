"""Tests for the AI assistant chat endpoint and tools."""

import json
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from django.test import RequestFactory

from apps.assistant.tools import (
    execute_tool,
    get_customer_details,
    get_revenue_summary,
    search_contracts,
    search_customers,
    search_invoices,
    search_products,
)
from apps.contracts.models import Contract, ContractItem
from apps.customers.models import Customer
from apps.products.models import Product


@pytest.fixture
def tenant(db):
    from apps.tenants.models import Tenant

    return Tenant.objects.create(name="Test Tenant", is_active=True)


@pytest.fixture
def user(db, tenant):
    from apps.tenants.models import User

    from apps.tenants.models import Role

    role = Role.objects.create(
        tenant=tenant,
        name="TestAdmin",
        permissions={"assistant.use": True, "contracts.read": True, "customers.read": True},
    )
    u = User.objects.create_user(
        email="test@test.local",
        password="test123",
        first_name="Test",
        last_name="User",
        tenant=tenant,
    )
    u.roles.add(role)
    return u


@pytest.fixture
def customer(db, tenant):
    return Customer.objects.create(
        tenant=tenant,
        name="Acme Corp",
        billing_emails=["billing@acme.com"],
    )


@pytest.fixture
def product(db, tenant):
    return Product.objects.create(
        tenant=tenant,
        name="Support Plan",
        sku="SP-001",
        billing_frequency="monthly",
    )


@pytest.fixture
def contract(db, tenant, customer):
    return Contract.objects.create(
        tenant=tenant,
        customer=customer,
        name="Acme Support",
        status="active",
        billing_interval="monthly",
        start_date="2025-01-01",
        billing_start_date="2025-01-01",
    )


class TestTools:
    def test_search_customers(self, tenant, customer):
        result = search_customers(tenant, search="Acme")
        assert "Acme Corp" in result
        assert "ID:" in result

    def test_search_customers_no_results(self, tenant):
        result = search_customers(tenant, search="NonExistent")
        assert "No customers found" in result

    def test_get_customer_details(self, tenant, customer):
        result = get_customer_details(tenant, customer_id=customer.id)
        assert "Acme Corp" in result
        assert "billing@acme.com" in result

    def test_get_customer_not_found(self, tenant):
        result = get_customer_details(tenant, customer_id=99999)
        assert "not found" in result

    def test_search_contracts(self, tenant, contract):
        result = search_contracts(tenant, status="active")
        assert "Acme Support" in result

    def test_search_contracts_by_customer(self, tenant, contract, customer):
        result = search_contracts(tenant, customer_id=customer.id)
        assert "Acme Support" in result

    def test_search_products(self, tenant, product):
        result = search_products(tenant, search="Support")
        assert "Support Plan" in result
        assert "SP-001" in result

    def test_search_invoices_empty(self, tenant):
        result = search_invoices(tenant)
        assert "No invoices found" in result

    def test_get_revenue_summary(self, tenant, contract, product):
        ContractItem.objects.create(
            tenant=tenant,
            contract=contract,
            product=product,
            quantity=1,
            unit_price=Decimal("1000.00"),
            is_one_off=False,
            sort_order=1,
        )
        result = get_revenue_summary(tenant)
        assert "MRR" in result
        assert "Active Contracts: 1" in result
        assert "Acme Corp" in result

    def test_execute_tool_unknown(self, tenant):
        result = execute_tool(tenant, "nonexistent_tool", {})
        assert "Unknown tool" in result

    def test_execute_tool_search_customers(self, tenant, customer):
        result = execute_tool(tenant, "search_customers", {"search": "Acme"})
        assert "Acme Corp" in result

    def test_tenant_isolation(self, db, tenant, customer):
        """Tools from one tenant should not see another tenant's data."""
        from apps.tenants.models import Tenant

        other_tenant = Tenant.objects.create(name="Other Tenant", is_active=True)
        Customer.objects.create(tenant=other_tenant, name="Other Corp")

        result = search_customers(tenant, search="Other")
        assert "No customers found" in result

        result_other = search_customers(other_tenant, search="Other")
        assert "Other Corp" in result_other


class TestChatEndpoint:
    @pytest.fixture
    def auth_header(self, user):
        from apps.core.auth import create_access_token
        token = create_access_token(user)
        return {"HTTP_AUTHORIZATION": f"Bearer {token}"}

    def test_unauthenticated_returns_403(self, client):
        response = client.post(
            "/api/assistant/chat/",
            data=json.dumps({"message": "hello"}),
            content_type="application/json",
        )
        assert response.status_code == 403

    def test_authenticated_no_message(self, client, user, auth_header):
        response = client.post(
            "/api/assistant/chat/",
            data=json.dumps({"message": ""}),
            content_type="application/json",
            **auth_header,
        )
        assert response.status_code == 400

    def test_invalid_json(self, client, user, auth_header):
        response = client.post(
            "/api/assistant/chat/",
            data="not json",
            content_type="application/json",
            **auth_header,
        )
        assert response.status_code == 400

    @patch("apps.assistant.views._check_rate_limit", return_value=True)
    def test_rate_limit(self, mock_rl, client, user, auth_header):
        response = client.post(
            "/api/assistant/chat/",
            data=json.dumps({"message": "hello"}),
            content_type="application/json",
            **auth_header,
        )
        assert response.status_code == 429

    @patch("apps.assistant.views.settings")
    def test_no_api_key_returns_503(self, mock_settings, client, user, auth_header):
        mock_settings.ANTHROPIC_API_KEY = ""
        response = client.post(
            "/api/assistant/chat/",
            data=json.dumps({"message": "hello"}),
            content_type="application/json",
            **auth_header,
        )
        assert response.status_code == 503
