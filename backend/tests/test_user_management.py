"""Tests for user management: invitations, password change/reset, and user deactivation."""
import pytest
from datetime import timedelta
from unittest.mock import Mock

from django.utils import timezone

from config.schema import schema
from apps.tenants.models import Role, Tenant, User, UserInvitation, PasswordResetToken
from apps.core.context import Context


def run_graphql(query, variables, context):
    """Helper to run GraphQL queries synchronously."""
    return schema.execute_sync(query, variable_values=variables, context_value=context)


def make_context(user=None):
    """Create a proper Context object for GraphQL testing."""
    request = Mock()
    return Context(request=request, user=user)


@pytest.fixture
def tenant(db):
    """Create a test tenant."""
    return Tenant.objects.create(
        name="Test Company",
        currency="EUR",
    )


@pytest.fixture
def admin_user(db, tenant):
    """Create an admin test user."""
    u = User.objects.create_user(
        email="admin@example.com",
        password="admin123",
        tenant=tenant,
        is_admin=True,
    )
    admin_role = Role.objects.get(tenant=tenant, name="Admin")
    u.roles.add(admin_role)
    return u


@pytest.fixture
def regular_user(db, tenant):
    """Create a regular (non-admin) test user."""
    u = User.objects.create_user(
        email="user@example.com",
        password="user123",
        tenant=tenant,
        is_admin=False,
    )
    viewer_role = Role.objects.get(tenant=tenant, name="Viewer")
    u.roles.add(viewer_role)
    return u


@pytest.fixture
def pending_invitation(db, tenant, admin_user):
    """Create a pending invitation."""
    return UserInvitation.create_invitation(
        tenant=tenant,
        email="newuser@example.com",
        created_by=admin_user,
    )


