"""Tests for notification event system."""
import pytest
from unittest.mock import Mock, patch, MagicMock

from apps.core.notifications import is_subscribed, notify, NOTIFICATION_TYPES
from apps.core.context import Context
from apps.tenants.models import Role, Tenant, User
from apps.tenants.schema import TenantMutation, TenantQuery


def _make_context(user):
    request = Mock()
    request.tenant = user.tenant
    return Context(request=request, user=user)


@pytest.fixture
def admin_user(db, tenant):
    user = User.objects.create_user(
        email="admin@test.local",
        password="test1234",
        tenant=tenant,
        is_admin=True,
        first_name="Admin",
        last_name="User",
    )
    admin_role = Role.objects.get(tenant=tenant, name="Admin")
    user.roles.add(admin_role)
    return user


@pytest.fixture
def other_user(db, tenant):
    return User.objects.create_user(
        email="other@test.local",
        password="test1234",
        tenant=tenant,
        first_name="Other",
        last_name="Person",
    )


@pytest.fixture
def smtp_tenant(tenant):
    tenant.settings = {
        "smtp": {
            "host": "smtp.example.com",
            "port": 587,
            "username": "user@example.com",
            "password": "secret123",
            "from_address": "noreply@example.com",
            "use_tls": True,
        }
    }
    tenant.save()
    return tenant


class TestIsSubscribed:
    def test_default_subscribed(self, admin_user):
        assert is_subscribed(admin_user, "todo_assigned") is True
        assert is_subscribed(admin_user, "hubspot_new_contract") is True

    def test_explicit_false_unsubscribed(self, admin_user):
        admin_user.notification_preferences = {"todo_assigned": False}
        assert is_subscribed(admin_user, "todo_assigned") is False

    def test_explicit_true_subscribed(self, admin_user):
        admin_user.notification_preferences = {"todo_assigned": True}
        assert is_subscribed(admin_user, "todo_assigned") is True

    def test_other_types_unaffected(self, admin_user):
        admin_user.notification_preferences = {"todo_assigned": False}
        assert is_subscribed(admin_user, "hubspot_new_contract") is True


class TestNotify:
    @patch("apps.core.notifications.send_notification")
    def test_sends_to_subscribed_user(self, mock_send, admin_user, smtp_tenant):
        todo = Mock(text="Fix the bug", assigned_to=admin_user)
        assigner = Mock()
        assigner.get_full_name.return_value = "Boss Person"

        notify(
            smtp_tenant,
            "todo_assigned",
            recipients=[admin_user],
            todo=todo,
            assigner=assigner,
        )

        mock_send.assert_called_once()
        call_kwargs = mock_send.call_args
        assert call_kwargs[1]["to"] == [admin_user.email]
        assert "Fix the bug" in call_kwargs[1]["body_html"]
        assert "Boss Person" in call_kwargs[1]["body_html"]

    @patch("apps.core.notifications.send_notification")
    def test_skips_unsubscribed_user(self, mock_send, admin_user, smtp_tenant):
        admin_user.notification_preferences = {"todo_assigned": False}
        admin_user.save()

        todo = Mock(text="Fix the bug")
        assigner = Mock()
        assigner.get_full_name.return_value = "Boss"

        notify(
            smtp_tenant,
            "todo_assigned",
            recipients=[admin_user],
            todo=todo,
            assigner=assigner,
        )

        mock_send.assert_not_called()

    @patch("apps.core.notifications.send_notification")
    def test_catches_smtp_error(self, mock_send, admin_user, smtp_tenant):
        from apps.core.smtp import SmtpError
        mock_send.side_effect = SmtpError("Connection refused")

        todo = Mock(text="Fix the bug")
        assigner = Mock()
        assigner.get_full_name.return_value = "Boss"

        # Should not raise
        notify(
            smtp_tenant,
            "todo_assigned",
            recipients=[admin_user],
            todo=todo,
            assigner=assigner,
        )

    @patch("apps.core.notifications.send_notification")
    def test_no_recipients_no_send(self, mock_send, smtp_tenant):
        notify(smtp_tenant, "todo_assigned", recipients=[])
        mock_send.assert_not_called()

    @patch("apps.core.notifications.send_notification")
    def test_unknown_event_type(self, mock_send, admin_user, smtp_tenant):
        notify(smtp_tenant, "nonexistent_type", recipients=[admin_user])
        mock_send.assert_not_called()


