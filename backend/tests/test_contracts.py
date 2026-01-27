"""Tests for contract models and billing alignment."""
import pytest
from datetime import date
from decimal import Decimal
from dateutil.relativedelta import relativedelta

from apps.contracts.models import Contract, ContractItem
from apps.customers.models import Customer
from apps.products.models import Product


@pytest.fixture
def customer(db, tenant):
    """Create a test customer."""
    return Customer.objects.create(
        tenant=tenant,
        name="Test Customer",
        is_active=True,
    )


@pytest.fixture
def product(db, tenant):
    """Create a test product."""
    return Product.objects.create(
        tenant=tenant,
        name="Test Product",
        sku="TEST-001",
    )


@pytest.fixture
def annual_contract(db, tenant, customer):
    """Create a test contract with annual billing starting Jan 1."""
    return Contract.objects.create(
        tenant=tenant,
        customer=customer,
        name="Annual Contract",
        status=Contract.Status.ACTIVE,
        start_date=date(2025, 1, 1),
        billing_start_date=date(2025, 1, 1),
        billing_interval=Contract.BillingInterval.ANNUAL,
        billing_anchor_day=1,
    )


@pytest.fixture
def monthly_contract(db, tenant, customer):
    """Create a test contract with monthly billing."""
    return Contract.objects.create(
        tenant=tenant,
        customer=customer,
        name="Monthly Contract",
        status=Contract.Status.ACTIVE,
        start_date=date(2025, 1, 1),
        billing_start_date=date(2025, 1, 1),
        billing_interval=Contract.BillingInterval.MONTHLY,
        billing_anchor_day=1,
    )


@pytest.fixture
def quarterly_contract(db, tenant, customer):
    """Create a test contract with quarterly billing starting Jan 1."""
    return Contract.objects.create(
        tenant=tenant,
        customer=customer,
        name="Quarterly Contract",
        status=Contract.Status.ACTIVE,
        start_date=date(2025, 1, 1),
        billing_start_date=date(2025, 1, 1),
        billing_interval=Contract.BillingInterval.QUARTERLY,
        billing_anchor_day=1,
    )


class TestContractItemBillingFields:
    """Test ContractItem billing fields."""

    def test_item_with_billing_dates(self, tenant, annual_contract, product):
        """Test creating an item with custom billing dates."""
        item = ContractItem.objects.create(
            tenant=tenant,
            contract=annual_contract,
            product=product,
            quantity=1,
            unit_price=Decimal("100.00"),
            billing_start_date=date(2026, 5, 4),
            align_to_contract_at=date(2027, 1, 1),
        )

        assert item.billing_start_date == date(2026, 5, 4)
        assert item.align_to_contract_at == date(2027, 1, 1)
        assert item.billing_end_date is None

    def test_item_without_billing_dates(self, tenant, annual_contract, product):
        """Test creating an item without custom billing dates."""
        item = ContractItem.objects.create(
            tenant=tenant,
            contract=annual_contract,
            product=product,
            quantity=1,
            unit_price=Decimal("100.00"),
        )

        assert item.billing_start_date is None
        assert item.align_to_contract_at is None
        assert item.billing_end_date is None


