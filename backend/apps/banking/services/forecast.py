"""Service for generating liquidity forecasts from recurring patterns."""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Optional

from dateutil.relativedelta import relativedelta
from django.db.models import Sum

from apps.banking.models import BankAccount, BankTransaction, RecurringPattern
from apps.tenants.models import Tenant


@dataclass
class ProjectedTransaction:
    """A single projected future transaction."""

    pattern_id: int
    counterparty_name: str
    amount: Decimal
    projected_date: date
    is_confirmed: bool


@dataclass
class MonthlyForecast:
    """Forecast data for a single month."""

    month: date  # First day of month
    starting_balance: Decimal
    projected_costs: Decimal
    projected_income: Decimal
    ending_balance: Decimal
    transactions: list[ProjectedTransaction]


def get_current_balance(tenant: Tenant) -> tuple[Decimal, Optional[date]]:
    """
    Get current total balance across all bank accounts.

    Returns (balance, as_of_date) tuple.
    Balance is calculated from the most recent closing_balance per account.
    """
    accounts = BankAccount.objects.filter(tenant=tenant)

    total_balance = Decimal("0.00")
    latest_date = None

    for account in accounts:
        # Get the most recent transaction with a closing balance
        latest_txn = (
            BankTransaction.objects.filter(
                tenant=tenant,
                account=account,
                closing_balance__isnull=False,
            )
            .order_by("-entry_date", "-id")
            .first()
        )

        if latest_txn and latest_txn.closing_balance is not None:
            total_balance += latest_txn.closing_balance
            if latest_date is None or latest_txn.entry_date > latest_date:
                latest_date = latest_txn.entry_date

    return total_balance, latest_date


def project_pattern(pattern: RecurringPattern, months: int = 12) -> list[ProjectedTransaction]:
    """
    Generate projected transactions for a pattern over the next N months.

    Returns list of ProjectedTransaction for each expected occurrence.
    """
    if pattern.is_ignored or pattern.is_paused:
        return []

    # Only project confirmed patterns or high-confidence auto-detected
    if not pattern.is_confirmed and pattern.confidence_score < 0.7:
        return []

    projections = []
    today = date.today()
    day_of_month = pattern.day_of_month or 15  # Default to mid-month

    # Determine interval based on frequency
    if pattern.frequency == RecurringPattern.Frequency.MONTHLY:
        interval_months = 1
    elif pattern.frequency == RecurringPattern.Frequency.QUARTERLY:
        interval_months = 3
    elif pattern.frequency == RecurringPattern.Frequency.SEMI_ANNUAL:
        interval_months = 6
    elif pattern.frequency == RecurringPattern.Frequency.ANNUAL:
        interval_months = 12
    else:
        # Irregular patterns: just project monthly as approximation
        interval_months = 1

    # Find next occurrence date
    current = date(today.year, today.month, min(day_of_month, 28))
    if current <= today:
        current = current + relativedelta(months=1)

    # Project for the specified number of months
    end_date = today + relativedelta(months=months)

    while current <= end_date:
        projections.append(
            ProjectedTransaction(
                pattern_id=pattern.id,
                counterparty_name=pattern.counterparty_name,
                amount=pattern.average_amount,
                projected_date=current,
                is_confirmed=pattern.is_confirmed,
            )
        )
        current = current + relativedelta(months=interval_months)

    return projections


def get_liquidity_forecast(tenant: Tenant, months: int = 12) -> list[MonthlyForecast]:
    """
    Generate a liquidity forecast for the next N months.

    Aggregates current balance with all projected recurring patterns.
    Returns list of MonthlyForecast objects, one per month.
    """
    current_balance, balance_date = get_current_balance(tenant)

    # Get all patterns that should be projected
    patterns = RecurringPattern.objects.filter(
        tenant=tenant,
        is_ignored=False,
        is_paused=False,
    ).filter(
        # Confirmed OR high confidence
        is_confirmed=True,
    ) | RecurringPattern.objects.filter(
        tenant=tenant,
        is_ignored=False,
        is_paused=False,
        is_confirmed=False,
        confidence_score__gte=0.7,
    )

    # Collect all projections
    all_projections: list[ProjectedTransaction] = []
    for pattern in patterns:
        all_projections.extend(project_pattern(pattern, months))

    # Group projections by month
    today = date.today()
    forecasts = []
    running_balance = current_balance

    for i in range(months):
        month_start = date(today.year, today.month, 1) + relativedelta(months=i)
        month_end = month_start + relativedelta(months=1, days=-1)

        # Get projections for this month
        month_txns = [
            p for p in all_projections if month_start <= p.projected_date <= month_end
        ]

        # Calculate totals
        costs = sum(
            (p.amount for p in month_txns if p.amount < 0), Decimal("0.00")
        )
        income = sum(
            (p.amount for p in month_txns if p.amount > 0), Decimal("0.00")
        )
        net = costs + income

        forecasts.append(
            MonthlyForecast(
                month=month_start,
                starting_balance=running_balance,
                projected_costs=costs,
                projected_income=income,
                ending_balance=running_balance + net,
                transactions=month_txns,
            )
        )

        running_balance = running_balance + net

    return forecasts


def get_pattern_next_date(pattern: RecurringPattern) -> Optional[date]:
    """Calculate the next expected occurrence date for a pattern."""
    if pattern.is_ignored or pattern.is_paused:
        return None

    today = date.today()
    day_of_month = pattern.day_of_month or 15

    # Determine interval
    if pattern.frequency == RecurringPattern.Frequency.MONTHLY:
        interval_months = 1
    elif pattern.frequency == RecurringPattern.Frequency.QUARTERLY:
        interval_months = 3
    elif pattern.frequency == RecurringPattern.Frequency.SEMI_ANNUAL:
        interval_months = 6
    elif pattern.frequency == RecurringPattern.Frequency.ANNUAL:
        interval_months = 12
    else:
        interval_months = 1

    # Start from last occurrence if available
    if pattern.last_occurrence:
        next_date = pattern.last_occurrence + relativedelta(months=interval_months)
        # Adjust to typical day
        next_date = date(next_date.year, next_date.month, min(day_of_month, 28))
    else:
        next_date = date(today.year, today.month, min(day_of_month, 28))

    # Ensure it's in the future
    while next_date <= today:
        next_date = next_date + relativedelta(months=interval_months)

    return next_date
