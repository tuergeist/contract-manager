"""Service for detecting recurring payment patterns from bank transactions."""
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from statistics import mean, stdev
from typing import Optional

from django.db.models import QuerySet

from apps.banking.models import BankTransaction, Counterparty, RecurringPattern
from apps.tenants.models import Tenant


# Patterns to extract a grouping key from booking_text when no counterparty
BOOKING_TEXT_PATTERNS = [
    # SEPA Sammel-Ueberweisung (batch transfers like payroll)
    (r"SEPA Sammel-Ueberweisung", "SEPA Sammel-Ueberweisung"),
    (r"Sammelueberweisung", "Sammelueberweisung"),
    # Add more patterns as needed
]


def extract_booking_pattern(booking_text: str) -> Optional[str]:
    """Extract a pattern name from booking text for grouping."""
    if not booking_text:
        return None
    for pattern, name in BOOKING_TEXT_PATTERNS:
        if re.search(pattern, booking_text, re.IGNORECASE):
            return name
    return None


@dataclass
class SimilarityResult:
    """Result of comparing two transactions for similarity."""

    score: int
    counterparty_match: bool
    amount_match: bool
    timing_match: bool


def calculate_similarity(
    txn1: BankTransaction,
    txn2: BankTransaction,
    lenient_amount: bool = False,
) -> SimilarityResult:
    """
    Calculate similarity score between two transactions.

    Scoring:
    - Counterparty match (same counterparty FK or IBAN): +1
    - Amount match (within 5%, or 30% if lenient_amount): +1
    - Timing pattern (same day-of-month ±3 days): +1

    Returns SimilarityResult with score and individual match flags.
    """
    score = 0

    # Counterparty match: same counterparty FK or IBAN
    counterparty_match = False
    if txn1.counterparty_id and txn2.counterparty_id:
        if txn1.counterparty_id == txn2.counterparty_id:
            counterparty_match = True
    if not counterparty_match:
        # Fall back to IBAN match if available
        if txn1.counterparty.iban and txn2.counterparty.iban:
            if txn1.counterparty.iban == txn2.counterparty.iban:
                counterparty_match = True
    if counterparty_match:
        score += 1

    # Amount match: within 5% (or 30% for batch payments like payroll)
    amount_match = False
    amount_threshold = Decimal("0.30") if lenient_amount else Decimal("0.05")
    if txn1.amount != 0 and txn2.amount != 0:
        # Both must be same sign (both costs or both income)
        if (txn1.amount < 0) == (txn2.amount < 0):
            larger = max(abs(txn1.amount), abs(txn2.amount))
            diff = abs(txn1.amount - txn2.amount)
            if larger > 0 and (diff / larger) <= amount_threshold:
                amount_match = True
                score += 1

    # Timing match: same day-of-month ±3 days
    timing_match = False
    day1 = txn1.entry_date.day
    day2 = txn2.entry_date.day
    if abs(day1 - day2) <= 3 or abs(day1 - day2) >= 28:  # Handle month wraparound
        timing_match = True
        score += 1

    return SimilarityResult(
        score=score,
        counterparty_match=counterparty_match,
        amount_match=amount_match,
        timing_match=timing_match,
    )


def detect_frequency(dates: list[date]) -> tuple[str, Optional[int]]:
    """
    Detect the frequency of payments based on dates.

    Returns (frequency, typical_day_of_month).
    """
    if len(dates) < 2:
        return RecurringPattern.Frequency.IRREGULAR, None

    # Sort dates and calculate intervals in days
    sorted_dates = sorted(dates)
    intervals = []
    for i in range(1, len(sorted_dates)):
        interval = (sorted_dates[i] - sorted_dates[i - 1]).days
        intervals.append(interval)

    if not intervals:
        return RecurringPattern.Frequency.IRREGULAR, None

    avg_interval = mean(intervals)

    # Classify based on average interval
    if 25 <= avg_interval <= 35:
        frequency = RecurringPattern.Frequency.MONTHLY
    elif 80 <= avg_interval <= 100:
        frequency = RecurringPattern.Frequency.QUARTERLY
    elif 170 <= avg_interval <= 190:
        frequency = RecurringPattern.Frequency.SEMI_ANNUAL
    elif 350 <= avg_interval <= 380:
        frequency = RecurringPattern.Frequency.ANNUAL
    else:
        frequency = RecurringPattern.Frequency.IRREGULAR

    # Calculate typical day of month
    days = [d.day for d in sorted_dates]
    typical_day = round(mean(days))

    return frequency, typical_day


def calculate_confidence(
    transactions: list[BankTransaction],
    frequency: str,
) -> float:
    """
    Calculate confidence score (0.0-1.0) for a pattern.

    Higher confidence for:
    - More occurrences
    - Consistent timing
    - Consistent amounts
    """
    if len(transactions) < 2:
        return 0.0

    score = 0.0

    # Base score for number of occurrences (max 0.4)
    occurrence_score = min(len(transactions) / 10, 0.4)
    score += occurrence_score

    # Timing consistency (max 0.3)
    dates = sorted([t.entry_date for t in transactions])
    if len(dates) >= 2:
        intervals = [(dates[i] - dates[i - 1]).days for i in range(1, len(dates))]
        if len(intervals) >= 2:
            try:
                interval_stdev = stdev(intervals)
                # Lower stdev = more consistent
                timing_score = max(0, 0.3 - (interval_stdev / 30) * 0.3)
                score += timing_score
            except Exception:
                pass

    # Amount consistency (max 0.3)
    amounts = [float(t.amount) for t in transactions]
    if len(amounts) >= 2:
        try:
            avg_amount = mean(amounts)
            if avg_amount != 0:
                amount_stdev = stdev(amounts)
                # Lower relative stdev = more consistent
                relative_stdev = abs(amount_stdev / avg_amount)
                amount_score = max(0, 0.3 - relative_stdev * 0.3)
                score += amount_score
        except Exception:
            pass

    return min(score, 1.0)


