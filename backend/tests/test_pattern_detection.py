"""Tests for recurring payment pattern detection."""
from datetime import date, timedelta
from decimal import Decimal

import pytest

from apps.banking.models import BankAccount, BankTransaction, RecurringPattern
from apps.banking.services.pattern_detection import (
    calculate_confidence,
    calculate_similarity,
    detect_frequency,
    detect_recurring_patterns,
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
def create_transaction(tenant, bank_account):
    """Factory for creating test transactions."""

    def _create(
        counterparty_name: str,
        amount: Decimal,
        entry_date: date,
        counterparty_iban: str = "",
    ) -> BankTransaction:
        return BankTransaction.objects.create(
            tenant=tenant,
            account=bank_account,
            counterparty_name=counterparty_name,
            counterparty_iban=counterparty_iban,
            amount=amount,
            entry_date=entry_date,
            import_hash=BankTransaction.compute_hash(
                bank_account.id,
                entry_date,
                amount,
                "EUR",
                "",
                counterparty_name,
            ),
        )

    return _create


class TestSimilarityScoring:
    """Tests for calculate_similarity function."""

    def test_identical_transactions_score_3(self, create_transaction):
        """Transactions with same counterparty, amount, and day-of-month score 3."""
        txn1 = create_transaction("Netflix", Decimal("-12.99"), date(2024, 1, 15))
        txn2 = create_transaction("Netflix", Decimal("-12.99"), date(2024, 2, 15))

        result = calculate_similarity(txn1, txn2)

        assert result.score == 3
        assert result.counterparty_match is True
        assert result.amount_match is True
        assert result.timing_match is True

    def test_same_counterparty_different_amount_scores_2(self, create_transaction):
        """Same counterparty and timing but different amount scores 2."""
        txn1 = create_transaction("Electric Co", Decimal("-150.00"), date(2024, 1, 5))
        txn2 = create_transaction("Electric Co", Decimal("-180.00"), date(2024, 2, 5))

        result = calculate_similarity(txn1, txn2)

        assert result.score == 2
        assert result.counterparty_match is True
        assert result.amount_match is False  # >5% difference
        assert result.timing_match is True

    def test_amount_within_5_percent_matches(self, create_transaction):
        """Amounts within 5% should match."""
        txn1 = create_transaction("Vendor", Decimal("-100.00"), date(2024, 1, 10))
        txn2 = create_transaction("Vendor", Decimal("-104.00"), date(2024, 2, 10))

        result = calculate_similarity(txn1, txn2)

        assert result.amount_match is True
        assert result.score == 3

    def test_amount_over_5_percent_no_match(self, create_transaction):
        """Amounts over 5% apart should not match."""
        txn1 = create_transaction("Vendor", Decimal("-100.00"), date(2024, 1, 10))
        txn2 = create_transaction("Vendor", Decimal("-106.00"), date(2024, 2, 10))

        result = calculate_similarity(txn1, txn2)

        assert result.amount_match is False

    def test_different_sign_amounts_no_match(self, create_transaction):
        """Positive and negative amounts should not match."""
        txn1 = create_transaction("Client", Decimal("100.00"), date(2024, 1, 10))
        txn2 = create_transaction("Client", Decimal("-100.00"), date(2024, 2, 10))

        result = calculate_similarity(txn1, txn2)

        assert result.amount_match is False

    def test_timing_within_3_days_matches(self, create_transaction):
        """Transactions within 3 days of same day-of-month should match."""
        txn1 = create_transaction("Vendor", Decimal("-50.00"), date(2024, 1, 15))
        txn2 = create_transaction("Vendor", Decimal("-50.00"), date(2024, 2, 17))

        result = calculate_similarity(txn1, txn2)

        assert result.timing_match is True

    def test_timing_over_3_days_no_match(self, create_transaction):
        """Transactions over 3 days apart should not match timing."""
        txn1 = create_transaction("Vendor", Decimal("-50.00"), date(2024, 1, 5))
        txn2 = create_transaction("Vendor", Decimal("-50.00"), date(2024, 2, 20))

        result = calculate_similarity(txn1, txn2)

        assert result.timing_match is False

    def test_only_counterparty_match_scores_1(self, create_transaction):
        """Only counterparty match should score 1."""
        txn1 = create_transaction("Vendor", Decimal("-50.00"), date(2024, 1, 5))
        txn2 = create_transaction("Vendor", Decimal("-200.00"), date(2024, 2, 20))

        result = calculate_similarity(txn1, txn2)

        assert result.score == 1
        assert result.counterparty_match is True


class TestFrequencyDetection:
    """Tests for detect_frequency function."""

    def test_monthly_frequency(self):
        """Detect monthly frequency from ~30 day intervals."""
        dates = [
            date(2024, 1, 15),
            date(2024, 2, 15),
            date(2024, 3, 15),
            date(2024, 4, 15),
        ]
        frequency, day = detect_frequency(dates)

        assert frequency == "monthly"
        assert day == 15

    def test_quarterly_frequency(self):
        """Detect quarterly frequency from ~90 day intervals."""
        dates = [
            date(2024, 1, 10),
            date(2024, 4, 10),
            date(2024, 7, 10),
        ]
        frequency, day = detect_frequency(dates)

        assert frequency == "quarterly"
        assert day == 10

    def test_annual_frequency(self):
        """Detect annual frequency from ~365 day intervals."""
        dates = [
            date(2022, 6, 1),
            date(2023, 6, 1),
            date(2024, 6, 1),
        ]
        frequency, day = detect_frequency(dates)

        assert frequency == "annual"

    def test_irregular_frequency(self):
        """Irregular intervals should be classified as irregular."""
        dates = [
            date(2024, 1, 1),
            date(2024, 1, 15),
            date(2024, 3, 20),
        ]
        frequency, _ = detect_frequency(dates)

        assert frequency == "irregular"


class TestPatternDetection:
    """Tests for detect_recurring_patterns function."""

    @pytest.mark.django_db
    def test_detect_monthly_subscription(self, tenant, create_transaction):
        """Detect a monthly subscription pattern."""
        today = date.today()
        for i in range(4):
            month_date = today - timedelta(days=30 * i)
            create_transaction("Netflix", Decimal("-12.99"), month_date)

        patterns = detect_recurring_patterns(tenant)

        assert len(patterns) == 1
        pattern = patterns[0]
        assert pattern.counterparty_name == "Netflix"
        assert pattern.average_amount == Decimal("-12.99")
        assert pattern.frequency == "monthly"
        assert pattern.confidence_score > 0.5

    @pytest.mark.django_db
    def test_ignore_single_transaction(self, tenant, create_transaction):
        """Single transactions should not create patterns."""
        create_transaction("One-time Vendor", Decimal("-500.00"), date.today())

        patterns = detect_recurring_patterns(tenant)

        assert len(patterns) == 0

    @pytest.mark.django_db
    def test_separate_costs_and_income(self, tenant, create_transaction):
        """Costs and income from same counterparty create separate patterns."""
        today = date.today()
        # Regular payments to vendor (costs)
        for i in range(3):
            create_transaction("Client A", Decimal("-100.00"), today - timedelta(days=30 * i))
        # Regular payments from vendor (income)
        for i in range(3):
            create_transaction(
                "Client A",
                Decimal("500.00"),
                today - timedelta(days=30 * i + 5),
            )

        patterns = detect_recurring_patterns(tenant)

        assert len(patterns) == 2
        costs = [p for p in patterns if p.average_amount < 0]
        income = [p for p in patterns if p.average_amount > 0]
        assert len(costs) == 1
        assert len(income) == 1

    @pytest.mark.django_db
    def test_low_similarity_not_grouped(self, tenant, create_transaction):
        """Transactions with only 1 similarity point should not create patterns."""
        today = date.today()
        # Same counterparty but wildly different amounts and timing
        create_transaction("Misc Vendor", Decimal("-50.00"), today)
        create_transaction("Misc Vendor", Decimal("-500.00"), today - timedelta(days=45))

        patterns = detect_recurring_patterns(tenant)

        # Should not create a pattern since similarity < 2
        misc_patterns = [p for p in patterns if "Misc Vendor" in p.counterparty_name]
        assert len(misc_patterns) == 0
