"""Pytest configuration and fixtures."""
import pytest
from apps.tenants.models import Role, Tenant, User


@pytest.fixture
def tenant(db):
    """Create a test tenant.

    The post_save signal creates default roles (Admin, Manager, Viewer).
    """
    return Tenant.objects.create(
        name="Test Company",
        currency="EUR",
    )


@pytest.fixture
def user(db, tenant):
    """Create a test user with Admin role (full permissions for tests)."""
    u = User.objects.create_user(
        email="test@example.com",
        password="testpass123",
        tenant=tenant,
    )
    admin_role = Role.objects.get(tenant=tenant, name="Admin")
    u.roles.add(admin_role)
    return u
