"""Tests for RBAC: roles, permissions, role CRUD, and last-admin protection."""
import pytest
from unittest.mock import Mock

from config.schema import schema
from apps.tenants.models import Role, Tenant, User, UserInvitation
from apps.core.context import Context
from apps.core.permissions import (
    ADMIN_PROTECTED_PERMISSIONS,
    ALL_PERMISSIONS,
    DEFAULT_ROLES,
    PERMISSION_REGISTRY,
    normalize_permissions,
)


def run_graphql(query, variables, context):
    """Helper to run GraphQL queries synchronously."""
    return schema.execute_sync(query, variable_values=variables, context_value=context)


def make_context(user=None):
    """Create a proper Context object for GraphQL testing."""
    request = Mock()
    return Context(request=request, user=user)


@pytest.fixture
def tenant(db):
    """Create a test tenant (signal creates default roles)."""
    return Tenant.objects.create(name="Test Company", currency="EUR")


@pytest.fixture
def admin_user(db, tenant):
    u = User.objects.create_user(
        email="admin@example.com", password="admin123", tenant=tenant, is_admin=True
    )
    admin_role = Role.objects.get(tenant=tenant, name="Admin")
    u.roles.add(admin_role)
    return u


@pytest.fixture
def manager_user(db, tenant):
    u = User.objects.create_user(
        email="manager@example.com", password="mgr123", tenant=tenant
    )
    manager_role = Role.objects.get(tenant=tenant, name="Manager")
    u.roles.add(manager_role)
    return u


@pytest.fixture
def viewer_user(db, tenant):
    u = User.objects.create_user(
        email="viewer@example.com", password="view123", tenant=tenant
    )
    viewer_role = Role.objects.get(tenant=tenant, name="Viewer")
    u.roles.add(viewer_role)
    return u


@pytest.fixture
def no_role_user(db, tenant):
    return User.objects.create_user(
        email="norole@example.com", password="norole123", tenant=tenant
    )


class TestNormalizePermissions:
    """Test normalize_permissions converts old formats and strips invalid keys."""

    def test_valid_flat_keys_pass_through(self):
        raw = {"contracts.read": True, "todos.write": True}
        assert normalize_permissions(raw) == {"contracts.read": True, "todos.write": True}

    def test_old_format_list_converted(self):
        raw = {"products": ["read", "write"], "customers": ["read"]}
        assert normalize_permissions(raw) == {
            "products.read": True,
            "products.write": True,
            "customers.read": True,
        }

    def test_mixed_format_normalized(self):
        raw = {
            "products": ["read"],
            "contracts": ["read", "write"],
            "todos.read": True,
            "todos.write": True,
        }
        assert normalize_permissions(raw) == {
            "products.read": True,
            "contracts.read": True,
            "contracts.write": True,
            "todos.read": True,
            "todos.write": True,
        }

    def test_bare_resource_true_stripped(self):
        raw = {"products": True, "contracts.read": True}
        assert normalize_permissions(raw) == {"contracts.read": True}

    def test_false_values_stripped(self):
        raw = {"contracts.read": True, "contracts.write": False}
        assert normalize_permissions(raw) == {"contracts.read": True}

    def test_unknown_keys_stripped(self):
        raw = {"nonexistent.read": True, "contracts.read": True}
        assert normalize_permissions(raw) == {"contracts.read": True}

    def test_empty_dict(self):
        assert normalize_permissions({}) == {}


