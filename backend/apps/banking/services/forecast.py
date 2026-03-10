"""Service for generating liquidity forecasts from recurring patterns."""
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

from dateutil.relativedelta import relativedelta
from django.db.models import Q, Sum

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
                counterparty_name=pattern.counterparty.name,
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


@dataclass
class LiquidityMonth:
    """Liquidity analysis data for a single month."""

    month: date  # First day of month
    actual_costs: Decimal
    actual_income: Decimal
    projected_costs: Decimal
    projected_income: Decimal
    is_past: bool

    @property
    def total_costs(self) -> Decimal:
        return self.actual_costs + self.projected_costs

    @property
    def total_income(self) -> Decimal:
        return self.actual_income + self.projected_income

    @property
    def net(self) -> Decimal:
        return self.total_income + self.total_costs  # costs are negative


@dataclass
class LiquidityAnalysis:
    """Full liquidity analysis for a year."""

    year: int
    current_balance: Decimal
    balance_as_of: Optional[date]
    months: list[LiquidityMonth]


def _get_avg_monthly_costs(tenant: Tenant, num_months: int = 3) -> Decimal:
    """
    Calculate the average monthly costs from the last N complete months
    of bank transactions (debit amounts only).
    """
    today = date.today()
    # Go back to the 1st of the current month, then N months earlier
    end = date(today.year, today.month, 1) - timedelta(days=1)  # last day of prev month
    start = date(today.year, today.month, 1) - relativedelta(months=num_months)

    result = BankTransaction.objects.filter(
        tenant=tenant,
        entry_date__gte=start,
        entry_date__lte=end,
        amount__lt=0,
    ).aggregate(total=Sum("amount"))

    total = result["total"] or Decimal("0.00")
    if num_months > 0:
        return total / num_months
    return Decimal("0.00")


def get_payment_delay_days(tenant: Tenant) -> int:
    """Get configured payment delay days from tenant settings, default 60."""
    s = tenant.settings or {}
    return int(s.get("payment_delay_days", 60))


