"""Tests for contract models and billing alignment."""
import base64
import pytest
from datetime import date
from decimal import Decimal
from dateutil.relativedelta import relativedelta

from apps.contracts.models import Contract, ContractItem, ContractAmendment, ContractAttachment
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
        """Test total price is quantity * monthly_unit_price (monthly price)."""
        item = ContractItem.objects.create(
            tenant=tenant,
            contract=annual_contract,
            product=product,
            quantity=5,
            unit_price=Decimal("100.00"),
            price_period="monthly",
        )

        # For monthly: total_price = 5 * (100 / 1) = 500
        assert item.total_price == Decimal("500.00")

    def test_total_price_with_quarterly_period(self, tenant, annual_contract, product):
        """Test total price normalizes quarterly prices to monthly."""
        item = ContractItem.objects.create(
            tenant=tenant,
            contract=annual_contract,
            product=product,
            quantity=1,
            unit_price=Decimal("300.00"),  # 300/quarter
            price_period="quarterly",
        )

        # For quarterly: total_price = 1 * (300 / 3) = 100/month
        assert item.total_price == Decimal("100.00")
        # Raw total should be the un-normalized value
        assert item.total_price_raw == Decimal("300.00")

    def test_total_price_with_annual_period(self, tenant, annual_contract, product):
        """Test total price normalizes annual prices to monthly."""
        item = ContractItem.objects.create(
            tenant=tenant,
            contract=annual_contract,
            product=product,
            quantity=2,
            unit_price=Decimal("1200.00"),  # 1200/year
            price_period="annual",
        )

        # For annual: total_price = 2 * (1200 / 12) = 2 * 100 = 200/month
        assert item.total_price == Decimal("200.00")
        # Raw total should be the un-normalized value
        assert item.total_price_raw == Decimal("2400.00")

    def test_same_arr_regardless_of_price_period(self, tenant, annual_contract, product):
        """Test that ARR is the same whether price is entered monthly, quarterly, or annual."""
        # Create three items with equivalent prices in different periods
        item_monthly = ContractItem.objects.create(
            tenant=tenant,
            contract=annual_contract,
            product=product,
            quantity=1,
            unit_price=Decimal("100.00"),  # 100/month
            price_period="monthly",
        )
        item_quarterly = ContractItem.objects.create(
            tenant=tenant,
            contract=annual_contract,
            product=product,
            quantity=1,
            unit_price=Decimal("300.00"),  # 300/quarter = 100/month
            price_period="quarterly",
        )
        item_annual = ContractItem.objects.create(
            tenant=tenant,
            contract=annual_contract,
            product=product,
            quantity=1,
            unit_price=Decimal("1200.00"),  # 1200/year = 100/month
            price_period="annual",
        )

        # All should have the same monthly total
        assert item_monthly.total_price == Decimal("100.00")
        assert item_quarterly.total_price == Decimal("100.00")
        assert item_annual.total_price == Decimal("100.00")


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


