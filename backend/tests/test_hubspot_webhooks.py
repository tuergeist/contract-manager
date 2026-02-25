"""Tests for HubSpot webhook receiver and event processing."""

import hashlib
import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, Mock, patch

import pytest
from django.test import Client as HttpClient

from apps.core.context import Context
from apps.customers.models import Customer
from apps.customers.tasks import process_hubspot_webhook_event, sync_all_hubspot_tenants
from apps.products.models import Product
from apps.tenants.models import Tenant, User
from config.schema import schema


@pytest.fixture
def tenant_with_webhooks(db):
    """Tenant configured for webhook sync."""
    tenant = Tenant.objects.create(
        name="Webhook Tenant",
        is_active=True,
        hubspot_config={
            "api_key": "test-key",
            "portal_id": "12345678",
            "client_secret": "test-secret-key",
            "sync_mode": "webhooks",
            "auto_sync_enabled": True,
        },
    )
    return tenant


@pytest.fixture
def tenant_polling(db):
    """Tenant configured for polling sync."""
    tenant = Tenant.objects.create(
        name="Polling Tenant",
        is_active=True,
        hubspot_config={
            "api_key": "test-key",
            "auto_sync_enabled": True,
            "sync_mode": "polling",
        },
    )
    return tenant


def _sign_payload(secret: str, body: bytes) -> str:
    """Compute HubSpot v1 signature."""
    return hashlib.sha256(secret.encode("utf-8") + body).hexdigest()


class TestWebhookEndpoint:
    """Tests for the /api/hubspot/webhook/ endpoint."""

    def test_valid_signature_returns_200(self, tenant_with_webhooks):
        client = HttpClient()
        events = [
            {
                "subscriptionType": "company.creation",
                "portalId": 12345678,
                "objectId": 999,
                "occurredAt": 1700000000000,
            }
        ]
        body = json.dumps(events).encode("utf-8")
        signature = _sign_payload("test-secret-key", body)

        with patch("apps.customers.tasks.process_hubspot_webhook_event") as mock_task:
            mock_task.delay = MagicMock()
            response = client.post(
                "/api/hubspot/webhook/",
                data=body,
                content_type="application/json",
                HTTP_X_HUBSPOT_SIGNATURE=signature,
            )

        assert response.status_code == 200
        mock_task.delay.assert_called_once()

    def test_missing_signature_returns_401(self, tenant_with_webhooks):
        client = HttpClient()
        body = json.dumps([{"portalId": 12345678, "objectId": 1}]).encode("utf-8")

        response = client.post(
            "/api/hubspot/webhook/",
            data=body,
            content_type="application/json",
        )
        assert response.status_code == 401

    def test_invalid_signature_returns_401(self, tenant_with_webhooks):
        client = HttpClient()
        body = json.dumps(
            [{"subscriptionType": "company.creation", "portalId": 12345678, "objectId": 1}]
        ).encode("utf-8")

        response = client.post(
            "/api/hubspot/webhook/",
            data=body,
            content_type="application/json",
            HTTP_X_HUBSPOT_SIGNATURE="invalid-signature",
        )
        assert response.status_code == 401

    def test_unknown_portal_returns_200(self, tenant_with_webhooks):
        client = HttpClient()
        events = [{"subscriptionType": "company.creation", "portalId": 99999999, "objectId": 1}]
        body = json.dumps(events).encode("utf-8")

        response = client.post(
            "/api/hubspot/webhook/",
            data=body,
            content_type="application/json",
            HTTP_X_HUBSPOT_SIGNATURE="anything",
        )
        # Returns 200 to prevent HubSpot retries
        assert response.status_code == 200

    def test_empty_payload_returns_200(self, tenant_with_webhooks):
        client = HttpClient()
        body = json.dumps([]).encode("utf-8")
        signature = _sign_payload("test-secret-key", body)

        response = client.post(
            "/api/hubspot/webhook/",
            data=body,
            content_type="application/json",
            HTTP_X_HUBSPOT_SIGNATURE=signature,
        )
        assert response.status_code == 200

    def test_get_method_returns_405(self, tenant_with_webhooks):
        client = HttpClient()
        response = client.get("/api/hubspot/webhook/")
        assert response.status_code == 405

    def test_batch_events_dispatch_individually(self, tenant_with_webhooks):
        client = HttpClient()
        events = [
            {"subscriptionType": "company.creation", "portalId": 12345678, "objectId": i}
            for i in range(5)
        ]
        body = json.dumps(events).encode("utf-8")
        signature = _sign_payload("test-secret-key", body)

        with patch("apps.customers.tasks.process_hubspot_webhook_event") as mock_task:
            mock_task.delay = MagicMock()
            response = client.post(
                "/api/hubspot/webhook/",
                data=body,
                content_type="application/json",
                HTTP_X_HUBSPOT_SIGNATURE=signature,
            )

        assert response.status_code == 200
        assert mock_task.delay.call_count == 5


