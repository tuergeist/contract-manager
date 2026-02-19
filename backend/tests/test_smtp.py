"""Tests for SMTP notification service."""
import pytest
import smtplib
from unittest.mock import Mock, patch, MagicMock

from apps.core.smtp import SmtpError, _get_config, send_notification
from apps.core.smtp import test_connection as smtp_test_connection
from apps.core.context import Context
from apps.tenants.models import Role, Tenant, User
from apps.tenants.schema import TenantMutation, TenantQuery


SMTP_CONFIG = {
    "host": "smtp.example.com",
    "port": 587,
    "username": "user@example.com",
    "password": "secret123",
    "from_address": "noreply@example.com",
    "use_tls": True,
}


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
    )
    admin_role = Role.objects.get(tenant=tenant, name="Admin")
    user.roles.add(admin_role)
    return user


@pytest.fixture
def smtp_tenant(tenant):
    tenant.settings = {"smtp": SMTP_CONFIG.copy()}
    tenant.save()
    return tenant


class TestGetConfig:
    def test_returns_config_when_present(self, smtp_tenant):
        config = _get_config(smtp_tenant)
        assert config["host"] == "smtp.example.com"
        assert config["port"] == 587
        assert config["username"] == "user@example.com"
        assert config["from_address"] == "noreply@example.com"

    def test_raises_when_no_settings(self, tenant):
        with pytest.raises(SmtpError, match="SMTP not configured"):
            _get_config(tenant)

    def test_raises_when_missing_host(self, tenant):
        tenant.settings = {"smtp": {"port": 587, "username": "u", "password": "p", "from_address": "a"}}
        with pytest.raises(SmtpError, match="SMTP not configured"):
            _get_config(tenant)

    def test_raises_when_missing_password(self, tenant):
        tenant.settings = {"smtp": {"host": "h", "port": 587, "username": "u", "from_address": "a"}}
        with pytest.raises(SmtpError, match="SMTP not configured"):
            _get_config(tenant)


class TestTestConnection:
    @patch("apps.core.smtp.smtplib.SMTP")
    def test_successful_connection(self, mock_smtp_class, smtp_tenant):
        mock_server = MagicMock()
        mock_smtp_class.return_value = mock_server

        result = smtp_test_connection(smtp_tenant)

        assert result["success"] is True
        mock_smtp_class.assert_called_once_with("smtp.example.com", 587, timeout=15)
        mock_server.ehlo.assert_called()
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("user@example.com", "secret123")
        mock_server.quit.assert_called_once()

    @patch("apps.core.smtp.smtplib.SMTP")
    def test_no_tls_when_disabled(self, mock_smtp_class, tenant):
        tenant.settings = {"smtp": {**SMTP_CONFIG, "use_tls": False}}
        tenant.save()

        mock_server = MagicMock()
        mock_smtp_class.return_value = mock_server

        smtp_test_connection(tenant)

        mock_server.starttls.assert_not_called()

    @patch("apps.core.smtp.smtplib.SMTP")
    def test_connection_error(self, mock_smtp_class, smtp_tenant):
        mock_smtp_class.side_effect = OSError("Connection refused")

        with pytest.raises(SmtpError, match="SMTP connection failed"):
            smtp_test_connection(smtp_tenant)

    @patch("apps.core.smtp.smtplib.SMTP")
    def test_auth_error(self, mock_smtp_class, smtp_tenant):
        mock_server = MagicMock()
        mock_smtp_class.return_value = mock_server
        mock_server.login.side_effect = smtplib.SMTPAuthenticationError(535, b"Auth failed")

        with pytest.raises(SmtpError, match="SMTP connection failed"):
            smtp_test_connection(smtp_tenant)


class TestSendNotification:
    @patch("apps.core.smtp.smtplib.SMTP")
    def test_sends_email(self, mock_smtp_class, smtp_tenant):
        mock_server = MagicMock()
        mock_smtp_class.return_value = mock_server

        send_notification(
            smtp_tenant,
            to=["recipient@example.com"],
            subject="Test Subject",
            body_html="<p>Hello</p>",
        )

        mock_server.sendmail.assert_called_once()
        call_args = mock_server.sendmail.call_args
        assert call_args[0][0] == "noreply@example.com"
        assert call_args[0][1] == ["recipient@example.com"]
        assert "Test Subject" in call_args[0][2]
        assert "<p>Hello</p>" in call_args[0][2]

    @patch("apps.core.smtp.smtplib.SMTP")
    def test_multiple_recipients(self, mock_smtp_class, smtp_tenant):
        mock_server = MagicMock()
        mock_smtp_class.return_value = mock_server

        send_notification(
            smtp_tenant,
            to=["a@example.com", "b@example.com"],
            subject="Test",
            body_html="<p>Hi</p>",
        )

        call_args = mock_server.sendmail.call_args
        assert call_args[0][1] == ["a@example.com", "b@example.com"]

    @patch("apps.core.smtp.smtplib.SMTP")
    def test_uses_from_name_in_header(self, mock_smtp_class, tenant):
        tenant.settings = {"smtp": {**SMTP_CONFIG, "from_name": "Contract Cora"}}
        tenant.save()

        mock_server = MagicMock()
        mock_smtp_class.return_value = mock_server

        send_notification(tenant, to=["a@b.com"], subject="Test", body_html="<p>Hi</p>")

        call_args = mock_server.sendmail.call_args
        msg_str = call_args[0][2]
        assert "Contract Cora" in msg_str
        assert "noreply@example.com" in msg_str

    def test_raises_when_not_configured(self, tenant):
        with pytest.raises(SmtpError, match="SMTP not configured"):
            send_notification(tenant, to=["a@b.com"], subject="x", body_html="<p>x</p>")

    @patch("apps.core.smtp.smtplib.SMTP")
    def test_smtp_send_error(self, mock_smtp_class, smtp_tenant):
        mock_server = MagicMock()
        mock_smtp_class.return_value = mock_server
        mock_server.sendmail.side_effect = smtplib.SMTPRecipientsRefused({"a@b.com": (550, b"Rejected")})

        with pytest.raises(SmtpError, match="Failed to send email"):
            send_notification(smtp_tenant, to=["a@b.com"], subject="x", body_html="<p>x</p>")