class TestSuggestedAlignmentDate:
    """Test get_suggested_alignment_date() method."""

    def test_annual_contract_item_added_mid_year(self, tenant, annual_contract, product):
        """
        Test: Item added on 4.5.26 to annual contract starting 1.1.
        Expected: Suggests 1.1.27 as alignment date.
        """
        item = ContractItem(
            tenant=tenant,
            contract=annual_contract,
            product=product,
            quantity=1,
            unit_price=Decimal("100.00"),
            billing_start_date=date(2026, 5, 4),
        )

        suggested = item.get_suggested_alignment_date()
        assert suggested == date(2027, 1, 1)

    def test_annual_contract_item_added_in_december(self, tenant, annual_contract, product):
        """
        Test: Item added on 15.12.26 to annual contract starting 1.1.
        Expected: Suggests 1.1.27 as alignment date.
        """
        item = ContractItem(
            tenant=tenant,
            contract=annual_contract,
            product=product,
            quantity=1,
            unit_price=Decimal("100.00"),
            billing_start_date=date(2026, 12, 15),
        )

        suggested = item.get_suggested_alignment_date()
        assert suggested == date(2027, 1, 1)

    def test_annual_contract_item_added_on_cycle_start(self, tenant, annual_contract, product):
        """
        Test: Item added on 1.1.26 (exactly on cycle start).
        Expected: Suggests 1.1.27 (next cycle).
        """
        item = ContractItem(
            tenant=tenant,
            contract=annual_contract,
            product=product,
            quantity=1,
            unit_price=Decimal("100.00"),
            billing_start_date=date(2026, 1, 1),
        )

        suggested = item.get_suggested_alignment_date()
        assert suggested == date(2027, 1, 1)

    def test_monthly_contract_item_added_mid_month(self, tenant, monthly_contract, product):
        """
        Test: Item added on 15.5.26 to monthly contract.
        Expected: Suggests 1.6.26 as alignment date.
        """
        item = ContractItem(
            tenant=tenant,
            contract=monthly_contract,
            product=product,
            quantity=1,
            unit_price=Decimal("100.00"),
            billing_start_date=date(2026, 5, 15),
        )

        suggested = item.get_suggested_alignment_date()
        assert suggested == date(2026, 6, 1)

    def test_quarterly_contract_item_added_mid_quarter(self, tenant, quarterly_contract, product):
        """
        Test: Item added on 15.2.26 to quarterly contract starting 1.1.
        Expected: Suggests 1.4.26 as alignment date (next quarter).
        """
        item = ContractItem(
            tenant=tenant,
            contract=quarterly_contract,
            product=product,
            quantity=1,
            unit_price=Decimal("100.00"),
            billing_start_date=date(2026, 2, 15),
        )

        suggested = item.get_suggested_alignment_date()
        assert suggested == date(2026, 4, 1)

    def test_quarterly_contract_item_added_last_day_of_quarter(self, tenant, quarterly_contract, product):
        """
        Test: Item added on 31.3.26 (last day of Q1).
        Expected: Suggests 1.4.26 (Q2 start).
        """
        item = ContractItem(
            tenant=tenant,
            contract=quarterly_contract,
            product=product,
            quantity=1,
            unit_price=Decimal("100.00"),
            billing_start_date=date(2026, 3, 31),
        )

        suggested = item.get_suggested_alignment_date()
        assert suggested == date(2026, 4, 1)

    def test_uses_billing_start_date_when_provided(self, tenant, annual_contract, product):
        """Test that billing_start_date is used for calculation."""
        item = ContractItem(
            tenant=tenant,
            contract=annual_contract,
            product=product,
            quantity=1,
            unit_price=Decimal("100.00"),
            billing_start_date=date(2026, 5, 4),
        )

        # Should use billing_start_date, not from_date parameter
        suggested = item.get_suggested_alignment_date()
        assert suggested == date(2027, 1, 1)

    def test_explicit_from_date_overrides_billing_start(self, tenant, annual_contract, product):
        """Test that explicit from_date parameter is used when provided."""
        item = ContractItem(
            tenant=tenant,
            contract=annual_contract,
            product=product,
            quantity=1,
            unit_price=Decimal("100.00"),
            billing_start_date=date(2026, 5, 4),
        )

        # Explicit from_date should be used
        suggested = item.get_suggested_alignment_date(from_date=date(2027, 6, 1))
        assert suggested == date(2028, 1, 1)


class TestContractItemTotalPrice:
    """Test ContractItem total price calculation."""

    def test_total_price_calculation(self, tenant, annual_contract, product):
        """Test total price is quantity * unit_price."""
        item = ContractItem.objects.create(
            tenant=tenant,
            contract=annual_contract,
            product=product,
            quantity=5,
            unit_price=Decimal("100.00"),
        )

        assert item.total_price == Decimal("500.00")


