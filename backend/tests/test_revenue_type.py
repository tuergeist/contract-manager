"""Tests for revenue type classification."""
import pytest
from datetime import date
from decimal import Decimal

from apps.contracts.models import Contract, ContractItem
from apps.core.models import RevenueType
from apps.customers.models import Customer
from apps.products.models import Product


@pytest.fixture
def customer(db, tenant):
    return Customer.objects.create(
        tenant=tenant,
        name="Test Customer",
        is_active=True,
    )


@pytest.fixture
def contract(db, tenant, customer):
    return Contract.objects.create(
        tenant=tenant,
        customer=customer,
        name="Test Contract",
        status=Contract.Status.ACTIVE,
        start_date=date(2026, 1, 1),
        billing_start_date=date(2026, 1, 1),
        billing_interval=Contract.BillingInterval.MONTHLY,
        billing_anchor_day=1,
    )


@pytest.fixture
def recurring_product(db, tenant):
    return Product.objects.create(
        tenant=tenant,
        name="SaaS License",
        sku="SAAS-001",
        type=Product.ProductType.SUBSCRIPTION,
        revenue_type=RevenueType.RECURRING,
    )


@pytest.fixture
def dev_product(db, tenant):
    return Product.objects.create(
        tenant=tenant,
        name="Custom Dev",
        sku="DEV-001",
        type=Product.ProductType.ONE_OFF,
        revenue_type=RevenueType.ADVANCED_DEVELOPMENT,
    )


class TestGetEffectiveRevenueType:
    def test_inherits_from_product(self, contract, recurring_product, tenant):
        item = ContractItem.objects.create(
            tenant=tenant,
            contract=contract,
            product=recurring_product,
            quantity=1,
            unit_price=Decimal("100.00"),
        )
        assert item.get_effective_revenue_type() == RevenueType.RECURRING

    def test_explicit_override_takes_precedence(self, contract, recurring_product, tenant):
        item = ContractItem.objects.create(
            tenant=tenant,
            contract=contract,
            product=recurring_product,
            quantity=1,
            unit_price=Decimal("100.00"),
            revenue_type=RevenueType.ADVANCED_DEVELOPMENT,
        )
        assert item.get_effective_revenue_type() == RevenueType.ADVANCED_DEVELOPMENT

    def test_no_product_with_explicit_type(self, contract, tenant):
        item = ContractItem.objects.create(
            tenant=tenant,
            contract=contract,
            product=None,
            quantity=1,
            unit_price=Decimal("-50.00"),
            revenue_type=RevenueType.TRAINING_IMPLEMENTATION,
        )
        assert item.get_effective_revenue_type() == RevenueType.TRAINING_IMPLEMENTATION

    def test_no_product_no_type_returns_none(self, contract, tenant):
        item = ContractItem.objects.create(
            tenant=tenant,
            contract=contract,
            product=None,
            quantity=1,
            unit_price=Decimal("-50.00"),
        )
        assert item.get_effective_revenue_type() is None

    def test_product_without_revenue_type_returns_none(self, contract, tenant):
        product = Product.objects.create(
            tenant=tenant,
            name="Unclassified Product",
            sku="UNC-001",
            type=Product.ProductType.ONE_OFF,
            revenue_type=None,
        )
        item = ContractItem.objects.create(
            tenant=tenant,
            contract=contract,
            product=product,
            quantity=1,
            unit_price=Decimal("200.00"),
        )
        assert item.get_effective_revenue_type() is None

    def test_dev_product_inheritance(self, contract, dev_product, tenant):
        item = ContractItem.objects.create(
            tenant=tenant,
            contract=contract,
            product=dev_product,
            quantity=1,
            unit_price=Decimal("5000.00"),
            is_one_off=True,
        )
        assert item.get_effective_revenue_type() == RevenueType.ADVANCED_DEVELOPMENT
