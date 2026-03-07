"""Tests for two-factor authentication."""
import pytest
from unittest.mock import patch, MagicMock, Mock

import pyotp

from config.schema import schema
from apps.tenants.models import Role, Tenant, TwoFactorConfig, User
from apps.core.context import Context
from apps.core.auth import create_2fa_challenge_token


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


SETUP_TOTP = """
    mutation { setupTotp { success error secret provisioningUri } }
"""

CONFIRM_TOTP = """
    mutation ConfirmTotp($code: String!) {
        confirmTotp(code: $code) { success error recoveryCodes }
    }
"""

ENABLE_EMAIL = """
    mutation { enableEmail2fa { success error recoveryCodes } }
"""

DISABLE_2FA = """
    mutation Disable2fa($password: String!) {
        disable2fa(password: $password) { success error }
    }
"""

LOGIN = """
    mutation Login($email: String!, $password: String!) {
        login(email: $email, password: $password) {
            ... on AuthPayload { accessToken refreshToken userId }
            ... on TwoFactorChallenge { requiresTwoFactor challengeToken method }
            ... on AuthError { message }
        }
    }
"""

VERIFY_2FA = """
    mutation Verify2fa($challengeToken: String!, $code: String!) {
        verify2fa(challengeToken: $challengeToken, code: $code) {
            ... on AuthPayload { accessToken refreshToken userId }
            ... on AuthError { message }
        }
    }
"""

RESET_USER_2FA = """
    mutation ResetUser2fa($userId: ID!) {
        resetUser2fa(userId: $userId) { success error }
    }
"""


class TestTotpSetup:
    def test_setup_returns_secret(self, user):
        ctx = make_context(user=user)
        result = run_graphql(SETUP_TOTP, {}, ctx)
        assert result.errors is None
        data = result.data["setupTotp"]
        assert data["success"] is True
        assert data["secret"] is not None
        assert "otpauth://" in data["provisioningUri"]

    def test_confirm_with_valid_code(self, user):
        ctx = make_context(user=user)
        # Setup
        result = run_graphql(SETUP_TOTP, {}, ctx)
        secret = result.data["setupTotp"]["secret"]

        # Generate valid code
        totp = pyotp.TOTP(secret)
        code = totp.now()

        result = run_graphql(CONFIRM_TOTP, {"code": code}, ctx)
        assert result.errors is None
        data = result.data["confirmTotp"]
        assert data["success"] is True
        assert len(data["recoveryCodes"]) == 10

        # Verify config is active
        config = TwoFactorConfig.objects.get(user=user)
        assert config.is_active is True
        assert config.method == "totp"

    def test_confirm_with_invalid_code(self, user):
        ctx = make_context(user=user)
        run_graphql(SETUP_TOTP, {}, ctx)

        result = run_graphql(CONFIRM_TOTP, {"code": "000000"}, ctx)
        data = result.data["confirmTotp"]
        assert data["success"] is False

        # Config should not be active
        config = TwoFactorConfig.objects.get(user=user)
        assert config.is_active is False


class TestEmailSetup:
    def test_enable_email_2fa_without_smtp(self, user):
        ctx = make_context(user=user)
        result = run_graphql(ENABLE_EMAIL, {}, ctx)
        data = result.data["enableEmail2fa"]
        assert data["success"] is False
        assert "SMTP" in data["error"]

    @patch("apps.core.smtp._get_config")
    def test_enable_email_2fa_with_smtp(self, mock_config, user):
        mock_config.return_value = {"host": "smtp.test.com", "port": 587}
        ctx = make_context(user=user)
        result = run_graphql(ENABLE_EMAIL, {}, ctx)
        data = result.data["enableEmail2fa"]
        assert data["success"] is True
        assert len(data["recoveryCodes"]) == 10

        config = TwoFactorConfig.objects.get(user=user)
        assert config.is_active is True
        assert config.method == "email"


