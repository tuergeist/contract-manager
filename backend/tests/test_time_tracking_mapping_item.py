"""Tests for update_time_tracking_mapping_item mutation."""

from datetime import date
from decimal import Decimal
from unittest.mock import Mock

import pytest

from apps.contracts.models import (
    Contract,
    ContractItem,
    TimeTrackingProjectMapping,
)
from apps.contracts.schema import ContractMutation as Mutation
from apps.core.context import Context
from apps.customers.models import Customer
from apps.products.models import Product
from apps.tenants.models import Role, Tenant, User


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tenant(db):
    return Tenant.objects.create(name="MappingTest", currency="EUR")


@pytest.fixture
def other_tenant(db):
    return Tenant.objects.create(name="OtherTenant", currency="EUR")


@pytest.fixture
def user(tenant):
    u = User.objects.create_user(
        email="mapper@test.com",
        password="test1234",
        tenant=tenant,
    )
    admin_role = Role.objects.get(tenant=tenant, name="Admin")
    u.roles.add(admin_role)
    return u


@pytest.fixture
def viewer_user(tenant):
    u = User.objects.create_user(
        email="viewer@test.com",
        password="view1234",
        tenant=tenant,
    )
    viewer_role = Role.objects.get(tenant=tenant, name="Viewer")
    u.roles.add(viewer_role)
    return u


@pytest.fixture
def customer(tenant):
    return Customer.objects.create(tenant=tenant, name="Mapping Co", is_active=True)


@pytest.fixture
def product(tenant):
    return Product.objects.create(tenant=tenant, name="Mapping Product", sku="MAP-001")


@pytest.fixture
def contract(tenant, customer):
    return Contract.objects.create(
        tenant=tenant,
        customer=customer,
        name="Mapping Contract",
        status=Contract.Status.ACTIVE,
        start_date=date(2025, 1, 1),
        billing_start_date=date(2025, 1, 1),
        billing_interval=Contract.BillingInterval.MONTHLY,
        billing_anchor_day=1,
    )


@pytest.fixture
def other_contract(tenant, customer):
    """Different contract on the same tenant to test cross-contract rejection."""
    return Contract.objects.create(
        tenant=tenant,
        customer=customer,
        name="Other Contract",
        status=Contract.Status.ACTIVE,
        start_date=date(2025, 1, 1),
        billing_start_date=date(2025, 1, 1),
        billing_interval=Contract.BillingInterval.MONTHLY,
        billing_anchor_day=1,
    )


@pytest.fixture
def contract_item(tenant, contract, product):
    return ContractItem.objects.create(
        tenant=tenant,
        contract=contract,
        product=product,
        quantity=1,
        unit_price=Decimal("100.00"),
    )


@pytest.fixture
def contract_item_no_product(tenant, contract):
    return ContractItem.objects.create(
        tenant=tenant,
        contract=contract,
        product=None,
        description="Custom line item description that should be truncated nicely",
        quantity=1,
        unit_price=Decimal("50.00"),
    )


@pytest.fixture
def other_contract_item(tenant, other_contract, product):
    """ContractItem on a different contract (same tenant)."""
    return ContractItem.objects.create(
        tenant=tenant,
        contract=other_contract,
        product=product,
        quantity=1,
        unit_price=Decimal("200.00"),
    )


@pytest.fixture
def mapping(tenant, contract):
    return TimeTrackingProjectMapping.objects.create(
        tenant=tenant,
        contract=contract,
        external_project_id="ext-mapping-1",
        external_project_name="Mapping Project",
        external_customer_name="Mapping Cust",
    )


