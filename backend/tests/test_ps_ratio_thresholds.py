"""Tests for ps_ratio_thresholds query and save_ps_ratio_thresholds mutation."""

from unittest.mock import Mock

import pytest

from apps.core.context import Context
from apps.core.permissions import PermissionError as PermDenied
from apps.tenants.models import Role, Tenant, User
from apps.tenants.schema import TenantMutation, TenantQuery


@pytest.fixture
def tenant(db):
    return Tenant.objects.create(name="PsThresholdsTest")


@pytest.fixture
def admin_user(tenant):
    user = User.objects.create_user(
        email="admin@psthr.test",
        password="test1234",
        tenant=tenant,
        is_admin=True,
    )
    admin_role = Role.objects.get(tenant=tenant, name="Admin")
    user.roles.add(admin_role)
    return user


@pytest.fixture
def viewer_user(tenant):
    user = User.objects.create_user(
        email="viewer@psthr.test",
        password="test1234",
        tenant=tenant,
    )
    viewer_role = Role.objects.get(tenant=tenant, name="Viewer")
    user.roles.add(viewer_role)
    return user


def _info(user):
    request = Mock()
    request.tenant = user.tenant
    ctx = Context(request=request, user=user)
    info = Mock()
    info.context = ctx
    return info


class TestPsRatioThresholdsQuery:
    def test_returns_defaults_when_unset(self, admin_user):
        result = TenantQuery().ps_ratio_thresholds(_info(admin_user))
        assert result.amber_min == 1.0
        assert result.yellow_min == 1.5
        assert result.green_min == 2.0

    def test_returns_stored_values(self, tenant, admin_user):
        tenant.settings = {
            "ps_ratio_thresholds": {
                "amber_min": 0.5,
                "yellow_min": 1.2,
                "green_min": 1.8,
            }
        }
        tenant.save()
        result = TenantQuery().ps_ratio_thresholds(_info(admin_user))
        assert result.amber_min == 0.5
        assert result.yellow_min == 1.2
        assert result.green_min == 1.8


class TestSavePsRatioThresholdsMutation:
    def test_saves_valid_thresholds(self, tenant, admin_user):
        result = TenantMutation().save_ps_ratio_thresholds(
            _info(admin_user),
            amber_min=0.8,
            yellow_min=1.3,
            green_min=1.7,
        )
        assert result.success, result.error
        tenant.refresh_from_db()
        thresholds = tenant.settings["ps_ratio_thresholds"]
        assert thresholds["amber_min"] == 0.8
        assert thresholds["yellow_min"] == 1.3
        assert thresholds["green_min"] == 1.7

    def test_rejects_non_increasing(self, admin_user):
        result = TenantMutation().save_ps_ratio_thresholds(
            _info(admin_user),
            amber_min=1.5,
            yellow_min=1.0,
            green_min=2.0,
        )
        assert not result.success
        assert "increasing" in result.error.lower()

    def test_rejects_equal_values(self, admin_user):
        result = TenantMutation().save_ps_ratio_thresholds(
            _info(admin_user),
            amber_min=1.0,
            yellow_min=1.0,
            green_min=2.0,
        )
        assert not result.success

    def test_rejects_negative(self, admin_user):
        result = TenantMutation().save_ps_ratio_thresholds(
            _info(admin_user),
            amber_min=-0.1,
            yellow_min=1.5,
            green_min=2.0,
        )
        assert not result.success
        assert "non-negative" in result.error.lower()

    def test_viewer_cannot_save(self, viewer_user):
        with pytest.raises(PermDenied):
            TenantMutation().save_ps_ratio_thresholds(
                _info(viewer_user),
                amber_min=1.0,
                yellow_min=1.5,
                green_min=2.0,
            )