class TestLoginWith2fa:
    def test_login_with_totp_returns_challenge(self, user):
        # Setup TOTP
        ctx = make_context(user=user)
        result = run_graphql(SETUP_TOTP, {}, ctx)
        secret = result.data["setupTotp"]["secret"]
        totp = pyotp.TOTP(secret)
        run_graphql(CONFIRM_TOTP, {"code": totp.now()}, ctx)

        # Login
        ctx = make_context()
        result = run_graphql(LOGIN, {"email": "test@example.com", "password": "testpass123"}, ctx)
        assert result.errors is None
        data = result.data["login"]
        assert data["requiresTwoFactor"] is True
        assert data["method"] == "totp"
        assert data["challengeToken"] is not None

    def test_verify_totp(self, user):
        # Setup TOTP
        ctx = make_context(user=user)
        result = run_graphql(SETUP_TOTP, {}, ctx)
        secret = result.data["setupTotp"]["secret"]
        totp = pyotp.TOTP(secret)
        run_graphql(CONFIRM_TOTP, {"code": totp.now()}, ctx)

        # Create challenge
        challenge = create_2fa_challenge_token(user, "totp")
        code = totp.now()

        ctx = make_context()
        result = run_graphql(VERIFY_2FA, {"challengeToken": challenge, "code": code}, ctx)
        assert result.errors is None
        data = result.data["verify2fa"]
        assert data["accessToken"] is not None

    def test_verify_with_recovery_code(self, user):
        # Setup TOTP
        ctx = make_context(user=user)
        result = run_graphql(SETUP_TOTP, {}, ctx)
        secret = result.data["setupTotp"]["secret"]
        totp = pyotp.TOTP(secret)
        result = run_graphql(CONFIRM_TOTP, {"code": totp.now()}, ctx)
        recovery_codes = result.data["confirmTotp"]["recoveryCodes"]

        # Verify with recovery code
        challenge = create_2fa_challenge_token(user, "totp")
        ctx = make_context()
        result = run_graphql(VERIFY_2FA, {"challengeToken": challenge, "code": recovery_codes[0]}, ctx)
        data = result.data["verify2fa"]
        assert data["accessToken"] is not None

        # Same recovery code should not work again
        challenge = create_2fa_challenge_token(user, "totp")
        result = run_graphql(VERIFY_2FA, {"challengeToken": challenge, "code": recovery_codes[0]}, ctx)
        data = result.data["verify2fa"]
        assert data.get("message") is not None

    def test_verify_with_invalid_code(self, user):
        challenge = create_2fa_challenge_token(user, "totp")
        ctx = make_context()
        result = run_graphql(VERIFY_2FA, {"challengeToken": challenge, "code": "000000"}, ctx)
        data = result.data["verify2fa"]
        assert data.get("message") is not None

    def test_verify_with_expired_challenge(self, user):
        ctx = make_context()
        result = run_graphql(VERIFY_2FA, {"challengeToken": "invalid.token.here", "code": "123456"}, ctx)
        data = result.data["verify2fa"]
        assert "Invalid" in data["message"] or "expired" in data["message"]


class TestDisable2fa:
    def test_disable_with_correct_password(self, user):
        # Setup TOTP first
        ctx = make_context(user=user)
        run_graphql(SETUP_TOTP, {}, ctx)
        secret = TwoFactorConfig.objects.get(user=user).get_totp_secret()
        totp = pyotp.TOTP(secret)
        run_graphql(CONFIRM_TOTP, {"code": totp.now()}, ctx)

        # Disable
        result = run_graphql(DISABLE_2FA, {"password": "testpass123"}, ctx)
        assert result.data["disable2fa"]["success"] is True
        assert not TwoFactorConfig.objects.filter(user=user).exists()

    def test_disable_with_wrong_password(self, user):
        ctx = make_context(user=user)
        run_graphql(SETUP_TOTP, {}, ctx)
        secret = TwoFactorConfig.objects.get(user=user).get_totp_secret()
        totp = pyotp.TOTP(secret)
        run_graphql(CONFIRM_TOTP, {"code": totp.now()}, ctx)

        result = run_graphql(DISABLE_2FA, {"password": "wrongpassword"}, ctx)
        assert result.data["disable2fa"]["success"] is False

    def test_disable_with_enforcement(self, user, tenant):
        # Enable enforcement
        tenant.settings = {"two_factor_enforced": True}
        tenant.save()

        ctx = make_context(user=user)
        run_graphql(SETUP_TOTP, {}, ctx)
        secret = TwoFactorConfig.objects.get(user=user).get_totp_secret()
        totp = pyotp.TOTP(secret)
        run_graphql(CONFIRM_TOTP, {"code": totp.now()}, ctx)

        result = run_graphql(DISABLE_2FA, {"password": "testpass123"}, ctx)
        assert result.data["disable2fa"]["success"] is False
        assert "required" in result.data["disable2fa"]["error"]


class TestAdminReset:
    def test_admin_resets_user_2fa(self, user, other_user):
        # Setup TOTP for other_user
        ctx = make_context(user=other_user)
        run_graphql(SETUP_TOTP, {}, ctx)
        secret = TwoFactorConfig.objects.get(user=other_user).get_totp_secret()
        totp = pyotp.TOTP(secret)
        run_graphql(CONFIRM_TOTP, {"code": totp.now()}, ctx)

        # Admin resets
        ctx = make_context(user=user)
        result = run_graphql(RESET_USER_2FA, {"userId": str(other_user.id)}, ctx)
        assert result.data["resetUser2fa"]["success"] is True
        assert not TwoFactorConfig.objects.filter(user=other_user).exists()


class TestEnforcement:
    def test_login_without_2fa_in_enforced_tenant(self, user, tenant):
        tenant.settings = {"two_factor_enforced": True}
        tenant.save()

        ctx = make_context()
        result = run_graphql(LOGIN, {"email": "test@example.com", "password": "testpass123"}, ctx)
        data = result.data["login"]
        # Should get a restricted token (accessToken present but refreshToken empty)
        assert data.get("accessToken") is not None
        assert data.get("refreshToken") == ""