class TestTodoAssignedNotification:
    @patch("apps.core.notifications.send_notification")
    def test_fires_on_create_with_different_assignee(self, mock_send, admin_user, other_user, smtp_tenant):
        from apps.todos.models import TodoItem
        from apps.customers.models import Customer

        customer = Customer.objects.create(
            tenant=smtp_tenant, name="Test Customer"
        )

        from apps.todos.schema import TodoMutation
        info = Mock()
        info.context = _make_context(admin_user)

        mutation = TodoMutation()
        result = mutation.create_todo(
            info,
            text="Please review this",
            assigned_to_id=other_user.id,
            customer_id=customer.id,
        )

        assert result.success is True
        mock_send.assert_called_once()
        call_kwargs = mock_send.call_args[1]
        assert call_kwargs["to"] == [other_user.email]
        assert "Please review this" in call_kwargs["body_html"]

    @patch("apps.core.notifications.send_notification")
    def test_no_notification_on_self_assign(self, mock_send, admin_user, smtp_tenant):
        from apps.customers.models import Customer

        customer = Customer.objects.create(
            tenant=smtp_tenant, name="Test Customer"
        )

        from apps.todos.schema import TodoMutation
        info = Mock()
        info.context = _make_context(admin_user)

        mutation = TodoMutation()
        result = mutation.create_todo(
            info,
            text="My own todo",
            customer_id=customer.id,
        )

        assert result.success is True
        mock_send.assert_not_called()

    @patch("apps.core.notifications.send_notification")
    def test_fires_on_reassignment(self, mock_send, admin_user, other_user, smtp_tenant):
        from apps.todos.models import TodoItem
        from apps.customers.models import Customer

        customer = Customer.objects.create(
            tenant=smtp_tenant, name="Test Customer"
        )
        todo = TodoItem.objects.create(
            tenant=smtp_tenant,
            text="Reassign me",
            created_by=admin_user,
            assigned_to=admin_user,
            customer=customer,
        )

        from apps.todos.schema import TodoMutation
        info = Mock()
        info.context = _make_context(admin_user)

        mutation = TodoMutation()
        result = mutation.update_todo(info, todo_id=todo.id, assigned_to_id=other_user.id)

        assert result.success is True
        mock_send.assert_called_once()
        call_kwargs = mock_send.call_args[1]
        assert call_kwargs["to"] == [other_user.email]


class TestHubspotNewContractNotification:
    @patch("apps.core.notifications.send_notification")
    def test_fires_on_new_contract(self, mock_send, admin_user, other_user, smtp_tenant):
        # Both users are subscribed by default
        notify(
            smtp_tenant,
            "hubspot_new_contract",
            recipients=[admin_user, other_user],
            contract_name="Big Deal",
            customer_name="Acme Corp",
        )

        assert mock_send.call_count == 2
        emails_sent = [call[1]["to"][0] for call in mock_send.call_args_list]
        assert admin_user.email in emails_sent
        assert other_user.email in emails_sent

    @patch("apps.core.notifications.send_notification")
    def test_skips_opted_out_user(self, mock_send, admin_user, other_user, smtp_tenant):
        other_user.notification_preferences = {"hubspot_new_contract": False}
        other_user.save()

        notify(
            smtp_tenant,
            "hubspot_new_contract",
            recipients=[admin_user, other_user],
            contract_name="Big Deal",
            customer_name="Acme Corp",
        )

        assert mock_send.call_count == 1
        assert mock_send.call_args[1]["to"] == [admin_user.email]


class TestNotificationPreferencesQuery:
    def test_defaults_all_true(self, admin_user):
        info = Mock()
        info.context = _make_context(admin_user)

        query = TenantQuery()
        result = query.notification_preferences(info)
        assert result.todo_assigned is True
        assert result.hubspot_new_contract is True

    def test_reflects_opt_outs(self, admin_user):
        admin_user.notification_preferences = {"todo_assigned": False}
        admin_user.save()

        info = Mock()
        info.context = _make_context(admin_user)

        query = TenantQuery()
        result = query.notification_preferences(info)
        assert result.todo_assigned is False
        assert result.hubspot_new_contract is True


class TestUpdateNotificationPreferencesMutation:
    def test_partial_update(self, admin_user):
        info = Mock()
        info.context = _make_context(admin_user)

        mutation = TenantMutation()
        result = mutation.update_notification_preferences(info, todo_assigned=False)
        assert result.success is True

        admin_user.refresh_from_db()
        assert admin_user.notification_preferences["todo_assigned"] is False

    def test_preserves_existing(self, admin_user):
        admin_user.notification_preferences = {"todo_assigned": False}
        admin_user.save()

        info = Mock()
        info.context = _make_context(admin_user)

        mutation = TenantMutation()
        result = mutation.update_notification_preferences(info, hubspot_new_contract=False)
        assert result.success is True

        admin_user.refresh_from_db()
        assert admin_user.notification_preferences["todo_assigned"] is False
        assert admin_user.notification_preferences["hubspot_new_contract"] is False

    def test_resubscribe(self, admin_user):
        admin_user.notification_preferences = {"todo_assigned": False}
        admin_user.save()

        info = Mock()
        info.context = _make_context(admin_user)

        mutation = TenantMutation()
        result = mutation.update_notification_preferences(info, todo_assigned=True)
        assert result.success is True

        admin_user.refresh_from_db()
        assert admin_user.notification_preferences["todo_assigned"] is True