def get_liquidity_analysis(
    tenant: Tenant, year: int, payment_delay_days: int | None = None
) -> LiquidityAnalysis:
    """
    Generate a liquidity analysis for a given year.

    Combines:
    - Actual costs/income from bank transactions (past months)
    - Projected costs from average of last months' actual costs
    - Projected income from invoice records (sent/finalized) and billing schedule

    Args:
        tenant: The tenant to analyze
        year: The year to analyze
        payment_delay_days: Days between invoice/send date and expected payment.
            If None, reads from tenant settings (default 60).
    """
    from apps.contracts.models import Contract
    from apps.invoices.models import InvoicePaymentMatch, InvoiceRecord

    if payment_delay_days is None:
        payment_delay_days = get_payment_delay_days(tenant)

    today = date.today()
    current_balance, balance_as_of = get_current_balance(tenant)

    year_start = date(year, 1, 1)
    year_end = date(year, 12, 31)

    # 1. Actual bank transactions for the year (up to today)
    actual_cutoff = min(today, year_end)
    actual_txns = (
        BankTransaction.objects.filter(
            tenant=tenant,
            entry_date__gte=year_start,
            entry_date__lte=actual_cutoff,
        )
        .values("entry_date__month")
        .annotate(
            total_debits=Sum("amount", filter=Q(amount__lt=0)),
            total_credits=Sum("amount", filter=Q(amount__gt=0)),
        )
    )
    actual_by_month: dict[int, dict] = {}
    for row in actual_txns:
        actual_by_month[row["entry_date__month"]] = {
            "costs": row["total_debits"] or Decimal("0.00"),
            "income": row["total_credits"] or Decimal("0.00"),
        }

    # 2. Projected costs: average of last 3 months' actual costs
    avg_monthly_costs = _get_avg_monthly_costs(tenant, num_months=3)

    # 3. Projected income from existing invoice records + future billing schedule
    # 3a. Existing unpaid invoice records (sent or finalized) — use actual dates
    unpaid_invoices = InvoiceRecord.objects.filter(
        tenant=tenant,
        status__in=[InvoiceRecord.Status.FINALIZED, InvoiceRecord.Status.SENT, InvoiceRecord.Status.DUNNING],
        document_type=InvoiceRecord.DocumentType.INVOICE,
    ).exclude(
        total_gross__isnull=True,
    )

    expected_payments_by_month: dict[int, Decimal] = defaultdict(Decimal)
    # Track which contracts+billing_dates have existing invoices to avoid double-counting
    invoiced_events: set[tuple[int, date]] = set()

    for inv in unpaid_invoices:
        # Sent invoices: use sent date + delay; otherwise use invoice date + delay
        if inv.status == InvoiceRecord.Status.SENT and inv.email_sent_at:
            base_date = inv.email_sent_at.date()
        else:
            base_date = inv.invoice_date or inv.billing_date

        payment_date = base_date + timedelta(days=payment_delay_days)
        if year_start <= payment_date <= year_end and payment_date > today:
            expected_payments_by_month[payment_date.month] += inv.total_gross

        # Track this so we don't double-count from billing schedule
        if inv.contract_id and inv.billing_date:
            invoiced_events.add((inv.contract_id, inv.billing_date))

    # 3b. Future billing events from contract schedules (not yet invoiced)
    contracts = (
        Contract.objects.filter(
            tenant=tenant,
            status__in=[Contract.Status.ACTIVE, Contract.Status.PAUSED],
        )
        .exclude(end_date__lt=year_start)
        .prefetch_related("items__product", "items__price_periods", "items__depends_on")
    )

    # Billing events need to start early enough that delayed payments fall in our year
    billing_start = year_start - timedelta(days=payment_delay_days)
    billing_end = year_end - timedelta(days=payment_delay_days)

    for contract in contracts:
        schedule = contract.get_billing_schedule(
            from_date=billing_start,
            to_date=billing_end,
            include_history=True,
        )
        for event in schedule:
            # Skip if an invoice already exists for this billing event
            if (contract.id, event["date"]) in invoiced_events:
                continue
            payment_date = event["date"] + timedelta(days=payment_delay_days)
            if year_start <= payment_date <= year_end and payment_date > today:
                expected_payments_by_month[payment_date.month] += event["total"]

    # 4. Subtract already-paid invoices that were counted in actual bank income
    paid_invoice_amounts_by_month: dict[int, Decimal] = defaultdict(Decimal)
    paid_matches = (
        InvoicePaymentMatch.objects.filter(
            tenant=tenant,
            invoice_record__isnull=False,
        )
        .select_related("invoice_record")
        .filter(
            transaction__entry_date__gte=year_start,
            transaction__entry_date__lte=year_end,
        )
    )
    for match in paid_matches:
        inv = match.invoice_record
        if inv and inv.total_gross:
            # Determine the expected payment month the same way as step 3a
            if inv.email_sent_at:
                base_date = inv.email_sent_at.date()
            else:
                base_date = inv.invoice_date or inv.billing_date
            payment_month_expected = base_date + timedelta(days=payment_delay_days)
            if year_start <= payment_month_expected <= year_end:
                paid_invoice_amounts_by_month[payment_month_expected.month] += inv.total_gross

    # Subtract paid amounts from projected income
    for month_num in expected_payments_by_month:
        expected_payments_by_month[month_num] -= paid_invoice_amounts_by_month.get(
            month_num, Decimal("0.00")
        )
        if expected_payments_by_month[month_num] < 0:
            expected_payments_by_month[month_num] = Decimal("0.00")

    # 5. Build monthly results
    months_data: list[LiquidityMonth] = []
    for m in range(1, 13):
        month_start = date(year, m, 1)
        month_is_past = month_start + relativedelta(months=1) <= today

        actuals = actual_by_month.get(m, {"costs": Decimal("0.00"), "income": Decimal("0.00")})

        # For past months, no projections. For current/future months, use projections.
        if month_is_past:
            proj_costs = Decimal("0.00")
            proj_income = Decimal("0.00")
        else:
            proj_costs = avg_monthly_costs  # negative value
            proj_income = expected_payments_by_month.get(m, Decimal("0.00"))

        months_data.append(
            LiquidityMonth(
                month=month_start,
                actual_costs=actuals["costs"],
                actual_income=actuals["income"],
                projected_costs=proj_costs,
                projected_income=proj_income,
                is_past=month_is_past,
            )
        )

    return LiquidityAnalysis(
        year=year,
        current_balance=current_balance,
        balance_as_of=balance_as_of,
        months=months_data,
    )


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