class TestWebhookEventProcessing:
    """Tests for the process_hubspot_webhook_event Celery task."""

    def test_company_creation_syncs_customer(self, tenant_with_webhooks):
        company_data = {
            "id": "100",
            "properties": {
                "name": "Webhook Corp",
                "address": "123 Main St",
                "city": "Berlin",
                "zip": "10115",
                "country_list": "Germany",
            },
        }

        event = {
            "subscriptionType": "company.creation",
            "objectId": 100,
            "portalId": 12345678,
        }

        with patch.object(
            __import__("apps.customers.hubspot", fromlist=["HubSpotService"]).HubSpotService,
            "fetch_company",
            return_value=company_data,
        ):
            result = process_hubspot_webhook_event(event, tenant_with_webhooks.id)

        assert result == "company_synced"
        customer = Customer.objects.get(tenant=tenant_with_webhooks, hubspot_id="100")
        assert customer.name == "Webhook Corp"

    def test_company_deletion_marks_inactive(self, tenant_with_webhooks):
        customer = Customer.objects.create(
            tenant=tenant_with_webhooks,
            hubspot_id="200",
            name="To Delete",
            is_active=True,
        )

        event = {
            "subscriptionType": "company.deletion",
            "objectId": 200,
            "portalId": 12345678,
        }

        result = process_hubspot_webhook_event(event, tenant_with_webhooks.id)

        assert result == "company_deleted"
        customer.refresh_from_db()
        assert customer.is_active is False
        assert customer.hubspot_deleted_at is not None

    def test_company_not_found_marks_inactive(self, tenant_with_webhooks):
        customer = Customer.objects.create(
            tenant=tenant_with_webhooks,
            hubspot_id="300",
            name="Gone Corp",
            is_active=True,
        )

        event = {
            "subscriptionType": "company.propertyChange",
            "objectId": 300,
            "portalId": 12345678,
        }

        with patch.object(
            __import__("apps.customers.hubspot", fromlist=["HubSpotService"]).HubSpotService,
            "fetch_company",
            return_value=None,
        ):
            result = process_hubspot_webhook_event(event, tenant_with_webhooks.id)

        assert result == "company_not_found"
        customer.refresh_from_db()
        assert customer.is_active is False

    def test_product_creation_syncs_product(self, tenant_with_webhooks):
        product_data = {
            "id": "500",
            "properties": {
                "name": "Webhook Product",
                "description": "Test product",
                "price": "99.99",
                "hs_sku": "WH-001",
                "hs_recurring_billing_period": None,
            },
        }

        event = {
            "subscriptionType": "product.creation",
            "objectId": 500,
            "portalId": 12345678,
        }

        with patch.object(
            __import__("apps.customers.hubspot", fromlist=["HubSpotService"]).HubSpotService,
            "fetch_product",
            return_value=product_data,
        ):
            result = process_hubspot_webhook_event(event, tenant_with_webhooks.id)

        assert result == "product_synced"
        product = Product.objects.get(tenant=tenant_with_webhooks, hubspot_id="500")
        assert product.name == "Webhook Product"

    def test_product_deletion_marks_inactive(self, tenant_with_webhooks):
        product = Product.objects.create(
            tenant=tenant_with_webhooks,
            hubspot_id="600",
            name="To Delete Product",
            is_active=True,
        )

        event = {
            "subscriptionType": "product.deletion",
            "objectId": 600,
            "portalId": 12345678,
        }

        result = process_hubspot_webhook_event(event, tenant_with_webhooks.id)

        assert result == "product_deleted"
        product.refresh_from_db()
        assert product.is_active is False

    def test_unknown_event_type_ignored(self, tenant_with_webhooks):
        event = {
            "subscriptionType": "contact.creation",
            "objectId": 999,
            "portalId": 12345678,
        }

        result = process_hubspot_webhook_event(event, tenant_with_webhooks.id)
        assert result == "ignored"

    def test_duplicate_event_is_idempotent(self, tenant_with_webhooks):
        """Processing the same event twice produces the same result."""
        company_data = {
            "id": "700",
            "properties": {
                "name": "Idempotent Corp",
                "address": "",
                "city": "",
                "zip": "",
                "country_list": "",
            },
        }

        event = {
            "subscriptionType": "company.creation",
            "objectId": 700,
            "portalId": 12345678,
        }

        with patch.object(
            __import__("apps.customers.hubspot", fromlist=["HubSpotService"]).HubSpotService,
            "fetch_company",
            return_value=company_data,
        ):
            result1 = process_hubspot_webhook_event(event, tenant_with_webhooks.id)
            result2 = process_hubspot_webhook_event(event, tenant_with_webhooks.id)

        assert result1 == "company_synced"
        assert result2 == "company_synced"
        assert Customer.objects.filter(tenant=tenant_with_webhooks, hubspot_id="700").count() == 1