@pytest.fixture
def mapping_with_item(tenant, contract, contract_item):
    return TimeTrackingProjectMapping.objects.create(
        tenant=tenant,
        contract=contract,
        contract_item=contract_item,
        external_project_id="ext-mapping-2",
        external_project_name="Mapping Project 2",
        external_customer_name="Mapping Cust 2",
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _Info(user):
    request = Mock()
    request.tenant = user.tenant
    ctx = Context(request=request, user=user)
    info = Mock()
    info.context = ctx
    return info


def _mutation():
    return Mutation()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestUpdateTimeTrackingMappingItem:
    def test_assigns_item_to_mapping_without_item(
        self, user, mapping, contract_item
    ):
        """Assigning an item to a mapping with contract_item=None should succeed."""
        info = _Info(user)
        result = _mutation().update_time_tracking_mapping_item(
            info,
            mapping_id=str(mapping.id),
            contract_item_id=str(contract_item.id),
        )

        assert result.success, result.error
        assert result.mapping is not None
        assert result.mapping.contract_item_id == contract_item.id
        # Item has product → name comes from product.name
        assert result.mapping.contract_item_name == "Mapping Product"

        mapping.refresh_from_db()
        assert mapping.contract_item_id == contract_item.id

    def test_assigns_item_without_product_uses_description(
        self, user, mapping, contract_item_no_product
    ):
        """When the item has no product, contract_item_name uses truncated description."""
        info = _Info(user)
        result = _mutation().update_time_tracking_mapping_item(
            info,
            mapping_id=str(mapping.id),
            contract_item_id=str(contract_item_no_product.id),
        )

        assert result.success, result.error
        assert result.mapping is not None
        assert result.mapping.contract_item_id == contract_item_no_product.id
        # Description is sliced to 50 chars
        assert (
            result.mapping.contract_item_name
            == contract_item_no_product.description[:50]
        )

    def test_unassign_clears_contract_item(self, user, mapping_with_item):
        """Passing contract_item_id=None unassigns the item."""
        info = _Info(user)
        assert mapping_with_item.contract_item_id is not None

        result = _mutation().update_time_tracking_mapping_item(
            info,
            mapping_id=str(mapping_with_item.id),
            contract_item_id=None,
        )

        assert result.success, result.error
        assert result.mapping is not None
        assert result.mapping.contract_item_id is None
        assert result.mapping.contract_item_name is None

        mapping_with_item.refresh_from_db()
        assert mapping_with_item.contract_item is None

    def test_rejects_item_from_different_contract(
        self, user, mapping, other_contract_item
    ):
        """An item from a different contract returns an error and leaves mapping intact."""
        info = _Info(user)
        result = _mutation().update_time_tracking_mapping_item(
            info,
            mapping_id=str(mapping.id),
            contract_item_id=str(other_contract_item.id),
        )

        assert not result.success
        assert result.error == "Item not found in this contract"

        mapping.refresh_from_db()
        assert mapping.contract_item is None

    def test_mapping_not_found_returns_error(self, user):
        """An unknown mapping id returns an error."""
        info = _Info(user)
        result = _mutation().update_time_tracking_mapping_item(
            info,
            mapping_id="999999",
            contract_item_id=None,
        )

        assert not result.success
        assert result.error == "Mapping not found"

    def test_mapping_from_other_tenant_not_found(
        self, user, other_tenant, customer
    ):
        """A mapping belonging to another tenant is not visible."""
        # Build a contract + mapping under a different tenant
        foreign_customer = Customer.objects.create(
            tenant=other_tenant, name="Foreign", is_active=True
        )
        foreign_contract = Contract.objects.create(
            tenant=other_tenant,
            customer=foreign_customer,
            name="Foreign Contract",
            status=Contract.Status.ACTIVE,
            start_date=date(2025, 1, 1),
            billing_start_date=date(2025, 1, 1),
            billing_interval=Contract.BillingInterval.MONTHLY,
            billing_anchor_day=1,
        )
        foreign_mapping = TimeTrackingProjectMapping.objects.create(
            tenant=other_tenant,
            contract=foreign_contract,
            external_project_id="ext-foreign",
            external_project_name="Foreign Project",
        )

        info = _Info(user)
        result = _mutation().update_time_tracking_mapping_item(
            info,
            mapping_id=str(foreign_mapping.id),
            contract_item_id=None,
        )

        assert not result.success
        assert result.error == "Mapping not found"

    def test_permission_denied_for_viewer(
        self, viewer_user, mapping, contract_item
    ):
        """A user without contracts.write permission is rejected."""
        info = _Info(viewer_user)
        result = _mutation().update_time_tracking_mapping_item(
            info,
            mapping_id=str(mapping.id),
            contract_item_id=str(contract_item.id),
        )

        assert not result.success
        assert result.error is not None
        assert "permission" in result.error.lower()

        mapping.refresh_from_db()
        assert mapping.contract_item is None