class TestDefaultRolesCreation:
    """Test 9.3: data migration / signal creates correct default roles."""

    def test_tenant_creation_seeds_three_roles(self, tenant):
        roles = Role.objects.filter(tenant=tenant)
        assert roles.count() == 3
        names = set(roles.values_list("name", flat=True))
        assert names == {"Admin", "Manager", "Viewer"}

    def test_default_roles_are_system(self, tenant):
        for role in Role.objects.filter(tenant=tenant):
            assert role.is_system is True

    def test_admin_role_has_all_permissions(self, tenant):
        admin = Role.objects.get(tenant=tenant, name="Admin")
        for perm in ALL_PERMISSIONS:
            assert admin.permissions.get(perm) is True, f"Admin missing {perm}"

    def test_manager_role_excludes_users_and_settings(self, tenant):
        mgr = Role.objects.get(tenant=tenant, name="Manager")
        for perm_key, granted in mgr.permissions.items():
            if perm_key.startswith("users.") or perm_key.startswith("settings."):
                assert not granted, f"Manager should not have {perm_key}"
            else:
                assert granted is True, f"Manager missing {perm_key}"

    def test_viewer_role_read_only_plus_todos(self, tenant):
        viewer = Role.objects.get(tenant=tenant, name="Viewer")
        expected = DEFAULT_ROLES["Viewer"]
        for perm_key, val in expected.items():
            assert viewer.permissions.get(perm_key) == val


class TestPermissionEnforcement:
    """Test 9.1: permission enforcement (user with/without permission, super-admin bypass)."""

    def test_admin_can_read_users(self, admin_user):
        query = "{ users { id email } }"
        result = run_graphql(query, {}, make_context(admin_user))
        assert result.errors is None

    def test_viewer_cannot_read_users(self, viewer_user):
        query = "{ users { id email } }"
        result = run_graphql(query, {}, make_context(viewer_user))
        assert result.errors is not None
        assert "Permission denied" in str(result.errors[0])

    def test_no_role_user_cannot_read_contracts(self, no_role_user):
        query = "{ contracts { totalCount } }"
        result = run_graphql(query, {}, make_context(no_role_user))
        assert result.errors is not None
        assert "Permission denied" in str(result.errors[0])

    def test_viewer_can_read_contracts(self, viewer_user):
        query = "{ contracts { totalCount } }"
        result = run_graphql(query, {}, make_context(viewer_user))
        assert result.errors is None

    def test_manager_can_read_contracts(self, manager_user):
        query = "{ contracts { totalCount } }"
        result = run_graphql(query, {}, make_context(manager_user))
        assert result.errors is None

    def test_viewer_cannot_create_invitation(self, viewer_user):
        mutation = """
            mutation { createInvitation(email: "x@x.com") { success error } }
        """
        result = run_graphql(mutation, {}, make_context(viewer_user))
        assert result.errors is None
        data = result.data["createInvitation"]
        assert data["success"] is False
        assert "Permission denied" in data["error"]

    def test_super_admin_bypasses_permissions(self, tenant):
        """The super-admin (admin@test.local) should always have all permissions."""
        sa = User.objects.create_user(
            email="admin@test.local", password="admin123", tenant=tenant
        )
        # Don't assign any roles — super-admin bypass should work
        assert sa.has_perm_check("users", "write") is True
        assert sa.has_perm_check("settings", "read") is True
        assert sa.has_perm_check("contracts", "delete") is True

    def test_effective_permissions_union_of_roles(self, tenant):
        """User with multiple roles gets union of permissions."""
        u = User.objects.create_user(
            email="multi@example.com", password="multi123", tenant=tenant
        )
        viewer = Role.objects.get(tenant=tenant, name="Viewer")
        manager = Role.objects.get(tenant=tenant, name="Manager")
        u.roles.add(viewer, manager)
        # Manager has contracts.write, Viewer has contracts.read
        assert u.has_perm_check("contracts", "write") is True
        assert u.has_perm_check("contracts", "read") is True
        # Manager doesn't have users.write, Viewer doesn't either
        assert u.has_perm_check("users", "write") is False