class TestOneOffItemBillingSchedule:
    """Test that one-off items use the full stated price, not monthly-normalized."""

    def test_one_off_annual_price_billed_in_full(self, tenant, annual_contract, product):
        """A one-off item priced at 150,000/year should bill 150,000 — not 12,500."""
        item = ContractItem.objects.create(
            tenant=tenant,
            contract=annual_contract,
            product=product,
            quantity=1,
            unit_price=Decimal("150000.00"),
            price_period="annual",
            is_one_off=True,
            billing_start_date=date(2025, 1, 1),
        )

        schedule = annual_contract.get_billing_schedule(
            from_date=date(2025, 1, 1),
            to_date=date(2025, 12, 31),
        )

        assert len(schedule) == 1
        event = schedule[0]
        assert event["items"][0]["is_one_off"] is True
        assert event["items"][0]["amount"] == Decimal("150000.00")
        assert event["total"] == Decimal("150000.00")

    def test_one_off_monthly_price_billed_in_full(self, tenant, monthly_contract, product):
        """A one-off item priced at 500/month should bill exactly 500."""
        item = ContractItem.objects.create(
            tenant=tenant,
            contract=monthly_contract,
            product=product,
            quantity=1,
            unit_price=Decimal("500.00"),
            price_period="monthly",
            is_one_off=True,
            billing_start_date=date(2025, 1, 1),
        )

        schedule = monthly_contract.get_billing_schedule(
            from_date=date(2025, 1, 1),
            to_date=date(2025, 12, 31),
        )

        assert len(schedule) == 1
        event = schedule[0]
        assert event["items"][0]["amount"] == Decimal("500.00")

    def test_discount_item_included_in_billing_schedule(self, tenant, annual_contract, product):
        """Discount items (no product, negative price) should appear in the billing schedule."""
        ContractItem.objects.create(
            tenant=tenant,
            contract=annual_contract,
            product=product,
            quantity=1,
            unit_price=Decimal("1200.00"),
            price_period="annual",
        )
        ContractItem.objects.create(
            tenant=tenant,
            contract=annual_contract,
            product=None,
            description="Volume Discount",
            quantity=1,
            unit_price=Decimal("-120.00"),
            price_period="annual",
        )

        schedule = annual_contract.get_billing_schedule(
            from_date=date(2025, 1, 1),
            to_date=date(2025, 12, 31),
        )

        assert len(schedule) == 1
        event = schedule[0]
        assert len(event["items"]) == 2
        # Product: 1200/12*12 = 1200, Discount: -120/12*12 = -120
        assert event["total"] == Decimal("1080.00")

    def test_discount_item_included_in_recognition_schedule(self, tenant, annual_contract, product):
        """Discount items (no product, negative price) should appear in the recognition schedule."""
        ContractItem.objects.create(
            tenant=tenant,
            contract=annual_contract,
            product=product,
            quantity=1,
            unit_price=Decimal("1200.00"),
            price_period="annual",
        )
        ContractItem.objects.create(
            tenant=tenant,
            contract=annual_contract,
            product=None,
            description="Volume Discount",
            quantity=1,
            unit_price=Decimal("-120.00"),
            price_period="annual",
        )

        schedule = annual_contract.get_recognition_schedule(
            from_date=date(2025, 1, 1),
            to_date=date(2025, 12, 31),
            include_history=True,
        )

        # Annual contract = 1 recognition event per year
        assert len(schedule) == 1
        event = schedule[0]
        assert len(event["items"]) == 2
        # Product: 1200/12*12 = 1200, Discount: -120/12*12 = -120
        assert event["total"] == Decimal("1080.00")

    def test_one_off_recognition_uses_full_price(self, tenant, annual_contract, product):
        """Recognition schedule should also use the full price for one-off items."""
        item = ContractItem.objects.create(
            tenant=tenant,
            contract=annual_contract,
            product=product,
            quantity=2,
            unit_price=Decimal("10000.00"),
            price_period="annual",
            is_one_off=True,
            start_date=date(2025, 3, 1),
            billing_start_date=date(2025, 3, 1),
        )

        schedule = annual_contract.get_recognition_schedule(
            from_date=date(2025, 1, 1),
            to_date=date(2025, 12, 31),
        )

        assert len(schedule) == 1
        event = schedule[0]
        # 2 x €10,000 = €20,000
        assert event["items"][0]["amount"] == Decimal("20000.00")
        assert event["total"] == Decimal("20000.00")