class TestUserInvitationFlow:
    """Test user invitation creation, validation, and acceptance."""

    def test_create_invitation_as_admin(self, admin_user, tenant):
        """Test that admins can create invitations."""
        mutation = """
            mutation CreateInvitation($email: String!) {
                createInvitation(email: $email) {
                    success
                    error
                    invitation {
                        email
                        status
                    }
                    inviteUrl
                }
            }
        """

        result = run_graphql(
            mutation,
            {"email": "newuser@example.com"},
            make_context(admin_user),
        )

        assert result.errors is None
        data = result.data["createInvitation"]
        assert data["success"] is True
        assert data["invitation"]["email"] == "newuser@example.com"
        assert data["invitation"]["status"] == "pending"
        assert data["inviteUrl"] is not None
        assert "/invite/" in data["inviteUrl"]

    def test_create_invitation_as_non_admin_fails(self, regular_user):
        """Test that non-admins cannot create invitations."""
        mutation = """
            mutation CreateInvitation($email: String!) {
                createInvitation(email: $email) {
                    success
                    error
                }
            }
        """

        result = run_graphql(
            mutation,
            {"email": "newuser@example.com"},
            make_context(regular_user),
        )

        assert result.errors is None
        data = result.data["createInvitation"]
        assert data["success"] is False
        assert "permission" in data["error"].lower() or "denied" in data["error"].lower()

    def test_validate_invitation_valid_token(self, pending_invitation):
        """Test validating a valid invitation token."""
        query = """
            query ValidateInvitation($token: String!) {
                validateInvitation(token: $token) {
                    valid
                    email
                    error
                }
            }
        """

        result = run_graphql(
            query,
            {"token": pending_invitation.token},
            make_context(None),
        )

        assert result.errors is None
        data = result.data["validateInvitation"]
        assert data["valid"] is True
        assert data["email"] == "newuser@example.com"
        assert data["error"] is None

    def test_validate_invitation_invalid_token(self, db):
        """Test validating an invalid invitation token."""
        query = """
            query ValidateInvitation($token: String!) {
                validateInvitation(token: $token) {
                    valid
                    email
                    error
                }
            }
        """

        result = run_graphql(
            query,
            {"token": "invalid-token"},
            make_context(None),
        )

        assert result.errors is None
        data = result.data["validateInvitation"]
        assert data["valid"] is False
        assert data["error"] is not None

    def test_validate_invitation_expired_token(self, db, tenant, admin_user):
        """Test validating an expired invitation token."""
        invitation = UserInvitation.create_invitation(
            tenant=tenant,
            email="expired@example.com",
            created_by=admin_user,
        )
        # Manually expire the invitation
        invitation.expires_at = timezone.now() - timedelta(days=1)
        invitation.save()

        query = """
            query ValidateInvitation($token: String!) {
                validateInvitation(token: $token) {
                    valid
                    email
                    error
                }
            }
        """

        result = run_graphql(
            query,
            {"token": invitation.token},
            make_context(None),
        )

        assert result.errors is None
        data = result.data["validateInvitation"]
        assert data["valid"] is False
        assert "expired" in data["error"].lower()

    def test_accept_invitation_creates_user(self, pending_invitation, tenant):
        """Test that accepting an invitation creates a new user."""
        mutation = """
            mutation AcceptInvitation($token: String!, $firstName: String!, $lastName: String!, $password: String!) {
                acceptInvitation(token: $token, firstName: $firstName, lastName: $lastName, password: $password) {
                    success
                    error
                }
            }
        """

        result = run_graphql(
            mutation,
            {
                "token": pending_invitation.token,
                "firstName": "New",
                "lastName": "User",
                "password": "securepassword123",
            },
            make_context(None),
        )

        assert result.errors is None
        data = result.data["acceptInvitation"]
        assert data["success"] is True

        # Verify user was created
        user = User.objects.get(email="newuser@example.com")
        assert user.first_name == "New"
        assert user.last_name == "User"
        assert user.tenant == tenant
        assert user.check_password("securepassword123")

        # Verify invitation is marked as used
        pending_invitation.refresh_from_db()
        assert pending_invitation.status == UserInvitation.Status.USED

    def test_accept_invitation_invalid_token_fails(self, db):
        """Test that accepting with invalid token fails."""
        mutation = """
            mutation AcceptInvitation($token: String!, $firstName: String!, $lastName: String!, $password: String!) {
                acceptInvitation(token: $token, firstName: $firstName, lastName: $lastName, password: $password) {
                    success
                    error
                }
            }
        """

        result = run_graphql(
            mutation,
            {
                "token": "invalid-token",
                "firstName": "New",
                "lastName": "User",
                "password": "securepassword123",
            },
            make_context(None),
        )

        assert result.errors is None
        data = result.data["acceptInvitation"]
        assert data["success"] is False
        assert data["error"] is not None

    def test_revoke_invitation(self, admin_user, pending_invitation):
        """Test that admins can revoke pending invitations."""
        mutation = """
            mutation RevokeInvitation($invitationId: ID!) {
                revokeInvitation(invitationId: $invitationId) {
                    success
                    error
                }
            }
        """

        result = run_graphql(
            mutation,
            {"invitationId": str(pending_invitation.id)},
            make_context(admin_user),
        )

        assert result.errors is None
        data = result.data["revokeInvitation"]
        assert data["success"] is True

        pending_invitation.refresh_from_db()
        assert pending_invitation.status == UserInvitation.Status.REVOKED

    def test_query_pending_invitations(self, admin_user, pending_invitation):
        """Test querying pending invitations."""
        query = """
            query PendingInvitations {
                pendingInvitations {
                    email
                    status
                    expiresAt
                }
            }
        """

        result = run_graphql(query, {}, make_context(admin_user))

        assert result.errors is None
        invitations = result.data["pendingInvitations"]
        assert len(invitations) >= 1
        emails = [inv["email"] for inv in invitations]
        assert "newuser@example.com" in emails