class TestSaveSmtpSettingsMutation:
    def test_saves_config(self, admin_user):
        ctx = _make_context(admin_user)
        info = Mock()
        info.context = ctx

        mutation = TenantMutation()
        result = mutation.save_smtp_settings(
            info,
            host="smtp.example.com",
            port=587,
            username="user@example.com",
            password="secret",
            from_name="Contract Cora",
            from_address="noreply@example.com",
            use_tls=True,
        )
        assert result.success is True

        admin_user.tenant.refresh_from_db()
        smtp = admin_user.tenant.settings["smtp"]
        assert smtp["host"] == "smtp.example.com"
        assert smtp["port"] == 587
        assert smtp["password"] == "secret"
        assert smtp["from_name"] == "Contract Cora"
        assert smtp["use_tls"] is True

    def test_preserves_password_when_empty(self, admin_user):
        admin_user.tenant.settings = {"smtp": SMTP_CONFIG.copy()}
        admin_user.tenant.save()

        ctx = _make_context(admin_user)
        info = Mock()
        info.context = ctx

        mutation = TenantMutation()
        result = mutation.save_smtp_settings(
            info,
            host="new-host.com",
            port=465,
            username="new-user",
            password="",
            from_name="Test",
            from_address="new@example.com",
        )
        assert result.success is True

        admin_user.tenant.refresh_from_db()
        smtp = admin_user.tenant.settings["smtp"]
        assert smtp["host"] == "new-host.com"
        assert smtp["password"] == "secret123"  # preserved from original


class TestSmtpSettingsQuery:
    def test_returns_defaults_when_unconfigured(self, admin_user):
        ctx = _make_context(admin_user)
        info = Mock()
        info.context = ctx

        query = TenantQuery()
        result = query.smtp_settings(info)
        assert result.is_configured is False
        assert result.host == ""
        assert result.port == 587
        assert result.password_set is False

    def test_returns_configured_settings(self, admin_user):
        admin_user.tenant.settings = {"smtp": SMTP_CONFIG.copy()}
        admin_user.tenant.save()

        ctx = _make_context(admin_user)
        info = Mock()
        info.context = ctx

        query = TenantQuery()
        result = query.smtp_settings(info)
        assert result.is_configured is True
        assert result.host == "smtp.example.com"
        assert result.port == 587
        assert result.username == "user@example.com"
        assert result.from_address == "noreply@example.com"
        assert result.use_tls is True
        assert result.password_set is True


class TestTestSmtpConnectionMutation:
    @patch("apps.core.smtp.test_connection")
    def test_success(self, mock_test, admin_user):
        mock_test.return_value = {"success": True}

        ctx = _make_context(admin_user)
        info = Mock()
        info.context = ctx

        mutation = TenantMutation()
        result = mutation.test_smtp_connection(info)
        assert result.success is True

    @patch("apps.core.smtp.test_connection")
    def test_error(self, mock_test, admin_user):
        mock_test.side_effect = SmtpError("Connection refused")

        ctx = _make_context(admin_user)
        info = Mock()
        info.context = ctx

        mutation = TenantMutation()
        result = mutation.test_smtp_connection(info)
        assert result.success is False
        assert "Connection refused" in result.error


class TestSendSmtpTestEmailMutation:
    @patch("apps.core.smtp.send_notification")
    def test_sends_to_current_user(self, mock_send, admin_user):
        ctx = _make_context(admin_user)
        info = Mock()
        info.context = ctx

        mutation = TenantMutation()
        result = mutation.send_smtp_test_email(info)
        assert result.success is True

        mock_send.assert_called_once()
        call_kwargs = mock_send.call_args
        assert call_kwargs[1]["to"] == [admin_user.email]
        assert "Test Notification" in call_kwargs[1]["subject"]

    @patch("apps.core.smtp.send_notification")
    def test_error_passthrough(self, mock_send, admin_user):
        mock_send.side_effect = SmtpError("SMTP server error")

        ctx = _make_context(admin_user)
        info = Mock()
        info.context = ctx

        mutation = TenantMutation()
        result = mutation.send_smtp_test_email(info)
        assert result.success is False
        assert "SMTP server error" in result.error
