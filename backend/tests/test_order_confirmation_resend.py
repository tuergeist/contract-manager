"""Tests for the resend order confirmation mutation."""
from datetime import date
from unittest.mock import Mock, patch

import pytest

from apps.contracts.models import Contract
from apps.contracts.order_confirmation_models import OrderConfirmation
from apps.core.context import Context
from apps.customers.models import Customer
from apps.tenants.models import Role, Tenant, User
from config.schema import schema


def run_graphql(query, variables, context):
    return schema.execute_sync(query, variable_values=variables, context_value=context)


def make_context(user):
    return Context(request=Mock(), user=user)


@pytest.fixture
def tenant(db):
    return Tenant.objects.create(name="Test Company", currency="EUR")


@pytest.fixture
def user(db, tenant):
    u = User.objects.create_user(
        email="admin@example.com", password="pw123456", tenant=tenant
    )
    u.roles.add(Role.objects.get(tenant=tenant, name="Admin"))
    return u


@pytest.fixture
def viewer_user(db, tenant):
    u = User.objects.create_user(
        email="viewer@example.com", password="pw123456", tenant=tenant
    )
    u.roles.add(Role.objects.get(tenant=tenant, name="Viewer"))
    return u


@pytest.fixture
def contract(db, tenant):
    customer = Customer.objects.create(
        tenant=tenant, name="Cust", billing_emails=["c@x.com"]
    )
    return Contract.objects.create(
        tenant=tenant,
        customer=customer,
        name="C1",
        status=Contract.Status.ACTIVE,
        start_date=date(2026, 1, 1),
        billing_start_date=date(2026, 1, 1),
        billing_interval=Contract.BillingInterval.MONTHLY,
        billing_anchor_day=1,
    )


@pytest.fixture
def sent_oc(db, tenant, contract):
    return OrderConfirmation.objects.create(
        tenant=tenant,
        contract=contract,
        order_confirmation_number="AB-2026-0001",
        status=OrderConfirmation.Status.SENT,
    )


RESEND = """
mutation Resend($id: ID!) {
  resendOrderConfirmation(orderConfirmationId: $id) {
    success
    error
  }
}
"""


@pytest.mark.django_db
class TestResendOrderConfirmation:
    @patch("apps.contracts.tasks.send_order_confirmation_email_task.delay")
    def test_resend_allowed_when_already_sent(self, mock_delay, user, sent_oc):
        """Re-send must succeed even though the OC is already SENT."""
        result = run_graphql(RESEND, {"id": str(sent_oc.id)}, make_context(user))
        assert result.errors is None
        payload = result.data["resendOrderConfirmation"]
        assert payload["success"] is True
        assert payload["error"] is None
        mock_delay.assert_called_once_with(sent_oc.id, user_id=user.id)

    @patch("apps.contracts.tasks.send_order_confirmation_email_task.delay")
    def test_resend_not_found(self, mock_delay, user):
        result = run_graphql(RESEND, {"id": "999999"}, make_context(user))
        payload = result.data["resendOrderConfirmation"]
        assert payload["success"] is False
        assert payload["error"] == "Order confirmation not found"
        mock_delay.assert_not_called()

    @patch("apps.contracts.tasks.send_order_confirmation_email_task.delay")
    def test_resend_requires_write_permission(self, mock_delay, viewer_user, sent_oc):
        result = run_graphql(RESEND, {"id": str(sent_oc.id)}, make_context(viewer_user))
        payload = result.data["resendOrderConfirmation"]
        assert payload["success"] is False
        assert payload["error"]
        mock_delay.assert_not_called()