def _get_or_create_counterparty(tenant: Tenant, name: str, iban: str = "") -> Counterparty:
    """Get or create a counterparty by name."""
    if not name:
        name = "(Unknown Pattern)"
    cp, _ = Counterparty.objects.get_or_create(
        tenant=tenant,
        name=name,
        defaults={"iban": iban, "bic": ""},
    )
    return cp


def detect_recurring_patterns(tenant: Tenant) -> list[RecurringPattern]:
    """
    Analyze transactions from the last 18 months and detect recurring patterns.

    Groups transactions by similarity score >= 2 and creates/updates patterns.
    Also detects batch payments (like Sammelüberweisungen) using booking_text patterns.
    Returns list of detected patterns.
    """
    # Get transactions from last 18 months
    cutoff_date = date.today() - timedelta(days=18 * 30)
    transactions = list(
        BankTransaction.objects.filter(
            tenant=tenant,
            entry_date__gte=cutoff_date,
        )
        .select_related("counterparty")
        .order_by("entry_date")
    )

    if not transactions:
        return []

    # Group transactions by counterparty (primary grouping key)
    # For transactions without counterparty name, try to extract pattern from booking_text
    by_group_key: dict[str, tuple[list[BankTransaction], bool, Counterparty | None]] = (
        defaultdict(lambda: ([], False, None))
    )  # (transactions, is_batch_payment, counterparty)

    for txn in transactions:
        counterparty = txn.counterparty
        counterparty_name = counterparty.name.strip() if counterparty else ""
        # Check if booking_text indicates a batch payment (e.g., Sammelüberweisung)
        is_batch = extract_booking_pattern(txn.booking_text) is not None

        if counterparty_name and counterparty_name != "(Bank Fees / Unknown)":
            key = f"counterparty:{counterparty.id}"
            txns, existing_is_batch, _ = by_group_key[key]
            txns.append(txn)
            # Mark as batch payment if ANY transaction in group is a batch payment
            by_group_key[key] = (txns, existing_is_batch or is_batch, counterparty)
        else:
            # No meaningful counterparty - try to extract pattern from booking_text
            pattern_name = extract_booking_pattern(txn.booking_text)
            if pattern_name:
                key = f"booking:{pattern_name.lower()}"
                txns, _, _ = by_group_key[key]
                txns.append(txn)
                by_group_key[key] = (txns, True, None)  # Mark as batch payment

    detected_patterns = []

    for group_key, (txns, is_batch_payment, counterparty) in by_group_key.items():
        if len(txns) < 2:
            continue

        # Further group by amount direction (costs vs income)
        costs = [t for t in txns if t.amount < 0]
        income = [t for t in txns if t.amount > 0]

        for group in [costs, income]:
            if len(group) < 2:
                continue

            # Check pairwise similarity within group
            # Use lenient amount matching for batch payments (payroll varies)
            similarity = calculate_similarity(
                group[0], group[1], lenient_amount=is_batch_payment
            )

            # For batch payments without counterparty, only need timing match (score >= 1)
            # For regular payments, need score >= 2
            min_score = 1 if is_batch_payment else 2
            if similarity.score < min_score:
                continue

            # Detect frequency and confidence
            dates = [t.entry_date for t in group]
            frequency, day_of_month = detect_frequency(dates)
            confidence = calculate_confidence(group, frequency)

            # Calculate average amount
            avg_amount = Decimal(str(mean([float(t.amount) for t in group])))

            # Get or create counterparty for the pattern
            if counterparty:
                pattern_counterparty = counterparty
            else:
                # Use the booking pattern as the counterparty name
                pattern_name = (
                    extract_booking_pattern(group[0].booking_text) or "Unknown Pattern"
                )
                pattern_counterparty = _get_or_create_counterparty(tenant, pattern_name)

            # Check if pattern already exists (same counterparty with same sign of amount)
            existing_qs = RecurringPattern.objects.filter(
                tenant=tenant,
                counterparty=pattern_counterparty,
            )
            if avg_amount > 0:
                existing_qs = existing_qs.filter(average_amount__gt=0)
            else:
                existing_qs = existing_qs.filter(average_amount__lt=0)
            existing = existing_qs.first()

            if existing:
                # Update existing pattern
                existing.average_amount = avg_amount.quantize(Decimal("0.01"))
                existing.frequency = frequency
                existing.day_of_month = day_of_month
                existing.confidence_score = confidence
                existing.last_occurrence = max(dates)
                existing.save()
                existing.source_transactions.set(group)
                detected_patterns.append(existing)
            else:
                # Create new pattern
                pattern = RecurringPattern.objects.create(
                    tenant=tenant,
                    counterparty=pattern_counterparty,
                    average_amount=avg_amount.quantize(Decimal("0.01")),
                    frequency=frequency,
                    day_of_month=day_of_month,
                    confidence_score=confidence,
                    last_occurrence=max(dates),
                )
                pattern.source_transactions.set(group)
                detected_patterns.append(pattern)

    return detected_patterns