class TestRoleCRUD:
    """Test 9.2: role CRUD (create, update permissions, delete, system role protection)."""

    def test_create_role(self, admin_user):
        mutation = """
            mutation CreateRole($name: String!, $permissions: JSON) {
                createRole(name: $name, permissions: $permissions) {
                    success
                    error
                    role { id name isSystem permissions userCount }
                }
            }
        """
        result = run_graphql(
            mutation,
            {"name": "Accountant", "permissions": {"invoices.read": True, "invoices.write": True}},
            make_context(admin_user),
        )
        assert result.errors is None
        data = result.data["createRole"]
        assert data["success"] is True
        assert data["role"]["name"] == "Accountant"
        assert data["role"]["isSystem"] is False

    def test_create_role_duplicate_name_fails(self, admin_user):
        mutation = """
            mutation CreateRole($name: String!) {
                createRole(name: $name) { success error }
            }
        """
        result = run_graphql(mutation, {"name": "Admin"}, make_context(admin_user))
        data = result.data["createRole"]
        assert data["success"] is False
        assert "already exists" in data["error"]

    def test_update_role_permissions(self, admin_user, tenant):
        role = Role.objects.get(tenant=tenant, name="Viewer")
        mutation = """
            mutation UpdateRolePerms($roleId: ID!, $permissions: JSON!) {
                updateRolePermissions(roleId: $roleId, permissions: $permissions) {
                    success error role { permissions }
                }
            }
        """
        new_perms = {"contracts.read": True, "customers.read": True}
        result = run_graphql(
            mutation,
            {"roleId": str(role.id), "permissions": new_perms},
            make_context(admin_user),
        )
        assert result.errors is None
        data = result.data["updateRolePermissions"]
        assert data["success"] is True

    def test_cannot_remove_protected_perms_from_admin(self, admin_user, tenant):
        admin_role = Role.objects.get(tenant=tenant, name="Admin")
        mutation = """
            mutation UpdateRolePerms($roleId: ID!, $permissions: JSON!) {
                updateRolePermissions(roleId: $roleId, permissions: $permissions) {
                    success error
                }
            }
        """
        # Try to remove users.write (protected)
        perms = {p: True for p in ALL_PERMISSIONS}
        perms["users.write"] = False
        result = run_graphql(
            mutation,
            {"roleId": str(admin_role.id), "permissions": perms},
            make_context(admin_user),
        )
        data = result.data["updateRolePermissions"]
        assert data["success"] is False
        assert "protected" in data["error"].lower() or "Cannot remove" in data["error"]

    def test_delete_custom_role(self, admin_user, tenant):
        custom = Role.objects.create(
            tenant=tenant, name="Custom", permissions={}, is_system=False
        )
        mutation = """
            mutation DeleteRole($roleId: ID!) {
                deleteRole(roleId: $roleId) { success error }
            }
        """
        result = run_graphql(mutation, {"roleId": str(custom.id)}, make_context(admin_user))
        data = result.data["deleteRole"]
        assert data["success"] is True
        assert not Role.objects.filter(id=custom.id).exists()

    def test_cannot_delete_system_role(self, admin_user, tenant):
        admin_role = Role.objects.get(tenant=tenant, name="Admin")
        mutation = """
            mutation DeleteRole($roleId: ID!) {
                deleteRole(roleId: $roleId) { success error }
            }
        """
        result = run_graphql(mutation, {"roleId": str(admin_role.id)}, make_context(admin_user))
        data = result.data["deleteRole"]
        assert data["success"] is False
        assert "system" in data["error"].lower()

    def test_cannot_delete_role_with_users(self, admin_user, tenant):
        custom = Role.objects.create(
            tenant=tenant, name="CustomWithUser", permissions={}, is_system=False
        )
        # Assign a user to this custom role
        u = User.objects.create_user(
            email="customrole@example.com", password="pass123", tenant=tenant
        )
        u.roles.add(custom)

        mutation = """
            mutation DeleteRole($roleId: ID!) {
                deleteRole(roleId: $roleId) { success error }
            }
        """
        result = run_graphql(mutation, {"roleId": str(custom.id)}, make_context(admin_user))
        data = result.data["deleteRole"]
        assert data["success"] is False
        assert "assigned users" in data["error"].lower()

    def test_create_role_strips_invalid_permission_keys(self, admin_user):
        """Bare resource names like 'products': True are silently stripped."""
        mutation = """
            mutation CreateRole($name: String!, $permissions: JSON) {
                createRole(name: $name, permissions: $permissions) {
                    success error role { permissions }
                }
            }
        """
        result = run_graphql(
            mutation,
            {"name": "StrippedRole", "permissions": {"products": True, "contracts.read": True}},
            make_context(admin_user),
        )
        data = result.data["createRole"]
        assert data["success"] is True
        perms = data["role"]["permissions"]
        assert "products" not in perms
        assert perms.get("contracts.read") is True

    def test_update_role_converts_old_format_permissions(self, admin_user, tenant):
        """Old-format {"customers": ["read"]} is auto-converted to {"customers.read": true}."""
        role = Role.objects.get(tenant=tenant, name="Viewer")
        mutation = """
            mutation UpdateRolePerms($roleId: ID!, $permissions: JSON!) {
                updateRolePermissions(roleId: $roleId, permissions: $permissions) {
                    success error role { permissions }
                }
            }
        """
        result = run_graphql(
            mutation,
            {"roleId": str(role.id), "permissions": {"customers": ["read"], "contracts.read": True}},
            make_context(admin_user),
        )
        data = result.data["updateRolePermissions"]
        assert data["success"] is True
        perms = data["role"]["permissions"]
        assert perms.get("customers.read") is True
        assert perms.get("contracts.read") is True
        assert "customers" not in perms

    def test_update_role_mixed_old_and_new_format(self, admin_user, tenant):
        """Mixed old/new format permissions are normalized correctly."""
        role = Role.objects.create(
            tenant=tenant,
            name="MixedRole",
            permissions={},
            is_system=False,
        )
        mutation = """
            mutation UpdateRolePerms($roleId: ID!, $permissions: JSON!) {
                updateRolePermissions(roleId: $roleId, permissions: $permissions) {
                    success error role { permissions }
                }
            }
        """
        mixed_perms = {
            "products": ["read"],
            "contracts": ["read", "write"],
            "customers": ["read"],
            "todos.read": True,
            "todos.write": True,
        }
        result = run_graphql(
            mutation,
            {"roleId": str(role.id), "permissions": mixed_perms},
            make_context(admin_user),
        )
        data = result.data["updateRolePermissions"]
        assert data["success"] is True
        perms = data["role"]["permissions"]
        assert perms.get("products.read") is True
        assert perms.get("contracts.read") is True
        assert perms.get("contracts.write") is True
        assert perms.get("customers.read") is True
        assert perms.get("todos.read") is True
        assert perms.get("todos.write") is True
        assert "products" not in perms
        assert "contracts" not in perms
        assert "customers" not in perms


