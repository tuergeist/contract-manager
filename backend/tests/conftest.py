"""Pytest configuration and fixtures."""
import pytest
from apps.tenants.models import Tenant, User


@pytest.fixture
def tenant(db):
    """Create a test tenant."""
    return Tenant.objects.create(
        name="Test Company",
        currency="EUR",
    )


@pytest.fixture
def user(db, tenant):
    """Create a test user."""
    return User.objects.create_user(
        email="test@example.com",
        password="testpass123",
        tenant=tenant,
    )