class TestPasswordChange:
    """Test password change functionality."""

    def test_change_password_success(self, regular_user):
        """Test changing password with correct current password."""
        mutation = """
            mutation ChangePassword($currentPassword: String!, $newPassword: String!) {
                changePassword(currentPassword: $currentPassword, newPassword: $newPassword) {
                    success
                    error
                }
            }
        """

        result = run_graphql(
            mutation,
            {
                "currentPassword": "user123",
                "newPassword": "newpassword123",
            },
            make_context(regular_user),
        )

        assert result.errors is None
        data = result.data["changePassword"]
        assert data["success"] is True

        regular_user.refresh_from_db()
        assert regular_user.check_password("newpassword123")

    def test_change_password_wrong_current_password(self, regular_user):
        """Test changing password with incorrect current password."""
        mutation = """
            mutation ChangePassword($currentPassword: String!, $newPassword: String!) {
                changePassword(currentPassword: $currentPassword, newPassword: $newPassword) {
                    success
                    error
                }
            }
        """

        result = run_graphql(
            mutation,
            {
                "currentPassword": "wrongpassword",
                "newPassword": "newpassword123",
            },
            make_context(regular_user),
        )

        assert result.errors is None
        data = result.data["changePassword"]
        assert data["success"] is False
        assert "incorrect" in data["error"].lower() or "invalid" in data["error"].lower()

    def test_change_password_unauthenticated_fails(self):
        """Test that unauthenticated users cannot change passwords."""
        mutation = """
            mutation ChangePassword($currentPassword: String!, $newPassword: String!) {
                changePassword(currentPassword: $currentPassword, newPassword: $newPassword) {
                    success
                    error
                }
            }
        """

        result = run_graphql(
            mutation,
            {
                "currentPassword": "user123",
                "newPassword": "newpassword123",
            },
            make_context(None),
        )

        # Should have an authentication error (either at GraphQL level or via get_current_user)
        assert result.errors is not None or result.data["changePassword"]["success"] is False


class TestPasswordReset:
    """Test password reset functionality."""

    def test_create_password_reset_as_admin(self, admin_user, regular_user):
        """Test that admins can create password reset tokens for other users."""
        mutation = """
            mutation CreatePasswordReset($userId: ID!) {
                createPasswordReset(userId: $userId) {
                    success
                    error
                    resetUrl
                }
            }
        """

        result = run_graphql(
            mutation,
            {"userId": str(regular_user.id)},
            make_context(admin_user),
        )

        assert result.errors is None
        data = result.data["createPasswordReset"]
        assert data["success"] is True
        assert data["resetUrl"] is not None
        assert "reset-password" in data["resetUrl"]

    def test_create_password_reset_as_non_admin_fails(self, regular_user, admin_user):
        """Test that non-admins cannot create password reset tokens."""
        mutation = """
            mutation CreatePasswordReset($userId: ID!) {
                createPasswordReset(userId: $userId) {
                    success
                    error
                }
            }
        """

        result = run_graphql(
            mutation,
            {"userId": str(admin_user.id)},
            make_context(regular_user),
        )

        assert result.errors is None
        data = result.data["createPasswordReset"]
        assert data["success"] is False

    def test_validate_password_reset_valid_token(self, db, regular_user):
        """Test validating a valid password reset token."""
        reset_token = PasswordResetToken.create_token(regular_user)

        query = """
            query ValidatePasswordReset($token: String!) {
                validatePasswordReset(token: $token) {
                    valid
                    email
                    error
                }
            }
        """

        result = run_graphql(
            query,
            {"token": reset_token.token},
            make_context(None),
        )

        assert result.errors is None
        data = result.data["validatePasswordReset"]
        assert data["valid"] is True
        assert data["email"] == regular_user.email

    def test_validate_password_reset_expired_token(self, db, regular_user):
        """Test validating an expired password reset token."""
        reset_token = PasswordResetToken.create_token(regular_user)
        reset_token.expires_at = timezone.now() - timedelta(hours=1)
        reset_token.save()

        query = """
            query ValidatePasswordReset($token: String!) {
                validatePasswordReset(token: $token) {
                    valid
                    error
                }
            }
        """

        result = run_graphql(
            query,
            {"token": reset_token.token},
            make_context(None),
        )

        assert result.errors is None
        data = result.data["validatePasswordReset"]
        assert data["valid"] is False
        assert "expired" in data["error"].lower()

    def test_reset_password_success(self, db, regular_user):
        """Test resetting password with valid token."""
        reset_token = PasswordResetToken.create_token(regular_user)

        mutation = """
            mutation ResetPassword($token: String!, $newPassword: String!) {
                resetPassword(token: $token, newPassword: $newPassword) {
                    success
                    error
                }
            }
        """

        result = run_graphql(
            mutation,
            {
                "token": reset_token.token,
                "newPassword": "brandnewpassword123",
            },
            make_context(None),
        )

        assert result.errors is None
        data = result.data["resetPassword"]
        assert data["success"] is True

        regular_user.refresh_from_db()
        assert regular_user.check_password("brandnewpassword123")

        # Token should be marked as used
        reset_token.refresh_from_db()
        assert reset_token.used is True

    def test_reset_password_invalid_token(self, db):
        """Test resetting password with invalid token fails."""
        mutation = """
            mutation ResetPassword($token: String!, $newPassword: String!) {
                resetPassword(token: $token, newPassword: $newPassword) {
                    success
                    error
                }
            }
        """

        result = run_graphql(
            mutation,
            {
                "token": "invalid-token",
                "newPassword": "brandnewpassword123",
            },
            make_context(None),
        )

        assert result.errors is None
        data = result.data["resetPassword"]
        assert data["success"] is False