class TestInvitationRoleAssignment:
    """Test 9.4: invitation with role assignment."""

    def test_invitation_stores_role_ids(self, admin_user, tenant):
        manager_role = Role.objects.get(tenant=tenant, name="Manager")
        mutation = """
            mutation CreateInvitation($email: String!, $roleIds: [ID!]) {
                createInvitation(email: $email, roleIds: $roleIds) {
                    success error inviteUrl
                }
            }
        """
        result = run_graphql(
            mutation,
            {"email": "new@example.com", "roleIds": [str(manager_role.id)]},
            make_context(admin_user),
        )
        data = result.data["createInvitation"]
        assert data["success"] is True

        invite = UserInvitation.objects.get(email="new@example.com")
        assert invite.role_ids == [manager_role.id]

    def test_invitation_defaults_to_manager(self, admin_user, tenant):
        mutation = """
            mutation CreateInvitation($email: String!) {
                createInvitation(email: $email) { success }
            }
        """
        result = run_graphql(mutation, {"email": "default@example.com"}, make_context(admin_user))
        assert result.data["createInvitation"]["success"] is True

        invite = UserInvitation.objects.get(email="default@example.com")
        manager_role = Role.objects.get(tenant=tenant, name="Manager")
        assert invite.role_ids == [manager_role.id]

    def test_accept_invitation_assigns_roles(self, admin_user, tenant):
        viewer_role = Role.objects.get(tenant=tenant, name="Viewer")
        invite = UserInvitation.create_invitation(
            tenant=tenant, email="accepted@example.com", created_by=admin_user
        )
        invite.role_ids = [viewer_role.id]
        invite.save()

        mutation = """
            mutation AcceptInvitation($token: String!, $password: String!) {
                acceptInvitation(token: $token, password: $password) { success error }
            }
        """
        result = run_graphql(mutation, {"token": invite.token, "password": "securepass1"}, make_context())
        assert result.data["acceptInvitation"]["success"] is True

        new_user = User.objects.get(email="accepted@example.com")
        assert list(new_user.roles.values_list("name", flat=True)) == ["Viewer"]