class TestMidCycleItemBilling:
    """Test that items added mid-billing-cycle get a pro-rated first event."""

    def test_annual_item_added_april_prorated_without_alignment(self, tenant, annual_contract, product):
        """
        Scenario: Annual contract Jan-Dec, item 1 billed Jan, item 2 added April 1.
        Without alignment, item 2 should still get a pro-rated Apr-Dec event.
        """
        # Item 1: 12,000 EUR/year (1,000/month), starts with contract
        ContractItem.objects.create(
            tenant=tenant,
            contract=annual_contract,
            product=product,
            quantity=1,
            unit_price=Decimal("1000.00"),
        )

        # Item 2: 6,000 EUR/year (500/month), billing effective April 1
        ContractItem.objects.create(
            tenant=tenant,
            contract=annual_contract,
            product=product,
            description="New service",
            quantity=1,
            unit_price=Decimal("500.00"),
            billing_start_date=date(2026, 4, 1),
        )

        schedule = annual_contract.get_billing_schedule(
            from_date=date(2026, 1, 1),
            to_date=date(2026, 12, 31),
        )

        # Should have 2 events: Jan 1 (item 1) and Apr 1 (item 2 pro-rated)
        assert len(schedule) == 2

        jan_event = schedule[0]
        assert jan_event["date"] == date(2026, 1, 1)
        assert len(jan_event["items"]) == 1
        assert jan_event["total"] == Decimal("12000.00")  # 1000 * 12

        apr_event = schedule[1]
        assert apr_event["date"] == date(2026, 4, 1)
        assert len(apr_event["items"]) == 1
        assert apr_event["items"][0]["is_prorated"] is True
        # 9 months (Apr-Dec): 500 * 12 * 9/12 = 4500
        assert apr_event["items"][0]["amount"] == Decimal("4500.00")
        assert apr_event["total"] == Decimal("4500.00")

    def test_annual_item_added_mid_cycle_full_year_next(self, tenant, annual_contract, product):
        """
        After the pro-rated first period, the next year should bill in full.
        """
        ContractItem.objects.create(
            tenant=tenant,
            contract=annual_contract,
            product=product,
            quantity=1,
            unit_price=Decimal("500.00"),
            billing_start_date=date(2026, 4, 1),
        )

        schedule = annual_contract.get_billing_schedule(
            from_date=date(2026, 1, 1),
            to_date=date(2027, 12, 31),
        )

        # Apr 2026 (pro-rated) + Jan 2027 (full year)
        assert len(schedule) == 2
        assert schedule[0]["date"] == date(2026, 4, 1)
        assert schedule[0]["items"][0]["amount"] == Decimal("4500.00")

        assert schedule[1]["date"] == date(2027, 1, 1)
        assert schedule[1]["items"][0]["is_prorated"] is False
        assert schedule[1]["items"][0]["amount"] == Decimal("6000.00")

    def test_quarterly_item_added_mid_cycle(self, tenant, customer, product):
        """Item added mid-quarter should get pro-rated stub event."""
        contract = Contract.objects.create(
            tenant=tenant,
            customer=customer,
            name="Quarterly Contract",
            status=Contract.Status.ACTIVE,
            start_date=date(2026, 1, 1),
            billing_start_date=date(2026, 1, 1),
            billing_interval=Contract.BillingInterval.QUARTERLY,
            billing_anchor_day=1,
        )
        # Item starts Feb 1 — mid Q1 cycle (Jan-Mar)
        ContractItem.objects.create(
            tenant=tenant,
            contract=contract,
            product=product,
            quantity=1,
            unit_price=Decimal("300.00"),
            billing_start_date=date(2026, 2, 1),
        )

        schedule = contract.get_billing_schedule(
            from_date=date(2026, 1, 1),
            to_date=date(2026, 6, 30),
        )

        # Feb 1 (pro-rated 2 months) + Apr 1 (full quarter)
        assert len(schedule) == 2
        assert schedule[0]["date"] == date(2026, 2, 1)
        assert schedule[0]["items"][0]["is_prorated"] is True
        # 2 months out of 3: 300 * 3 * 2/3 = 600
        assert schedule[0]["items"][0]["amount"] == Decimal("600.00")

        assert schedule[1]["date"] == date(2026, 4, 1)
        assert schedule[1]["items"][0]["amount"] == Decimal("900.00")

    def test_no_prorate_when_item_starts_on_cycle(self, tenant, annual_contract, product):
        """Item starting exactly on cycle date should NOT get a pro-rated stub."""
        ContractItem.objects.create(
            tenant=tenant,
            contract=annual_contract,
            product=product,
            quantity=1,
            unit_price=Decimal("500.00"),
            billing_start_date=date(2027, 1, 1),
        )

        schedule = annual_contract.get_billing_schedule(
            from_date=date(2027, 1, 1),
            to_date=date(2027, 12, 31),
        )

        assert len(schedule) == 1
        assert schedule[0]["date"] == date(2027, 1, 1)
        assert schedule[0]["items"][0]["is_prorated"] is False
        assert schedule[0]["items"][0]["amount"] == Decimal("6000.00")