class TestUserDeactivation:
    """Test user deactivation and its effect on login."""

    def test_deactivate_user_as_admin(self, admin_user, regular_user):
        """Test that admins can deactivate users."""
        mutation = """
            mutation DeactivateUser($userId: ID!) {
                deactivateUser(userId: $userId) {
                    success
                    error
                }
            }
        """

        result = run_graphql(
            mutation,
            {"userId": str(regular_user.id)},
            make_context(admin_user),
        )

        assert result.errors is None
        data = result.data["deactivateUser"]
        assert data["success"] is True

        regular_user.refresh_from_db()
        assert regular_user.is_active is False

    def test_deactivate_self_fails(self, admin_user):
        """Test that users cannot deactivate themselves."""
        mutation = """
            mutation DeactivateUser($userId: ID!) {
                deactivateUser(userId: $userId) {
                    success
                    error
                }
            }
        """

        result = run_graphql(
            mutation,
            {"userId": str(admin_user.id)},
            make_context(admin_user),
        )

        assert result.errors is None
        data = result.data["deactivateUser"]
        assert data["success"] is False
        assert "yourself" in data["error"].lower() or "self" in data["error"].lower()

    def test_deactivate_user_as_non_admin_fails(self, regular_user, admin_user):
        """Test that non-admins cannot deactivate users."""
        mutation = """
            mutation DeactivateUser($userId: ID!) {
                deactivateUser(userId: $userId) {
                    success
                    error
                }
            }
        """

        result = run_graphql(
            mutation,
            {"userId": str(admin_user.id)},
            make_context(regular_user),
        )

        assert result.errors is None
        data = result.data["deactivateUser"]
        assert data["success"] is False

    def test_reactivate_user_as_admin(self, admin_user, regular_user):
        """Test that admins can reactivate deactivated users."""
        # First deactivate the user
        regular_user.is_active = False
        regular_user.save()

        mutation = """
            mutation ReactivateUser($userId: ID!) {
                reactivateUser(userId: $userId) {
                    success
                    error
                }
            }
        """

        result = run_graphql(
            mutation,
            {"userId": str(regular_user.id)},
            make_context(admin_user),
        )

        assert result.errors is None
        data = result.data["reactivateUser"]
        assert data["success"] is True

        regular_user.refresh_from_db()
        assert regular_user.is_active is True

    def test_inactive_user_login_blocked(self, db, tenant):
        """Test that inactive users cannot log in."""
        # Create and deactivate a user
        inactive_user = User.objects.create_user(
            email="inactive@example.com",
            password="password123",
            tenant=tenant,
            is_active=False,
        )

        mutation = """
            mutation Login($email: String!, $password: String!) {
                login(email: $email, password: $password) {
                    ... on AuthPayload {
                        accessToken
                        userId
                    }
                    ... on AuthError {
                        message
                    }
                }
            }
        """

        result = run_graphql(
            mutation,
            {
                "email": "inactive@example.com",
                "password": "password123",
            },
            make_context(None),
        )

        assert result.errors is None
        data = result.data["login"]
        # Should get an AuthError, not an AuthPayload
        assert "message" in data
        assert "accessToken" not in data

    def test_active_user_login_succeeds(self, regular_user):
        """Test that active users can log in."""
        mutation = """
            mutation Login($email: String!, $password: String!) {
                login(email: $email, password: $password) {
                    ... on AuthPayload {
                        accessToken
                        userId
                    }
                    ... on AuthError {
                        message
                    }
                }
            }
        """

        result = run_graphql(
            mutation,
            {
                "email": "user@example.com",
                "password": "user123",
            },
            make_context(None),
        )

        assert result.errors is None
        data = result.data["login"]
        # Should get an AuthPayload, not an AuthError
        assert "accessToken" in data
        assert "message" not in data