class TestPollingSkipsWebhookTenants:
    """Test that the periodic sync task skips tenants in webhook mode."""

    def test_webhook_tenant_skipped(self, tenant_with_webhooks, tenant_polling):
        with patch("apps.customers.tasks._sync_tenant_hubspot") as mock_sync:
            result = sync_all_hubspot_tenants()

        # Only polling tenant should be synced
        assert mock_sync.call_count == 1
        mock_sync.assert_called_once_with(tenant_polling)

    def test_polling_tenant_synced(self, tenant_polling):
        with patch("apps.customers.tasks._sync_tenant_hubspot") as mock_sync:
            result = sync_all_hubspot_tenants()

        assert mock_sync.call_count == 1


def _make_context(user):
    """Create a Context object for GraphQL testing."""
    request = Mock()
    return Context(request=request, user=user)


def _run_graphql(query, variables, context):
    return schema.execute_sync(query, variable_values=variables, context_value=context)


SAVE_WEBHOOK_SETTINGS = """
    mutation SaveWebhookSettings($portalId: String, $clientSecret: String, $syncMode: String) {
        saveWebhookSettings(portalId: $portalId, clientSecret: $clientSecret, syncMode: $syncMode) {
            success
            error
        }
    }
"""

HUBSPOT_SETTINGS_QUERY = """
    query {
        hubspotSettings {
            portalId
            clientSecretSet
            syncMode
            webhookLastReceived
        }
    }
"""


class TestWebhookSettingsGraphQL:
    """Tests for the saveWebhookSettings mutation and hubspotSettings query."""

    @pytest.fixture
    def tenant(self, db):
        return Tenant.objects.create(
            name="GraphQL Tenant",
            is_active=True,
            hubspot_config={"api_key": "test-key"},
        )

    @pytest.fixture
    def admin_user(self, tenant):
        return User.objects.create_user(
            email="admin@webhook-test.local",
            password="admin123",
            tenant=tenant,
            is_admin=True,
        )

    def test_save_portal_id_and_secret(self, admin_user, tenant):
        ctx = _make_context(admin_user)
        result = _run_graphql(
            SAVE_WEBHOOK_SETTINGS,
            {"portalId": "12345678", "clientSecret": "my-secret"},
            ctx,
        )
        assert result.errors is None
        assert result.data["saveWebhookSettings"]["success"] is True

        tenant.refresh_from_db()
        assert tenant.hubspot_config["portal_id"] == "12345678"
        assert tenant.hubspot_config["client_secret"] == "my-secret"

    def test_switch_to_webhook_mode(self, admin_user, tenant):
        tenant.hubspot_config["portal_id"] = "12345678"
        tenant.hubspot_config["client_secret"] = "my-secret"
        tenant.save(update_fields=["hubspot_config"])

        ctx = _make_context(admin_user)
        result = _run_graphql(
            SAVE_WEBHOOK_SETTINGS,
            {"syncMode": "webhooks"},
            ctx,
        )
        assert result.errors is None
        assert result.data["saveWebhookSettings"]["success"] is True

        tenant.refresh_from_db()
        assert tenant.hubspot_config["sync_mode"] == "webhooks"

    def test_webhook_mode_requires_portal_and_secret(self, admin_user, tenant):
        ctx = _make_context(admin_user)
        result = _run_graphql(
            SAVE_WEBHOOK_SETTINGS,
            {"syncMode": "webhooks"},
            ctx,
        )
        assert result.errors is None
        data = result.data["saveWebhookSettings"]
        assert data["success"] is False
        assert "Portal ID" in data["error"]

    def test_invalid_sync_mode_rejected(self, admin_user, tenant):
        ctx = _make_context(admin_user)
        result = _run_graphql(
            SAVE_WEBHOOK_SETTINGS,
            {"syncMode": "invalid"},
            ctx,
        )
        assert result.errors is None
        data = result.data["saveWebhookSettings"]
        assert data["success"] is False
        assert "Invalid sync mode" in data["error"]

    def test_query_returns_webhook_fields(self, admin_user, tenant):
        tenant.hubspot_config.update({
            "portal_id": "99887766",
            "client_secret": "secret-val",
            "sync_mode": "webhooks",
            "webhook_last_received": "2026-02-25T10:00:00Z",
        })
        tenant.save(update_fields=["hubspot_config"])

        ctx = _make_context(admin_user)
        result = _run_graphql(HUBSPOT_SETTINGS_QUERY, {}, ctx)
        assert result.errors is None

        settings = result.data["hubspotSettings"]
        assert settings["portalId"] == "99887766"
        assert settings["clientSecretSet"] is True
        assert settings["syncMode"] == "webhooks"
        assert settings["webhookLastReceived"] == "2026-02-25T10:00:00Z"

    def test_query_no_secret_returns_false(self, admin_user, tenant):
        ctx = _make_context(admin_user)
        result = _run_graphql(HUBSPOT_SETTINGS_QUERY, {}, ctx)
        assert result.errors is None

        settings = result.data["hubspotSettings"]
        assert settings["clientSecretSet"] is False
        assert settings["portalId"] is None
