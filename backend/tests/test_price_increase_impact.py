"""Tests for price increase impact calculations."""
import pytest
from datetime import date
from decimal import Decimal
from unittest.mock import patch

from apps.contracts.models import Contract, ContractItem, ContractItemPrice
from apps.contracts.schema import calculate_price_increase_impact
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
def product(db, tenant):
    return Product.objects.create(
        tenant=tenant,
        name="Test Product",
        sku="TEST-001",
    )


@pytest.fixture
def active_contract(db, tenant, customer):
    return Contract.objects.create(
        tenant=tenant,
        customer=customer,
        name="Existing Contract",
        status=Contract.Status.ACTIVE,
        start_date=date(2024, 1, 1),
        billing_start_date=date(2024, 1, 1),
        billing_interval=Contract.BillingInterval.MONTHLY,
    )


class TestPriceIncreaseImpact:
    @patch("apps.contracts.schema.date")
    def test_no_increases_returns_zeros(self, mock_date, db, tenant, active_contract, product):
        mock_date.today.return_value = date(2026, 6, 1)
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)

        # Item with same price all year — no increase
        item = ContractItem.objects.create(
            tenant=tenant,
            contract=active_contract,
            product=product,
            quantity=1,
            unit_price=Decimal("100.00"),
            price_period="monthly",
        )

        result = calculate_price_increase_impact(tenant, 2026)
        assert result.total_arr_impact == Decimal("0")
        assert result.inflation_arr_impact == Decimal("0")
        assert result.negotiated_arr_impact == Decimal("0")
        assert result.untagged_arr_impact == Decimal("0")
        assert result.item_count == 0

    def test_inflation_increase(self, db, tenant, active_contract, product):
        item = ContractItem.objects.create(
            tenant=tenant,
            contract=active_contract,
            product=product,
            quantity=1,
            unit_price=Decimal("100.00"),
            price_period="monthly",
        )
        # Price period: old price in 2025
        ContractItemPrice.objects.create(
            tenant=tenant,
            item=item,
            valid_from=date(2025, 1, 1),
            valid_to=date(2025, 12, 31),
            unit_price=Decimal("100.00"),
            price_period="monthly",
            source="fixed",
        )
        # New price in 2026 tagged as inflation
        ContractItemPrice.objects.create(
            tenant=tenant,
            item=item,
            valid_from=date(2026, 1, 1),
            valid_to=None,
            unit_price=Decimal("110.00"),
            price_period="monthly",
            source="fixed",
            increase_type="inflation",
        )

        result = calculate_price_increase_impact(tenant, 2026)
        expected_delta = Decimal("10.00") * 12  # (110-100) * 1 * 12
        assert result.total_arr_impact == expected_delta
        assert result.inflation_arr_impact == expected_delta
        assert result.negotiated_arr_impact == Decimal("0")
        assert result.item_count == 1

    def test_negotiated_increase(self, db, tenant, active_contract, product):
        item = ContractItem.objects.create(
            tenant=tenant,
            contract=active_contract,
            product=product,
            quantity=2,
            unit_price=Decimal("200.00"),
            price_period="monthly",
        )
        ContractItemPrice.objects.create(
            tenant=tenant,
            item=item,
            valid_from=date(2025, 1, 1),
            valid_to=date(2025, 12, 31),
            unit_price=Decimal("200.00"),
            price_period="monthly",
            source="fixed",
        )
        ContractItemPrice.objects.create(
            tenant=tenant,
            item=item,
            valid_from=date(2026, 1, 1),
            valid_to=None,
            unit_price=Decimal("250.00"),
            price_period="monthly",
            source="fixed",
            increase_type="negotiated",
        )

        result = calculate_price_increase_impact(tenant, 2026)
        expected_delta = Decimal("50.00") * 2 * 12  # (250-200) * qty 2 * 12
        assert result.total_arr_impact == expected_delta
        assert result.negotiated_arr_impact == expected_delta
        assert result.inflation_arr_impact == Decimal("0")

    def test_untagged_increase(self, db, tenant, active_contract, product):
        item = ContractItem.objects.create(
            tenant=tenant,
            contract=active_contract,
            product=product,
            quantity=1,
            unit_price=Decimal("100.00"),
            price_period="monthly",
        )
        # Price period without increase_type
        ContractItemPrice.objects.create(
            tenant=tenant,
            item=item,
            valid_from=date(2026, 1, 1),
            valid_to=None,
            unit_price=Decimal("120.00"),
            price_period="monthly",
            source="fixed",
            increase_type=None,
        )

        result = calculate_price_increase_impact(tenant, 2026)
        # base price is 100 (no period for 2025), new price is 120
        expected_delta = Decimal("20.00") * 12
        assert result.total_arr_impact == expected_delta
        assert result.untagged_arr_impact == expected_delta

    def test_mixed_types(self, db, tenant, active_contract, product):
        """Multiple items with different increase types."""
        item1 = ContractItem.objects.create(
            tenant=tenant,
            contract=active_contract,
            product=product,
            quantity=1,
            unit_price=Decimal("100.00"),
            price_period="monthly",
        )
        item2 = ContractItem.objects.create(
            tenant=tenant,
            contract=active_contract,
            product=product,
            quantity=1,
            unit_price=Decimal("200.00"),
            price_period="monthly",
        )

        # Item 1: inflation increase
        ContractItemPrice.objects.create(
            tenant=tenant,
            item=item1,
            valid_from=date(2026, 1, 1),
            valid_to=None,
            unit_price=Decimal("110.00"),
            price_period="monthly",
            source="fixed",
            increase_type="inflation",
        )
        # Item 2: negotiated increase
        ContractItemPrice.objects.create(
            tenant=tenant,
            item=item2,
            valid_from=date(2026, 1, 1),
            valid_to=None,
            unit_price=Decimal("230.00"),
            price_period="monthly",
            source="fixed",
            increase_type="negotiated",
        )

        result = calculate_price_increase_impact(tenant, 2026)
        assert result.inflation_arr_impact == Decimal("10.00") * 12
        assert result.negotiated_arr_impact == Decimal("30.00") * 12
        assert result.total_arr_impact == Decimal("40.00") * 12
        assert result.item_count == 2

    def test_new_contracts_excluded(self, db, tenant, customer, product):
        """Contracts starting in the target year are excluded (new business)."""
        new_contract = Contract.objects.create(
            tenant=tenant,
            customer=customer,
            name="New Contract 2026",
            status=Contract.Status.ACTIVE,
            start_date=date(2026, 3, 1),  # Started in 2026
            billing_start_date=date(2026, 3, 1),
            billing_interval=Contract.BillingInterval.MONTHLY,
        )
        ContractItem.objects.create(
            tenant=tenant,
            contract=new_contract,
            product=product,
            quantity=1,
            unit_price=Decimal("500.00"),
            price_period="monthly",
        )

        result = calculate_price_increase_impact(tenant, 2026)
        assert result.total_arr_impact == Decimal("0")
        assert result.item_count == 0

    def test_expired_contracts_excluded(self, db, tenant, customer, product):
        """Contracts that ended before target year are excluded."""
        expired = Contract.objects.create(
            tenant=tenant,
            customer=customer,
            name="Expired Contract",
            status=Contract.Status.ACTIVE,
            start_date=date(2023, 1, 1),
            end_date=date(2025, 6, 30),  # Ended before 2026
            billing_start_date=date(2023, 1, 1),
            billing_interval=Contract.BillingInterval.MONTHLY,
        )
        item = ContractItem.objects.create(
            tenant=tenant,
            contract=expired,
            product=product,
            quantity=1,
            unit_price=Decimal("100.00"),
            price_period="monthly",
        )
        ContractItemPrice.objects.create(
            tenant=tenant,
            item=item,
            valid_from=date(2026, 1, 1),
            valid_to=None,
            unit_price=Decimal("150.00"),
            price_period="monthly",
            source="fixed",
            increase_type="inflation",
        )

        result = calculate_price_increase_impact(tenant, 2026)
        assert result.total_arr_impact == Decimal("0")

    def test_one_off_items_excluded(self, db, tenant, active_contract, product):
        """One-off items are not considered for price increase impact."""
        item = ContractItem.objects.create(
            tenant=tenant,
            contract=active_contract,
            product=product,
            quantity=1,
            unit_price=Decimal("1000.00"),
            price_period="monthly",
            is_one_off=True,
        )
        ContractItemPrice.objects.create(
            tenant=tenant,
            item=item,
            valid_from=date(2026, 1, 1),
            valid_to=None,
            unit_price=Decimal("2000.00"),
            price_period="monthly",
            source="fixed",
            increase_type="inflation",
        )

        result = calculate_price_increase_impact(tenant, 2026)
        assert result.total_arr_impact == Decimal("0")
        assert result.item_count == 0

    def test_bulk_price_increase_stores_increase_type(self, db, tenant, active_contract, product):
        """Verify ContractItemPrice supports increase_type field."""
        item = ContractItem.objects.create(
            tenant=tenant,
            contract=active_contract,
            product=product,
            quantity=1,
            unit_price=Decimal("100.00"),
            price_period="monthly",
        )
        price = ContractItemPrice.objects.create(
            tenant=tenant,
            item=item,
            valid_from=date(2026, 1, 1),
            valid_to=None,
            unit_price=Decimal("103.50"),
            price_period="monthly",
            source="fixed",
            increase_type="inflation",
        )

        price.refresh_from_db()
        assert price.increase_type == "inflation"

        price.increase_type = "negotiated"
        price.save()
        price.refresh_from_db()
        assert price.increase_type == "negotiated"
