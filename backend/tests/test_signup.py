"""Tests for tenant self-signup: signUp and verifySignup mutations."""
import pytest
from datetime import timedelta
from unittest.mock import Mock, patch

from django.utils import timezone

from config.schema import schema
from apps.tenants.models import Role, SignupVerification, Tenant, User
from apps.core.context import Context


def run_graphql(query, variables=None, context=None):
    """Helper to run GraphQL queries synchronously."""
    if context is None:
        context = Context(request=Mock(), user=None)
    return schema.execute_sync(query, variable_values=variables or {}, context_value=context)


SIGN_UP_MUTATION = """
mutation SignUp($companyName: String!, $email: String!, $firstName: String!, $lastName: String!, $password: String!, $baseUrl: String) {
    signUp(companyName: $companyName, email: $email, firstName: $firstName, lastName: $lastName, password: $password, baseUrl: $baseUrl) {
        success
        error
    }
}
"""

VERIFY_SIGNUP_MUTATION = """
mutation VerifySignup($token: String!) {
    verifySignup(token: $token) {
        success
        error
        accessToken
        refreshToken
    }
}
"""


class TestSignUp:
    """Tests for the signUp mutation."""

    @patch("apps.tenants.tasks.send_signup_verification_email.delay")
    def test_signup_happy_path(self, mock_email, db):
        """Successful signup creates inactive tenant, user, roles, and verification token."""
        result = run_graphql(SIGN_UP_MUTATION, {
            "companyName": "New Corp",
            "email": "new@example.com",
            "firstName": "John",
            "lastName": "Doe",
            "password": "secure123",
            "baseUrl": "http://localhost:4000",
        })

        assert result.errors is None
        assert result.data["signUp"]["success"] is True

        # Tenant created but inactive
        tenant = Tenant.objects.get(name="New Corp")
        assert tenant.is_active is False

        # User created but inactive
        user = User.objects.get(email="new@example.com")
        assert user.is_active is False
        assert user.tenant == tenant
        assert user.first_name == "John"
        assert user.last_name == "Doe"

        # User has Admin role
        assert user.roles.filter(name="Admin").exists()

        # Default roles seeded
        assert Role.objects.filter(tenant=tenant).count() == 3

        # Verification token created
        verification = SignupVerification.objects.get(user=user)
        assert verification.tenant == tenant
        assert verification.email == "new@example.com"
        assert verification.used is False
        assert verification.is_valid

        # Email task called
        mock_email.assert_called_once_with(verification.id, "http://localhost:4000")

    @patch("apps.tenants.tasks.send_signup_verification_email.delay")
    def test_signup_duplicate_email(self, mock_email, db):
        """Signup with existing email returns generic error."""
        # Create existing user
        tenant = Tenant.objects.create(name="Existing")
        User.objects.create_user(email="taken@example.com", password="pass1234", tenant=tenant)

        result = run_graphql(SIGN_UP_MUTATION, {
            "companyName": "New Corp",
            "email": "taken@example.com",
            "firstName": "John",
            "lastName": "Doe",
            "password": "secure123",
        })

        assert result.data["signUp"]["success"] is False
        assert "sign in" in result.data["signUp"]["error"].lower()
        mock_email.assert_not_called()

    def test_signup_short_password(self, db):
        """Signup with password < 8 chars fails."""
        result = run_graphql(SIGN_UP_MUTATION, {
            "companyName": "New Corp",
            "email": "new@example.com",
            "firstName": "John",
            "lastName": "Doe",
            "password": "short",
        })

        assert result.data["signUp"]["success"] is False
        assert "8 characters" in result.data["signUp"]["error"]

    def test_signup_invalid_email(self, db):
        """Signup with invalid email fails."""
        result = run_graphql(SIGN_UP_MUTATION, {
            "companyName": "New Corp",
            "email": "not-an-email",
            "firstName": "John",
            "lastName": "Doe",
            "password": "secure123",
        })

        assert result.data["signUp"]["success"] is False
        assert "email" in result.data["signUp"]["error"].lower()

    def test_signup_empty_company_name(self, db):
        """Signup with empty company name fails."""
        result = run_graphql(SIGN_UP_MUTATION, {
            "companyName": "  ",
            "email": "new@example.com",
            "firstName": "John",
            "lastName": "Doe",
            "password": "secure123",
        })

        assert result.data["signUp"]["success"] is False
        assert "company" in result.data["signUp"]["error"].lower()

    @pytest.mark.django_db
    def test_signup_disabled(self, db, settings):
        """Signup when SIGNUP_ENABLED=False returns error."""
        settings.SIGNUP_ENABLED = False

        result = run_graphql(SIGN_UP_MUTATION, {
            "companyName": "New Corp",
            "email": "new@example.com",
            "firstName": "John",
            "lastName": "Doe",
            "password": "secure123",
        })

        assert result.data["signUp"]["success"] is False
        assert "disabled" in result.data["signUp"]["error"].lower()


class TestVerifySignup:
    """Tests for the verifySignup mutation."""

    @pytest.fixture
    def signup_data(self, db):
        """Create an inactive tenant/user with verification token."""
        tenant = Tenant.objects.create(name="Verify Corp", is_active=False)
        user = User.objects.create_user(
            email="verify@example.com",
            password="secure123",
            tenant=tenant,
            is_active=False,
        )
        admin_role = Role.objects.get(tenant=tenant, name="Admin")
        user.roles.add(admin_role)
        verification = SignupVerification.create_token(tenant=tenant, user=user)
        return tenant, user, verification

    def test_verify_happy_path(self, signup_data):
        """Successful verification activates tenant and user, returns tokens."""
        tenant, user, verification = signup_data

        result = run_graphql(VERIFY_SIGNUP_MUTATION, {"token": verification.token})

        assert result.errors is None
        data = result.data["verifySignup"]
        assert data["success"] is True
        assert data["accessToken"] is not None
        assert data["refreshToken"] is not None

        # Tenant and user now active
        tenant.refresh_from_db()
        user.refresh_from_db()
        assert tenant.is_active is True
        assert user.is_active is True

        # Token marked as used
        verification.refresh_from_db()
        assert verification.used is True

    def test_verify_invalid_token(self, db):
        """Invalid token returns error."""
        result = run_graphql(VERIFY_SIGNUP_MUTATION, {"token": "nonexistent"})

        data = result.data["verifySignup"]
        assert data["success"] is False
        assert "invalid" in data["error"].lower()

    def test_verify_expired_token(self, signup_data):
        """Expired token returns error."""
        _, _, verification = signup_data
        verification.expires_at = timezone.now() - timedelta(hours=1)
        verification.save()

        result = run_graphql(VERIFY_SIGNUP_MUTATION, {"token": verification.token})

        data = result.data["verifySignup"]
        assert data["success"] is False
        assert "expired" in data["error"].lower()

    def test_verify_used_token(self, signup_data):
        """Already-used token returns error."""
        _, _, verification = signup_data
        verification.used = True
        verification.save()

        result = run_graphql(VERIFY_SIGNUP_MUTATION, {"token": verification.token})

        data = result.data["verifySignup"]
        assert data["success"] is False
        assert "already been used" in data["error"].lower()