class TestGetPriceAt:
    """Test ContractItem.get_price_at() method for year-specific pricing."""

    def test_returns_unit_price_when_no_price_periods(self, tenant, annual_contract, product):
        """
        Test backward compatibility: returns unit_price when no price_periods exist.
        This ensures existing contracts work unchanged.
        """
        from apps.contracts.models import ContractItemPrice

        item = ContractItem.objects.create(
            tenant=tenant,
            contract=annual_contract,
            product=product,
            quantity=1,
            unit_price=Decimal("100.00"),
        )

        # No price periods defined - should return unit_price
        assert item.get_price_at(date(2025, 1, 1)) == Decimal("100.00")
        assert item.get_price_at(date(2026, 6, 15)) == Decimal("100.00")
        assert item.get_price_at(date(2030, 12, 31)) == Decimal("100.00")

    def test_returns_correct_price_for_date_within_period(self, tenant, annual_contract, product):
        """Test returns correct price when date falls within a price period."""
        from apps.contracts.models import ContractItemPrice

        item = ContractItem.objects.create(
            tenant=tenant,
            contract=annual_contract,
            product=product,
            quantity=1,
            unit_price=Decimal("100.00"),
        )

        # Year 1: €80/month (Jan 2025 - Dec 2025)
        ContractItemPrice.objects.create(
            tenant=tenant,
            item=item,
            valid_from=date(2025, 1, 1),
            valid_to=date(2025, 12, 31),
            unit_price=Decimal("80.00"),
            source="fixed",
        )

        # Year 2: €100/month (Jan 2026 - Dec 2026)
        ContractItemPrice.objects.create(
            tenant=tenant,
            item=item,
            valid_from=date(2026, 1, 1),
            valid_to=date(2026, 12, 31),
            unit_price=Decimal("100.00"),
            source="fixed",
        )

        # Year 3+: €120/month (Jan 2027 onwards, no end date)
        ContractItemPrice.objects.create(
            tenant=tenant,
            item=item,
            valid_from=date(2027, 1, 1),
            valid_to=None,
            unit_price=Decimal("120.00"),
            source="list",
        )

        # Test Year 1
        assert item.get_price_at(date(2025, 1, 1)) == Decimal("80.00")
        assert item.get_price_at(date(2025, 6, 15)) == Decimal("80.00")
        assert item.get_price_at(date(2025, 12, 31)) == Decimal("80.00")

        # Test Year 2
        assert item.get_price_at(date(2026, 1, 1)) == Decimal("100.00")
        assert item.get_price_at(date(2026, 7, 20)) == Decimal("100.00")

        # Test Year 3+ (ongoing)
        assert item.get_price_at(date(2027, 1, 1)) == Decimal("120.00")
        assert item.get_price_at(date(2028, 6, 15)) == Decimal("120.00")
        assert item.get_price_at(date(2030, 12, 31)) == Decimal("120.00")

    def test_returns_unit_price_for_date_before_any_period(self, tenant, annual_contract, product):
        """Test falls back to unit_price when date is before any price period."""
        from apps.contracts.models import ContractItemPrice

        item = ContractItem.objects.create(
            tenant=tenant,
            contract=annual_contract,
            product=product,
            quantity=1,
            unit_price=Decimal("100.00"),
        )

        # Price period only starts in 2026
        ContractItemPrice.objects.create(
            tenant=tenant,
            item=item,
            valid_from=date(2026, 1, 1),
            valid_to=None,
            unit_price=Decimal("120.00"),
            source="fixed",
        )

        # Date before any period should return unit_price
        assert item.get_price_at(date(2025, 6, 15)) == Decimal("100.00")
        # Date within period should return period price
        assert item.get_price_at(date(2026, 6, 15)) == Decimal("120.00")

    def test_returns_unit_price_for_gap_between_periods(self, tenant, annual_contract, product):
        """Test falls back to unit_price when date falls in gap between periods."""
        from apps.contracts.models import ContractItemPrice

        item = ContractItem.objects.create(
            tenant=tenant,
            contract=annual_contract,
            product=product,
            quantity=1,
            unit_price=Decimal("100.00"),
        )

        # Period 1: Jan-Mar 2025
        ContractItemPrice.objects.create(
            tenant=tenant,
            item=item,
            valid_from=date(2025, 1, 1),
            valid_to=date(2025, 3, 31),
            unit_price=Decimal("80.00"),
            source="fixed",
        )

        # Period 2: Jul-Dec 2025 (gap in Apr-Jun)
        ContractItemPrice.objects.create(
            tenant=tenant,
            item=item,
            valid_from=date(2025, 7, 1),
            valid_to=date(2025, 12, 31),
            unit_price=Decimal("90.00"),
            source="fixed",
        )

        # Within period 1
        assert item.get_price_at(date(2025, 2, 15)) == Decimal("80.00")
        # Gap - should return unit_price
        assert item.get_price_at(date(2025, 5, 15)) == Decimal("100.00")
        # Within period 2
        assert item.get_price_at(date(2025, 9, 15)) == Decimal("90.00")