class TestUsersQuery:
    """Test querying users list."""

    def test_query_users_as_admin(self, admin_user, regular_user):
        """Test that admins can query the users list."""
        query = """
            query Users {
                users {
                    id
                    email
                    isAdmin
                    isActive
                    firstName
                    lastName
                }
            }
        """

        result = run_graphql(query, {}, make_context(admin_user))

        assert result.errors is None
        users = result.data["users"]
        assert len(users) >= 2
        emails = [u["email"] for u in users]
        assert "admin@example.com" in emails
        assert "user@example.com" in emails

    def test_query_users_as_non_admin_fails(self, regular_user):
        """Test that non-admins cannot query the users list."""
        query = """
            query Users {
                users {
                    id
                    email
                }
            }
        """

        result = run_graphql(query, {}, make_context(regular_user))

        # Should fail or return empty/error
        if result.errors:
            assert True  # Permission denied at GraphQL level
        else:
            assert result.data["users"] is None or len(result.data["users"]) == 0


class TestSuperAdmin:
    """Test super admin functionality."""

    def test_super_admin_property(self, db, tenant):
        """Test that admin@test.local is recognized as super admin."""
        super_admin = User.objects.create_user(
            email="admin@test.local",
            password="admin123",
            tenant=tenant,
        )
        regular = User.objects.create_user(
            email="other@test.local",
            password="other123",
            tenant=tenant,
        )

        assert super_admin.is_super_admin is True
        assert regular.is_super_admin is False


class TestProfileUpdate:
    """Test user profile update functionality."""

    def test_update_profile_name_success(self, regular_user):
        """Test updating first and last name."""
        mutation = """
            mutation UpdateProfile($firstName: String, $lastName: String) {
                updateProfile(firstName: $firstName, lastName: $lastName) {
                    success
                    error
                    user {
                        firstName
                        lastName
                    }
                }
            }
        """

        result = run_graphql(
            mutation,
            {
                "firstName": "Updated",
                "lastName": "Name",
            },
            make_context(regular_user),
        )

        assert result.errors is None
        data = result.data["updateProfile"]
        assert data["success"] is True
        assert data["user"]["firstName"] == "Updated"
        assert data["user"]["lastName"] == "Name"

        regular_user.refresh_from_db()
        assert regular_user.first_name == "Updated"
        assert regular_user.last_name == "Name"

    def test_update_profile_email_success(self, regular_user):
        """Test updating email address."""
        mutation = """
            mutation UpdateProfile($email: String) {
                updateProfile(email: $email) {
                    success
                    error
                    user {
                        email
                    }
                }
            }
        """

        result = run_graphql(
            mutation,
            {"email": "newemail@example.com"},
            make_context(regular_user),
        )

        assert result.errors is None
        data = result.data["updateProfile"]
        assert data["success"] is True
        assert data["user"]["email"] == "newemail@example.com"

        regular_user.refresh_from_db()
        assert regular_user.email == "newemail@example.com"

    def test_update_profile_email_already_in_use(self, admin_user, regular_user):
        """Test that email uniqueness is enforced."""
        mutation = """
            mutation UpdateProfile($email: String) {
                updateProfile(email: $email) {
                    success
                    error
                }
            }
        """

        # Try to update regular_user's email to admin_user's email
        result = run_graphql(
            mutation,
            {"email": admin_user.email},
            make_context(regular_user),
        )

        assert result.errors is None
        data = result.data["updateProfile"]
        assert data["success"] is False
        assert "already in use" in data["error"].lower()

    def test_update_profile_invalid_email_format(self, regular_user):
        """Test that invalid email format is rejected."""
        mutation = """
            mutation UpdateProfile($email: String) {
                updateProfile(email: $email) {
                    success
                    error
                }
            }
        """

        result = run_graphql(
            mutation,
            {"email": "not-an-email"},
            make_context(regular_user),
        )

        assert result.errors is None
        data = result.data["updateProfile"]
        assert data["success"] is False
        assert "invalid" in data["error"].lower()