class TestContractDurationCalculation:
    """Test contract duration calculation methods."""

    def test_get_min_end_date_with_min_duration(self, tenant, customer):
        """Test min_end_date calculation with min_duration_months."""
        contract = Contract.objects.create(
            tenant=tenant,
            customer=customer,
            name="Contract with Min Duration",
            status=Contract.Status.ACTIVE,
            start_date=date(2025, 1, 1),
            billing_start_date=date(2025, 1, 1),
            min_duration_months=12,
        )

        min_end = contract.get_min_end_date()
        assert min_end == date(2026, 1, 1)  # start_date + 12 months

    def test_get_min_end_date_without_min_duration(self, tenant, customer):
        """Test min_end_date returns None when no min_duration_months."""
        contract = Contract.objects.create(
            tenant=tenant,
            customer=customer,
            name="Contract without Min Duration",
            status=Contract.Status.ACTIVE,
            start_date=date(2025, 1, 1),
            billing_start_date=date(2025, 1, 1),
            min_duration_months=None,
        )

        assert contract.get_min_end_date() is None

    def test_get_earliest_cancellation_date_end_of_month_anchor(self, tenant, customer):
        """Test cancellation date calculation with END_OF_MONTH anchor."""
        contract = Contract.objects.create(
            tenant=tenant,
            customer=customer,
            name="Monthly Notice Contract",
            status=Contract.Status.ACTIVE,
            start_date=date(2025, 1, 1),
            billing_start_date=date(2025, 1, 1),
            notice_period_months=3,
            notice_period_anchor=Contract.NoticePeriodAnchor.END_OF_MONTH,
        )

        # Notice given on March 15, 2025
        # 3 months later = June 15
        # End of June = June 30
        cancellation = contract.get_earliest_cancellation_date(date(2025, 3, 15))
        assert cancellation == date(2025, 6, 30)

    def test_get_earliest_cancellation_date_end_of_quarter_anchor(self, tenant, customer):
        """Test cancellation date calculation with END_OF_QUARTER anchor."""
        contract = Contract.objects.create(
            tenant=tenant,
            customer=customer,
            name="Quarterly Notice Contract",
            status=Contract.Status.ACTIVE,
            start_date=date(2025, 1, 1),
            billing_start_date=date(2025, 1, 1),
            notice_period_months=3,
            notice_period_anchor=Contract.NoticePeriodAnchor.END_OF_QUARTER,
        )

        # Notice given on Feb 15, 2025
        # 3 months later = May 15
        # End of Q2 = June 30
        cancellation = contract.get_earliest_cancellation_date(date(2025, 2, 15))
        assert cancellation == date(2025, 6, 30)

    def test_get_earliest_cancellation_date_end_of_duration_anchor(self, tenant, customer):
        """Test cancellation date with END_OF_DURATION anchor during min duration."""
        contract = Contract.objects.create(
            tenant=tenant,
            customer=customer,
            name="Duration Notice Contract",
            status=Contract.Status.ACTIVE,
            start_date=date(2025, 1, 1),
            billing_start_date=date(2025, 1, 1),
            min_duration_months=12,
            notice_period_months=3,
            notice_period_anchor=Contract.NoticePeriodAnchor.END_OF_DURATION,
        )

        # Notice given on March 15, 2025 (within min duration)
        # 3 months later = June 15 (still before min end of Jan 1, 2026)
        # Should return min_end_date
        cancellation = contract.get_earliest_cancellation_date(date(2025, 3, 15))
        assert cancellation == date(2026, 1, 1)

    def test_get_effective_end_date_with_explicit_end(self, tenant, customer):
        """Test effective_end_date uses explicit end_date when set."""
        contract = Contract.objects.create(
            tenant=tenant,
            customer=customer,
            name="Fixed Term Contract",
            status=Contract.Status.ACTIVE,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),  # Explicit end date
            billing_start_date=date(2025, 1, 1),
        )

        assert contract.get_effective_end_date() == date(2025, 12, 31)

    def test_get_effective_end_date_cancelled(self, tenant, customer):
        """Test effective_end_date uses cancellation_effective_date when cancelled."""
        contract = Contract.objects.create(
            tenant=tenant,
            customer=customer,
            name="Cancelled Contract",
            status=Contract.Status.CANCELLED,
            start_date=date(2025, 1, 1),
            billing_start_date=date(2025, 1, 1),
            cancellation_effective_date=date(2025, 6, 30),
        )

        assert contract.get_effective_end_date() == date(2025, 6, 30)

    def test_get_duration_months_fixed_term(self, tenant, customer):
        """Test duration calculation for fixed-term contract."""
        contract = Contract.objects.create(
            tenant=tenant,
            customer=customer,
            name="12-Month Contract",
            status=Contract.Status.ACTIVE,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            billing_start_date=date(2025, 1, 1),
        )

        duration = contract.get_duration_months()
        assert duration == 12

    def test_get_duration_months_with_min_duration(self, tenant, customer):
        """Test duration calculation for indefinite contract with min duration."""
        contract = Contract.objects.create(
            tenant=tenant,
            customer=customer,
            name="Contract with Min Duration",
            status=Contract.Status.ACTIVE,
            start_date=date(2025, 1, 1),
            billing_start_date=date(2025, 1, 1),
            min_duration_months=24,  # 2 year minimum
        )

        # When today is before min_end_date, should return min_duration
        # Note: This test depends on current date, but min_end_date is 2027-01-01
        # and duration should be 24 months
        duration = contract.get_duration_months()
        assert duration >= 24

    def test_get_duration_months_minimum_one(self, tenant, customer):
        """Test duration is always at least 1 month."""
        contract = Contract.objects.create(
            tenant=tenant,
            customer=customer,
            name="Short Contract",
            status=Contract.Status.ACTIVE,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 15),  # Less than 1 month
            billing_start_date=date(2025, 1, 1),
        )

        duration = contract.get_duration_months()
        assert duration >= 1