class TestPriceLock:
    """Test price lock functionality."""

    def test_price_locked_fields_defaults(self, tenant, annual_contract, product):
        """Test price_locked defaults to False."""
        item = ContractItem.objects.create(
            tenant=tenant,
            contract=annual_contract,
            product=product,
            quantity=1,
            unit_price=Decimal("100.00"),
        )

        assert item.price_locked is False
        assert item.price_locked_until is None

    def test_price_locked_can_be_set(self, tenant, annual_contract, product):
        """Test price_locked fields can be set."""
        item = ContractItem.objects.create(
            tenant=tenant,
            contract=annual_contract,
            product=product,
            quantity=1,
            unit_price=Decimal("100.00"),
            price_locked=True,
            price_locked_until=date(2026, 12, 31),
        )

        assert item.price_locked is True
        assert item.price_locked_until == date(2026, 12, 31)


class TestNoticePeriodAfterMin:
    """Test notice_period_after_min_months field."""

    def test_notice_period_after_min_defaults_to_null(self, tenant, customer):
        """Test notice_period_after_min_months defaults to None."""
        contract = Contract.objects.create(
            tenant=tenant,
            customer=customer,
            name="Test Contract",
            status=Contract.Status.DRAFT,
            start_date=date(2025, 1, 1),
            billing_start_date=date(2025, 1, 1),
            notice_period_months=3,
        )

        assert contract.notice_period_after_min_months is None

    def test_notice_period_after_min_can_be_set(self, tenant, customer):
        """Test notice_period_after_min_months can be set to a different value."""
        contract = Contract.objects.create(
            tenant=tenant,
            customer=customer,
            name="Test Contract",
            status=Contract.Status.DRAFT,
            start_date=date(2025, 1, 1),
            billing_start_date=date(2025, 1, 1),
            notice_period_months=3,  # 3 months before min duration ends
            notice_period_after_min_months=1,  # 1 month after min duration
            min_duration_months=12,
        )

        assert contract.notice_period_months == 3
        assert contract.notice_period_after_min_months == 1
        assert contract.min_duration_months == 12


class TestBillingScheduleWithPricePeriods:
    """Test billing schedule calculation with year-specific pricing."""

    def test_billing_uses_price_at_date(self, tenant, annual_contract, product):
        """Test billing schedule uses get_price_at() for each billing date."""
        from apps.contracts.models import ContractItemPrice

        item = ContractItem.objects.create(
            tenant=tenant,
            contract=annual_contract,
            product=product,
            quantity=2,
            unit_price=Decimal("100.00"),
        )

        # Year 1: €80/month
        ContractItemPrice.objects.create(
            tenant=tenant,
            item=item,
            valid_from=date(2025, 1, 1),
            valid_to=date(2025, 12, 31),
            unit_price=Decimal("80.00"),
            source="fixed",
        )

        # Year 2+: €100/month
        ContractItemPrice.objects.create(
            tenant=tenant,
            item=item,
            valid_from=date(2026, 1, 1),
            valid_to=None,
            unit_price=Decimal("100.00"),
            source="fixed",
        )

        # Get billing schedule for 2025 and 2026
        schedule = annual_contract.get_billing_schedule(
            from_date=date(2025, 1, 1),
            to_date=date(2026, 12, 31),
        )

        # Should have 2 billing events (annual billing)
        assert len(schedule) == 2

        # 2025 billing: 2 x €80 x 12 months = €1920
        event_2025 = schedule[0]
        assert event_2025["date"] == date(2025, 1, 1)
        assert event_2025["items"][0]["unit_price"] == Decimal("80.00")
        assert event_2025["total"] == Decimal("1920.00")

        # 2026 billing: 2 x €100 x 12 months = €2400
        event_2026 = schedule[1]
        assert event_2026["date"] == date(2026, 1, 1)
        assert event_2026["items"][0]["unit_price"] == Decimal("100.00")
        assert event_2026["total"] == Decimal("2400.00")

    def test_billing_falls_back_to_unit_price(self, tenant, annual_contract, product):
        """Test billing uses unit_price when no price_periods exist (backward compat)."""
        item = ContractItem.objects.create(
            tenant=tenant,
            contract=annual_contract,
            product=product,
            quantity=1,
            unit_price=Decimal("50.00"),
        )

        # No price periods - should use unit_price
        schedule = annual_contract.get_billing_schedule(
            from_date=date(2025, 1, 1),
            to_date=date(2025, 12, 31),
        )

        assert len(schedule) == 1
        event = schedule[0]
        assert event["items"][0]["unit_price"] == Decimal("50.00")
        # 1 x €50 x 12 months = €600
        assert event["total"] == Decimal("600.00")
