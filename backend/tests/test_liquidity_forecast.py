"""Tests for liquidity forecast service."""
from datetime import date
from decimal import Decimal

import pytest
from dateutil.relativedelta import relativedelta

from apps.banking.models import BankAccount, BankTransaction, RecurringPattern
from apps.banking.services.forecast import (
    get_current_balance,
    get_liquidity_forecast,
    get_pattern_next_date,
    project_pattern,
)


@pytest.fixture
def bank_account(tenant):
    """Create a test bank account."""
    return BankAccount.objects.create(
        tenant=tenant,
        name="Test Account",
        bank_code="12345678",
        account_number="1234567890",
    )


@pytest.fixture
def transaction_with_balance(tenant, bank_account):
    """Create a transaction with closing balance."""

    def _create(closing_balance: Decimal, entry_date: date) -> BankTransaction:
        return BankTransaction.objects.create(
            tenant=tenant,
            account=bank_account,
            counterparty_name="Test",
            amount=Decimal("0"),
            entry_date=entry_date,
            closing_balance=closing_balance,
            import_hash=f"hash_{entry_date}_{closing_balance}",
        )

    return _create


@pytest.fixture
def recurring_pattern(tenant):
    """Create a test recurring pattern."""

    def _create(
        counterparty: str = "Netflix",
        amount: Decimal = Decimal("-12.99"),
        frequency: str = "monthly",
        day_of_month: int = 15,
        is_confirmed: bool = True,
        confidence_score: float = 0.9,
    ) -> RecurringPattern:
        return RecurringPattern.objects.create(
            tenant=tenant,
            counterparty_name=counterparty,
            average_amount=amount,
            frequency=frequency,
            day_of_month=day_of_month,
            is_confirmed=is_confirmed,
            confidence_score=confidence_score,
            last_occurrence=date.today() - relativedelta(days=15),
        )

    return _create


class TestCurrentBalance:
    """Tests for get_current_balance function."""

    @pytest.mark.django_db
    def test_single_account_balance(self, tenant, transaction_with_balance):
        """Get balance from single account."""
        transaction_with_balance(Decimal("5000.00"), date.today())

        balance, as_of = get_current_balance(tenant)

        assert balance == Decimal("5000.00")
        assert as_of == date.today()

    @pytest.mark.django_db
    def test_multiple_accounts_sum(self, tenant, bank_account, transaction_with_balance):
        """Sum balances from multiple accounts."""
        transaction_with_balance(Decimal("5000.00"), date.today())

        # Create second account with balance
        account2 = BankAccount.objects.create(
            tenant=tenant,
            name="Account 2",
            bank_code="87654321",
            account_number="0987654321",
        )
        BankTransaction.objects.create(
            tenant=tenant,
            account=account2,
            counterparty_name="Test",
            amount=Decimal("0"),
            entry_date=date.today(),
            closing_balance=Decimal("3000.00"),
            import_hash="hash_account2",
        )

        balance, _ = get_current_balance(tenant)

        assert balance == Decimal("8000.00")

    @pytest.mark.django_db
    def test_no_transactions_zero_balance(self, tenant):
        """No transactions returns zero balance."""
        balance, as_of = get_current_balance(tenant)

        assert balance == Decimal("0.00")
        assert as_of is None


class TestProjectPattern:
    """Tests for project_pattern function."""

    @pytest.mark.django_db
    def test_monthly_pattern_projects_12_months(self, recurring_pattern):
        """Monthly pattern should project for each of 12 months."""
        pattern = recurring_pattern(frequency="monthly")

        projections = project_pattern(pattern, months=12)

        assert len(projections) >= 11  # At least 11 occurrences in 12 months
        assert all(p.amount == Decimal("-12.99") for p in projections)
        assert all(p.counterparty_name == "Netflix" for p in projections)

    @pytest.mark.django_db
    def test_quarterly_pattern_projects_4_times(self, recurring_pattern):
        """Quarterly pattern should project ~4 times in 12 months."""
        pattern = recurring_pattern(frequency="quarterly")

        projections = project_pattern(pattern, months=12)

        assert 3 <= len(projections) <= 5

    @pytest.mark.django_db
    def test_ignored_pattern_no_projections(self, recurring_pattern):
        """Ignored patterns should not project."""
        pattern = recurring_pattern()
        pattern.is_ignored = True
        pattern.save()

        projections = project_pattern(pattern)

        assert len(projections) == 0

    @pytest.mark.django_db
    def test_paused_pattern_no_projections(self, recurring_pattern):
        """Paused patterns should not project."""
        pattern = recurring_pattern()
        pattern.is_paused = True
        pattern.save()

        projections = project_pattern(pattern)

        assert len(projections) == 0

    @pytest.mark.django_db
    def test_low_confidence_unconfirmed_no_projections(self, recurring_pattern):
        """Unconfirmed patterns with low confidence should not project."""
        pattern = recurring_pattern(is_confirmed=False, confidence_score=0.5)

        projections = project_pattern(pattern)

        assert len(projections) == 0

    @pytest.mark.django_db
    def test_high_confidence_unconfirmed_projects(self, recurring_pattern):
        """Unconfirmed patterns with high confidence should project."""
        pattern = recurring_pattern(is_confirmed=False, confidence_score=0.8)

        projections = project_pattern(pattern)

        assert len(projections) > 0


class TestLiquidityForecast:
    """Tests for get_liquidity_forecast function."""

    @pytest.mark.django_db
    def test_forecast_includes_starting_balance(
        self, tenant, transaction_with_balance, recurring_pattern
    ):
        """Forecast should start with current balance."""
        transaction_with_balance(Decimal("10000.00"), date.today())
        recurring_pattern()

        forecast = get_liquidity_forecast(tenant, months=3)

        assert len(forecast) == 3
        assert forecast[0].starting_balance == Decimal("10000.00")

    @pytest.mark.django_db
    def test_forecast_accumulates_costs(
        self, tenant, transaction_with_balance, recurring_pattern
    ):
        """Costs should reduce balance over time."""
        transaction_with_balance(Decimal("10000.00"), date.today())
        recurring_pattern(amount=Decimal("-100.00"))

        forecast = get_liquidity_forecast(tenant, months=3)

        # Balance should decrease each month
        assert forecast[0].ending_balance < forecast[0].starting_balance
        assert forecast[1].ending_balance < forecast[1].starting_balance


class TestPatternNextDate:
    """Tests for get_pattern_next_date function."""

    @pytest.mark.django_db
    def test_next_date_in_future(self, recurring_pattern):
        """Next date should always be in the future."""
        pattern = recurring_pattern()

        next_date = get_pattern_next_date(pattern)

        assert next_date is not None
        assert next_date > date.today()

    @pytest.mark.django_db
    def test_ignored_pattern_no_next_date(self, recurring_pattern):
        """Ignored patterns have no next date."""
        pattern = recurring_pattern()
        pattern.is_ignored = True
        pattern.save()

        next_date = get_pattern_next_date(pattern)

        assert next_date is None