# =============================================================================
# Contract Attachment Tests
# =============================================================================


class TestContractAttachments:
    """Tests for contract file attachments."""

    @pytest.fixture
    def simple_contract(self, db, tenant, customer):
        """Create a simple contract for attachment tests."""
        return Contract.objects.create(
            tenant=tenant,
            customer=customer,
            name="Test Contract",
            status=Contract.Status.ACTIVE,
            start_date=date(2025, 1, 1),
            billing_start_date=date(2025, 1, 1),
        )

    def test_upload_attachment_success(self, db, tenant, user, simple_contract):
        """Test successful file upload."""
        # Sample PDF content (minimal valid PDF header)
        pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\n%%EOF"

        attachment = ContractAttachment.objects.create(
            tenant=tenant,
            contract=simple_contract,
            original_filename="test.pdf",
            file_size=len(pdf_content),
            content_type="application/pdf",
            uploaded_by=user,
        )

        assert attachment.id is not None
        assert attachment.original_filename == "test.pdf"
        assert attachment.file_size == len(pdf_content)
        assert attachment.content_type == "application/pdf"
        assert attachment.tenant == tenant
        assert attachment.contract == simple_contract

    def test_attachment_tenant_isolation(self, db, tenant, simple_contract):
        """Test that attachments are filtered by tenant."""
        from apps.tenants.models import Tenant

        # Create another tenant
        other_tenant = Tenant.objects.create(name="Other Tenant")

        attachment = ContractAttachment.objects.create(
            tenant=tenant,
            contract=simple_contract,
            original_filename="test.pdf",
            file_size=100,
            content_type="application/pdf",
        )

        # Query with correct tenant finds attachment
        assert ContractAttachment.objects.filter(
            tenant=tenant, id=attachment.id
        ).exists()

        # Query with other tenant doesn't find attachment
        assert not ContractAttachment.objects.filter(
            tenant=other_tenant, id=attachment.id
        ).exists()

    def test_delete_attachment(self, db, tenant, simple_contract):
        """Test deleting an attachment."""
        attachment = ContractAttachment.objects.create(
            tenant=tenant,
            contract=simple_contract,
            original_filename="test.pdf",
            file_size=100,
            content_type="application/pdf",
        )

        attachment_id = attachment.id
        attachment.delete()

        assert not ContractAttachment.objects.filter(id=attachment_id).exists()

    def test_contract_attachments_relationship(self, db, tenant, simple_contract):
        """Test the contract.attachments relationship."""
        ContractAttachment.objects.create(
            tenant=tenant,
            contract=simple_contract,
            original_filename="doc1.pdf",
            file_size=100,
            content_type="application/pdf",
        )
        ContractAttachment.objects.create(
            tenant=tenant,
            contract=simple_contract,
            original_filename="doc2.pdf",
            file_size=200,
            content_type="application/pdf",
        )

        assert simple_contract.attachments.count() == 2
        filenames = list(simple_contract.attachments.values_list("original_filename", flat=True))
        assert "doc1.pdf" in filenames
        assert "doc2.pdf" in filenames

    def test_attachment_cascade_delete(self, db, tenant, customer):
        """Test that attachments are deleted when contract is deleted."""
        contract = Contract.objects.create(
            tenant=tenant,
            customer=customer,
            name="Delete Test Contract",
            status=Contract.Status.DRAFT,
            start_date=date(2025, 1, 1),
            billing_start_date=date(2025, 1, 1),
        )

        attachment = ContractAttachment.objects.create(
            tenant=tenant,
            contract=contract,
            original_filename="test.pdf",
            file_size=100,
            content_type="application/pdf",
        )

        attachment_id = attachment.id
        contract.delete()

        assert not ContractAttachment.objects.filter(id=attachment_id).exists()


# =============================================================================
# Contract Total Value Tests with Period-Specific Pricing
# =============================================================================


