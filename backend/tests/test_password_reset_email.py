"""Tests for self-service password reset via email."""
import pytest
from unittest.mock import patch, MagicMock, Mock

from config.schema import schema
from apps.tenants.models import PasswordResetToken, Role, Tenant, User
from apps.core.context import Context


MUTATION_REQUEST = """
    mutation RequestPasswordReset($email: String!) {
        requestPasswordReset(email: $email) {
            success
            error
        }
    }
"""

MUTATION_ADMIN_RESET = """
    mutation CreatePasswordReset($userId: ID!, $baseUrl: String) {
        createPasswordReset(userId: $userId, baseUrl: $baseUrl) {
            success
            resetUrl
            error
        }
    }
"""


def run_graphql(query, variables, context):
    return schema.execute_sync(query, variable_values=variables, context_value=context)


def make_context(user=None):
    request = Mock()
    request.headers = {"Origin": "http://localhost:5173"}
    return Context(request=request, user=user)


@pytest.fixture
def tenant(db):
    return Tenant.objects.create(name="Test Company", currency="EUR")


@pytest.fixture
def user(db, tenant):
    u = User.objects.create_user(
        email="test@example.com", password="testpass123", tenant=tenant
    )
    admin_role = Role.objects.get(tenant=tenant, name="Admin")
    u.roles.add(admin_role)
    return u


@pytest.fixture
def other_user(db, tenant):
    return User.objects.create_user(
        email="other@example.com", password="testpass123", tenant=tenant
    )


class TestRequestPasswordReset:
    @patch("apps.tenants.tasks.send_password_reset_email")
    def test_registered_email_creates_token_and_dispatches(self, mock_task, user):
        mock_task.delay = MagicMock()
        ctx = make_context()

        result = run_graphql(MUTATION_REQUEST, {"email": user.email}, ctx)
        assert result.errors is None
        assert result.data["requestPasswordReset"]["success"] is True

        assert PasswordResetToken.objects.filter(user=user).exists()
        mock_task.delay.assert_called_once()
        assert mock_task.delay.call_args[0][0] == user.id

    @patch("apps.tenants.tasks.send_password_reset_email")
    def test_unregistered_email_returns_success_no_token(self, mock_task, db):
        mock_task.delay = MagicMock()
        ctx = make_context()

        result = run_graphql(MUTATION_REQUEST, {"email": "nobody@example.com"}, ctx)
        assert result.errors is None
        assert result.data["requestPasswordReset"]["success"] is True

        assert PasswordResetToken.objects.count() == 0
        mock_task.delay.assert_not_called()

    @patch("apps.tenants.tasks.send_password_reset_email")
    def test_rate_limiting(self, mock_task, user):
        mock_task.delay = MagicMock()
        ctx = make_context()

        # Send 6 requests — first 5 should dispatch, 6th should be silently discarded
        for _ in range(6):
            run_graphql(MUTATION_REQUEST, {"email": user.email}, ctx)

        dispatched = mock_task.delay.call_count
        tokens = PasswordResetToken.objects.filter(user=user).count()

        # At most 5 should have gone through
        assert dispatched <= 5
        assert tokens <= 5

        # 7th should definitely be discarded
        mock_task.delay.reset_mock()
        result = run_graphql(MUTATION_REQUEST, {"email": user.email}, ctx)
        assert result.data["requestPasswordReset"]["success"] is True
        mock_task.delay.assert_not_called()


class TestAdminResetSendsEmail:
    @patch("apps.tenants.tasks.send_password_reset_email")
    def test_admin_reset_dispatches_email(self, mock_task, user, other_user):
        mock_task.delay = MagicMock()
        ctx = make_context(user=user)

        result = run_graphql(
            MUTATION_ADMIN_RESET,
            {"userId": str(other_user.id), "baseUrl": "http://localhost:5173"},
            ctx,
        )
        assert result.errors is None
        assert result.data["createPasswordReset"]["success"] is True
        assert result.data["createPasswordReset"]["resetUrl"] is not None

        mock_task.delay.assert_called_once()
        assert mock_task.delay.call_args[0][0] == other_user.id

    @patch("apps.tenants.tasks.send_password_reset_email")
    def test_admin_reset_works_if_email_fails(self, mock_task, user, other_user):
        mock_task.delay = MagicMock(side_effect=Exception("Celery down"))
        ctx = make_context(user=user)

        result = run_graphql(
            MUTATION_ADMIN_RESET,
            {"userId": str(other_user.id), "baseUrl": "http://localhost:5173"},
            ctx,
        )
        assert result.errors is None
        assert result.data["createPasswordReset"]["success"] is True
        assert result.data["createPasswordReset"]["resetUrl"] is not None