class TestLastAdminProtection:
    """Test 9.5: last-admin protection (cannot remove Admin role from last admin)."""

    def test_cannot_remove_admin_from_last_admin(self, admin_user, tenant):
        viewer_role = Role.objects.get(tenant=tenant, name="Viewer")
        mutation = """
            mutation AssignUserRoles($userId: ID!, $roleIds: [ID!]!) {
                assignUserRoles(userId: $userId, roleIds: $roleIds) {
                    success error
                }
            }
        """
        # Try to assign only Viewer to the sole admin
        result = run_graphql(
            mutation,
            {"userId": str(admin_user.id), "roleIds": [str(viewer_role.id)]},
            make_context(admin_user),
        )
        data = result.data["assignUserRoles"]
        assert data["success"] is False
        assert "last admin" in data["error"].lower()

    def test_can_remove_admin_when_other_admins_exist(self, admin_user, tenant):
        # Create another admin
        admin2 = User.objects.create_user(
            email="admin2@example.com", password="admin2", tenant=tenant, is_active=True
        )
        admin_role = Role.objects.get(tenant=tenant, name="Admin")
        admin2.roles.add(admin_role)

        viewer_role = Role.objects.get(tenant=tenant, name="Viewer")
        mutation = """
            mutation AssignUserRoles($userId: ID!, $roleIds: [ID!]!) {
                assignUserRoles(userId: $userId, roleIds: $roleIds) {
                    success error
                }
            }
        """
        # Now removing Admin from admin_user should succeed since admin2 exists
        result = run_graphql(
            mutation,
            {"userId": str(admin_user.id), "roleIds": [str(viewer_role.id)]},
            make_context(admin_user),
        )
        data = result.data["assignUserRoles"]
        assert data["success"] is True

    def test_assign_roles_works_normally(self, admin_user, tenant, manager_user):
        admin_role = Role.objects.get(tenant=tenant, name="Admin")
        manager_role = Role.objects.get(tenant=tenant, name="Manager")
        mutation = """
            mutation AssignUserRoles($userId: ID!, $roleIds: [ID!]!) {
                assignUserRoles(userId: $userId, roleIds: $roleIds) {
                    success error
                }
            }
        """
        # Give manager both Manager + Admin roles
        result = run_graphql(
            mutation,
            {
                "userId": str(manager_user.id),
                "roleIds": [str(admin_role.id), str(manager_role.id)],
            },
            make_context(admin_user),
        )
        data = result.data["assignUserRoles"]
        assert data["success"] is True
        manager_user.refresh_from_db()
        role_names = set(manager_user.roles.values_list("name", flat=True))
        assert role_names == {"Admin", "Manager"}


class TestMeQuery:
    """Test that the me query returns roles and permissions."""

    def test_me_returns_roles_and_permissions(self, admin_user):
        query = """
            query { me { id email roles permissions } }
        """
        result = run_graphql(query, {}, make_context(admin_user))
        assert result.errors is None
        data = result.data["me"]
        assert "Admin" in data["roles"]
        assert "contracts.read" in data["permissions"]
        assert "users.write" in data["permissions"]

    def test_me_viewer_has_limited_permissions(self, viewer_user):
        query = """
            query { me { roles permissions } }
        """
        result = run_graphql(query, {}, make_context(viewer_user))
        data = result.data["me"]
        assert "Viewer" in data["roles"]
        assert "contracts.read" in data["permissions"]
        assert "users.write" not in data["permissions"]
        assert "settings.write" not in data["permissions"]