class TestContractTotalValueWithPricePeriods:
    """Tests for contract total_value calculation with period-specific pricing."""

    def test_total_value_with_multiple_price_periods(self, tenant, customer, product):
        """Test total_value correctly sums values across different price periods.

        Contract: 4 years (2025-2028), annual billing
        Item: 1x Product with different prices per year
        - Year 1 (2025): €100/month
        - Year 2 (2026): €120/month
        - Year 3 (2027): €140/month
        - Year 4 (2028): €160/month

        Expected: (100*12) + (120*12) + (140*12) + (160*12) = 6240
        """
        from apps.contracts.models import ContractItemPrice
        from apps.contracts.schema import calculate_contract_total_value

        contract = Contract.objects.create(
            tenant=tenant,
            customer=customer,
            name="Multi-Year Contract",
            status=Contract.Status.ACTIVE,
            start_date=date(2025, 1, 1),
            end_date=date(2028, 12, 31),
            billing_start_date=date(2025, 1, 1),
            billing_interval=Contract.BillingInterval.ANNUAL,
        )

        item = ContractItem.objects.create(
            tenant=tenant,
            contract=contract,
            product=product,
            quantity=1,
            unit_price=Decimal("100.00"),  # Base price (should not be used when periods exist)
            price_period=ContractItem.PricePeriod.MONTHLY,
        )

        # Create price periods for each year
        ContractItemPrice.objects.create(
            tenant=tenant,
            item=item,
            valid_from=date(2025, 1, 1),
            valid_to=date(2025, 12, 31),
            unit_price=Decimal("100.00"),
            price_period=ContractItemPrice.PricePeriod.MONTHLY,
        )
        ContractItemPrice.objects.create(
            tenant=tenant,
            item=item,
            valid_from=date(2026, 1, 1),
            valid_to=date(2026, 12, 31),
            unit_price=Decimal("120.00"),
            price_period=ContractItemPrice.PricePeriod.MONTHLY,
        )
        ContractItemPrice.objects.create(
            tenant=tenant,
            item=item,
            valid_from=date(2027, 1, 1),
            valid_to=date(2027, 12, 31),
            unit_price=Decimal("140.00"),
            price_period=ContractItemPrice.PricePeriod.MONTHLY,
        )
        ContractItemPrice.objects.create(
            tenant=tenant,
            item=item,
            valid_from=date(2028, 1, 1),
            valid_to=date(2028, 12, 31),
            unit_price=Decimal("160.00"),
            price_period=ContractItemPrice.PricePeriod.MONTHLY,
        )

        # Calculate total value using the standalone function
        total = calculate_contract_total_value(contract)

        # Expected: (100*12) + (120*12) + (140*12) + (160*12) = 6240
        expected = Decimal("6240.00")
        assert total == expected, f"Expected {expected}, got {total}"

    def test_total_value_uses_base_price_for_gaps(self, tenant, customer, product):
        """Test total_value uses base price for periods without specific pricing.

        Contract: 3 years (2025-2027)
        Item: 1x Product, base price €100/month
        - Year 1 (2025): specific price €80/month
        - Year 2 (2026): no specific price (should use base €100/month)
        - Year 3 (2027): specific price €120/month

        Expected: (80*12) + (100*12) + (120*12) = 3600
        """
        from apps.contracts.models import ContractItemPrice
        from apps.contracts.schema import calculate_contract_total_value

        contract = Contract.objects.create(
            tenant=tenant,
            customer=customer,
            name="Contract with Gaps",
            status=Contract.Status.ACTIVE,
            start_date=date(2025, 1, 1),
            end_date=date(2027, 12, 31),
            billing_start_date=date(2025, 1, 1),
        )

        item = ContractItem.objects.create(
            tenant=tenant,
            contract=contract,
            product=product,
            quantity=1,
            unit_price=Decimal("100.00"),  # Base price used for Year 2
            price_period=ContractItem.PricePeriod.MONTHLY,
        )

        # Year 1 specific price
        ContractItemPrice.objects.create(
            tenant=tenant,
            item=item,
            valid_from=date(2025, 1, 1),
            valid_to=date(2025, 12, 31),
            unit_price=Decimal("80.00"),
            price_period=ContractItemPrice.PricePeriod.MONTHLY,
        )
        # Year 2: no specific price - should use base price

        # Year 3 specific price
        ContractItemPrice.objects.create(
            tenant=tenant,
            item=item,
            valid_from=date(2027, 1, 1),
            valid_to=date(2027, 12, 31),
            unit_price=Decimal("120.00"),
            price_period=ContractItemPrice.PricePeriod.MONTHLY,
        )

        total = calculate_contract_total_value(contract)

        # Expected: (80*12) + (100*12) + (120*12) = 3600
        expected = Decimal("3600.00")
        assert total == expected, f"Expected {expected}, got {total}"

    def test_total_value_without_price_periods(self, tenant, customer, product):
        """Test total_value falls back to base price when no price periods exist."""
        from apps.contracts.schema import calculate_contract_total_value

        contract = Contract.objects.create(
            tenant=tenant,
            customer=customer,
            name="Simple Contract",
            status=Contract.Status.ACTIVE,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            billing_start_date=date(2025, 1, 1),
        )

        ContractItem.objects.create(
            tenant=tenant,
            contract=contract,
            product=product,
            quantity=2,
            unit_price=Decimal("50.00"),
            price_period=ContractItem.PricePeriod.MONTHLY,
        )

        total = calculate_contract_total_value(contract)

        # Expected: 2 quantity × €50/month × 12 months = €1200
        expected = Decimal("1200.00")
        assert total == expected, f"Expected {expected}, got {total}"


class TestResetContractToDraft:
    """Test resetting an active contract to draft status."""

    TRANSITION_MUTATION = """
        mutation TransitionContractStatus($contractId: ID!, $newStatus: String!) {
            transitionContractStatus(contractId: $contractId, newStatus: $newStatus) {
                success
                error
                contract {
                    id
                    status
                }
            }
        }
    """

    def _execute(self, client, user, contract_id, new_status="draft"):
        from apps.core.auth import create_access_token

        token = create_access_token(user)
        return client.post(
            "/graphql",
            content_type="application/json",
            data={
                "query": self.TRANSITION_MUTATION,
                "variables": {
                    "contractId": str(contract_id),
                    "newStatus": new_status,
                },
            },
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

    def test_reset_active_contract_no_invoices(self, db, tenant, user, customer, client):
        """Reset active contract with no invoices succeeds, amendments deleted."""
        contract = Contract.objects.create(
            tenant=tenant,
            customer=customer,
            name="Active Contract",
            status=Contract.Status.ACTIVE,
            start_date=date(2026, 1, 1),
            billing_start_date=date(2026, 1, 1),
            billing_interval=Contract.BillingInterval.MONTHLY,
        )
        # Create some amendments
        ContractAmendment.objects.create(
            tenant=tenant,
            contract=contract,
            effective_date=date(2026, 1, 15),
            type=ContractAmendment.AmendmentType.TERMS_CHANGED,
            description="Some change",
            changes={"action": "test"},
        )
        assert contract.amendments.count() == 1

        response = self._execute(client, user, contract.id)

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["transitionContractStatus"]["success"] is True
        assert data["data"]["transitionContractStatus"]["contract"]["status"] == "draft"

        contract.refresh_from_db()
        assert contract.status == Contract.Status.DRAFT
        assert contract.amendments.count() == 0

    def test_reset_active_contract_with_generated_invoices(self, db, tenant, user, customer, client):
        """Reset blocked when generated invoices exist."""
        from apps.invoices.models import InvoiceRecord

        contract = Contract.objects.create(
            tenant=tenant,
            customer=customer,
            name="Invoiced Contract",
            status=Contract.Status.ACTIVE,
            start_date=date(2026, 1, 1),
            billing_start_date=date(2026, 1, 1),
            billing_interval=Contract.BillingInterval.MONTHLY,
        )
        InvoiceRecord.objects.create(
            tenant=tenant,
            contract=contract,
            customer=customer,
            invoice_number="INV-001",
            billing_date=date(2026, 1, 1),
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31),
            total_net=Decimal("100.00"),
            tax_rate=Decimal("19.00"),
            tax_amount=Decimal("19.00"),
            total_gross=Decimal("119.00"),
            line_items_snapshot=[],
            company_data_snapshot={},
            customer_name=customer.name,
            contract_name=contract.name,
        )

        response = self._execute(client, user, contract.id)

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["transitionContractStatus"]["success"] is False
        assert "invoices" in data["data"]["transitionContractStatus"]["error"]

        contract.refresh_from_db()
        assert contract.status == Contract.Status.ACTIVE

    def test_reset_active_contract_with_imported_invoices(self, db, tenant, user, customer, client):
        """Reset allowed even when imported invoices exist (only generated invoices block)."""
        from apps.invoices.models import ImportedInvoice

        contract = Contract.objects.create(
            tenant=tenant,
            customer=customer,
            name="Imported Invoice Contract",
            status=Contract.Status.ACTIVE,
            start_date=date(2026, 1, 1),
            billing_start_date=date(2026, 1, 1),
            billing_interval=Contract.BillingInterval.MONTHLY,
        )
        ImportedInvoice.objects.create(
            tenant=tenant,
            contract=contract,
            invoice_number="IMP-001",
            invoice_date=date(2026, 1, 1),
            total_amount=Decimal("119.00"),
            pdf_file="test.pdf",
            original_filename="test.pdf",
            file_size=1024,
        )

        response = self._execute(client, user, contract.id)

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["transitionContractStatus"]["success"] is True

    def test_reset_non_active_contract_fails(self, db, tenant, user, customer, client):
        """Reset from draft/paused/cancelled/ended returns error."""
        for status in [Contract.Status.DRAFT, Contract.Status.PAUSED]:
            contract = Contract.objects.create(
                tenant=tenant,
                customer=customer,
                name=f"Contract {status}",
                status=status,
                start_date=date(2026, 1, 1),
                billing_start_date=date(2026, 1, 1),
                billing_interval=Contract.BillingInterval.MONTHLY,
            )

            response = self._execute(client, user, contract.id)

            data = response.json()
            assert data["data"]["transitionContractStatus"]["success"] is False
            assert "Cannot transition" in data["data"]["transitionContractStatus"]["error"]


class TestChangeContractCustomer:
    """Test changing the customer of a draft contract."""

    CHANGE_CUSTOMER_MUTATION = """
        mutation ChangeContractCustomer($contractId: ID!, $customerId: ID!) {
            changeContractCustomer(contractId: $contractId, customerId: $customerId) {
                success
                error
                contract {
                    id
                    customer {
                        id
                    }
                }
            }
        }
    """

    def _execute(self, client, user, contract_id, customer_id):
        from apps.core.auth import create_access_token

        token = create_access_token(user)
        return client.post(
            "/graphql",
            content_type="application/json",
            data={
                "query": self.CHANGE_CUSTOMER_MUTATION,
                "variables": {
                    "contractId": str(contract_id),
                    "customerId": str(customer_id),
                },
            },
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

    def test_change_customer_on_draft_contract(self, db, tenant, user, customer, client):
        """Change customer on draft contract succeeds, group set to null."""
        from apps.contracts.models import ContractGroup

        other_customer = Customer.objects.create(
            tenant=tenant,
            name="Other Customer",
            is_active=True,
        )
        group = ContractGroup.objects.create(
            tenant=tenant,
            customer=customer,
            name="Test Group",
        )
        contract = Contract.objects.create(
            tenant=tenant,
            customer=customer,
            name="Draft Contract",
            status=Contract.Status.DRAFT,
            start_date=date(2026, 1, 1),
            billing_start_date=date(2026, 1, 1),
            billing_interval=Contract.BillingInterval.MONTHLY,
            group=group,
        )

        response = self._execute(client, user, contract.id, other_customer.id)

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["changeContractCustomer"]["success"] is True
        assert data["data"]["changeContractCustomer"]["contract"]["customer"]["id"] == str(other_customer.id)

        contract.refresh_from_db()
        assert contract.customer_id == other_customer.id
        assert contract.group is None

    def test_change_customer_on_active_contract_creates_amendment(self, db, tenant, user, customer, client):
        """Change customer on active contract succeeds and creates amendment."""
        from apps.contracts.models import ContractAmendment

        other_customer = Customer.objects.create(
            tenant=tenant,
            name="Other Customer 2",
            is_active=True,
        )
        contract = Contract.objects.create(
            tenant=tenant,
            customer=customer,
            name="Active Contract",
            status=Contract.Status.ACTIVE,
            start_date=date(2026, 1, 1),
            billing_start_date=date(2026, 1, 1),
            billing_interval=Contract.BillingInterval.MONTHLY,
        )

        response = self._execute(client, user, contract.id, other_customer.id)

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["changeContractCustomer"]["success"] is True

        contract.refresh_from_db()
        assert contract.customer_id == other_customer.id
        assert contract.group is None

        amendment = ContractAmendment.objects.filter(contract=contract).first()
        assert amendment is not None
        assert amendment.type == ContractAmendment.AmendmentType.TERMS_CHANGED
        assert "Other Customer 2" in amendment.description
