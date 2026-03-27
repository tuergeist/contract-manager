"""GraphQL schema for banking (bank accounts and transactions)."""
import re
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

import strawberry
from django.db.models import Count, Max, Min, Q, Sum
from django.db.models.functions import Abs
from strawberry.types import Info

from apps.core.context import Context
from apps.core.permissions import check_perm, require_perm
from apps.core.schema import DeleteResult
from apps.banking.services.forecast import (
    get_current_balance,
    get_liquidity_analysis,
    get_liquidity_forecast,
    get_pattern_next_date,
)
from apps.banking.services.pattern_detection import detect_recurring_patterns


@strawberry.type
class BankAccountType:
    id: int
    name: str
    bank_code: str
    account_number: str
    iban: str
    bic: str
    transaction_count: int


@strawberry.type
class CostCenterType:
    """A cost center (Kostenstelle)."""

    id: strawberry.ID
    code: str
    name: str
    is_active: bool


@strawberry.type
class CounterpartyType:
    """A counterparty entity with UUID identifier."""

    id: strawberry.ID
    name: str
    iban: str
    bic: str
    transaction_count: int
    customer_id: int | None = None
    customer_name: str | None = None
    default_cost_center: CostCenterType | None = None


@strawberry.type
class LinkedCustomerType:
    """Basic customer info for counterparty linking."""

    id: int
    name: str


@strawberry.type
class CounterpartySummaryType:
    """Summary stats for a counterparty (used in detail views)."""

    id: strawberry.ID
    name: str
    iban: str
    bic: str
    total_debit: Decimal
    total_credit: Decimal
    transaction_count: int
    first_date: date | None
    last_date: date | None
    total_invoiced: Decimal = Decimal("0")
    invoice_count: int = 0
    customer: LinkedCustomerType | None = None
    default_cost_center: CostCenterType | None = None


@strawberry.type
class CounterpartyPage:
    items: List[CounterpartySummaryType]
    total_count: int
    page: int
    page_size: int
    has_next_page: bool


@strawberry.type
class InvoiceMatchInfoType:
    """Info about an invoice matched to a transaction."""

    invoice_id: strawberry.ID
    invoice_number: str
    match_type: str
    confidence: Decimal
    contract_id: int | None
    customer_id: int | None
    invoice_type: str = "imported"  # "imported" or "generated"


@strawberry.type
class BankTransactionType:
    id: int
    entry_date: date
    value_date: date | None
    amount: Decimal
    currency: str
    transaction_type: str
    counterparty: CounterpartyType
    booking_text: str
    reference: str
    account_name: str
    cost_center: CostCenterType | None = None
    matched_invoice: InvoiceMatchInfoType | None = None


@strawberry.type
class BankTransactionPage:
    items: List[BankTransactionType]
    total_count: int
    page: int
    page_size: int
    has_next_page: bool


@strawberry.input
class CreateBankAccountInput:
    name: str
    bank_code: str
    account_number: str
    iban: str = ""
    bic: str = ""


@strawberry.input
class UpdateBankAccountInput:
    id: int
    name: str
    iban: str = ""
    bic: str = ""


@strawberry.type
class BankAccountResult:
    success: bool
    error: str | None = None
    account: BankAccountType | None = None


@strawberry.input
class CreateCounterpartyInput:
    name: str
    iban: str = ""
    bic: str = ""


@strawberry.input
class UpdateCounterpartyInput:
    id: strawberry.ID
    name: str | None = None
    iban: str | None = None
    bic: str | None = None
    default_cost_center_id: strawberry.ID | None = strawberry.UNSET


@strawberry.input
class UpdateTransactionCounterpartyInput:
    transaction_id: int
    counterparty_id: strawberry.ID


@strawberry.type
class CounterpartyResult:
    success: bool
    error: str | None = None
    counterparty: CounterpartyType | None = None


@strawberry.input
class CreateCostCenterInput:
    code: str
    name: str
    is_active: bool = True


@strawberry.input
class UpdateCostCenterInput:
    id: strawberry.ID
    code: str | None = None
    name: str | None = None
    is_active: bool | None = None


@strawberry.type
class CostCenterResult:
    success: bool
    error: str | None = None
    cost_center: CostCenterType | None = None


@strawberry.type
class CostCenterSplitAllocationType:
    id: strawberry.ID
    cost_center: CostCenterType
    percentage: Decimal | None = None
    fixed_amount: Decimal | None = None


@strawberry.type
class CostCenterSplitRuleType:
    id: strawberry.ID
    mode: str
    counterparty: CounterpartyType | None = None
    booking_text_pattern: str | None = None
    priority: int
    is_active: bool
    allocations: List[CostCenterSplitAllocationType]


@strawberry.type
class TransactionCostCenterSplitType:
    id: strawberry.ID
    cost_center: CostCenterType
    amount: Decimal
    is_manual: bool
    rule_id: strawberry.ID | None = None


@strawberry.type
class CostCenterSplitRuleResult:
    success: bool
    error: str | None = None
    rule: CostCenterSplitRuleType | None = None


@strawberry.input
class SplitAllocationInput:
    cost_center_id: strawberry.ID
    percentage: Decimal | None = None
    fixed_amount: Decimal | None = None


@strawberry.input
class CreateSplitRuleInput:
    counterparty_id: strawberry.ID | None = None
    booking_text_pattern: str | None = None
    priority: int = 0
    is_active: bool = True
    mode: str = "percentage"
    allocations: List[SplitAllocationInput] = strawberry.field(default_factory=list)


@strawberry.input
class UpdateSplitRuleInput:
    id: strawberry.ID
    counterparty_id: strawberry.ID | None = strawberry.UNSET
    booking_text_pattern: str | None = strawberry.UNSET
    priority: int | None = None
    is_active: bool | None = None
    allocations: List[SplitAllocationInput] | None = None


@strawberry.input
class ManualSplitInput:
    cost_center_id: strawberry.ID
    amount: Decimal


@strawberry.type
class ManualSplitResult:
    success: bool
    error: str | None = None
    splits: List[TransactionCostCenterSplitType] | None = None


@strawberry.type
class CostCenterReportRow:
    cost_center: CostCenterType | None = None
    label: str
    total_amount: Decimal
    transaction_count: int


@strawberry.type
class CostCenterReportType:
    rows: List[CostCenterReportRow]
    date_from: date
    date_to: date


@strawberry.type
class DeleteCostCenterResult:
    success: bool
    error: str | None = None
    in_use: bool = False
    usage_count: int = 0


@strawberry.type
class FteDistributionEntryType:
    id: strawberry.ID
    department_name: str
    cost_center_code: str
    fte_percentage: Decimal
    monthly_income_total: Decimal
    hours_total: Decimal


@strawberry.type
class FteDistributionSnapshotType:
    id: strawberry.ID
    year_month: str
    captured_at: str
    captured_by_name: str | None = None
    entries: List[FteDistributionEntryType] = strawberry.field(default_factory=list)


@strawberry.type
class FteSnapshotResult:
    success: bool
    error: str | None = None
    snapshot: FteDistributionSnapshotType | None = None


@strawberry.type
class MergeCounterpartiesResult:
    success: bool
    error: str | None = None
    target: CounterpartyType | None = None
    merged_transaction_count: int = 0


@strawberry.type
class RecurringPatternType:
    id: int
    counterparty: CounterpartyType
    average_amount: Decimal
    frequency: str
    day_of_month: int | None
    confidence_score: float
    is_confirmed: bool
    is_ignored: bool
    is_paused: bool
    last_occurrence: date | None
    projected_next_date: date | None
    source_transaction_count: int


@strawberry.type
class ProjectedTransactionType:
    pattern_id: int
    counterparty: CounterpartyType
    amount: Decimal
    projected_date: date
    is_confirmed: bool


@strawberry.type
class MonthlyForecastType:
    month: date
    starting_balance: Decimal
    projected_costs: Decimal
    projected_income: Decimal
    ending_balance: Decimal
    transactions: List[ProjectedTransactionType]


@strawberry.type
class LiquidityForecastType:
    current_balance: Decimal
    balance_as_of: date | None
    months: List[MonthlyForecastType]


@strawberry.type
class LiquidityMonthType:
    month: date
    actual_costs: Decimal
    actual_income: Decimal
    projected_costs: Decimal
    projected_income: Decimal
    total_costs: Decimal
    total_income: Decimal
    net: Decimal
    cumulative_balance: Decimal
    is_past: bool


@strawberry.type
class LiquidityAnalysisType:
    year: int
    current_balance: Decimal
    balance_as_of: date | None
    months: List[LiquidityMonthType]


@strawberry.type
class RecurringPatternResult:
    success: bool
    error: str | None = None
    pattern: RecurringPatternType | None = None


@strawberry.type
class DetectPatternsResult:
    success: bool
    error: str | None = None
    detected_count: int = 0


@strawberry.input
class UpdatePatternInput:
    id: int
    amount: Decimal | None = None
    frequency: str | None = None
    day_of_month: int | None = None


# --- Helper functions ---


def _make_cost_center_type(cc) -> CostCenterType | None:
    if cc is None:
        return None
    return CostCenterType(
        id=strawberry.ID(str(cc.id)),
        code=cc.code,
        name=cc.name,
        is_active=cc.is_active,
    )


def _make_split_rule_type(rule) -> CostCenterSplitRuleType:
    """Convert a CostCenterSplitRule model to CostCenterSplitRuleType."""
    allocations = []
    for a in rule.allocations.select_related("cost_center").all():
        allocations.append(CostCenterSplitAllocationType(
            id=strawberry.ID(str(a.id)),
            cost_center=_make_cost_center_type(a.cost_center),
            percentage=a.percentage,
            fixed_amount=a.fixed_amount,
        ))
    cp = getattr(rule, "counterparty", None)
    return CostCenterSplitRuleType(
        id=strawberry.ID(str(rule.id)),
        mode=rule.mode,
        counterparty=_make_counterparty_type(cp) if cp else None,
        booking_text_pattern=rule.booking_text_pattern,
        priority=rule.priority,
        is_active=rule.is_active,
        allocations=allocations,
    )


def _make_split_type(split) -> TransactionCostCenterSplitType:
    return TransactionCostCenterSplitType(
        id=strawberry.ID(str(split.id)),
        cost_center=_make_cost_center_type(split.cost_center),
        amount=split.amount,
        is_manual=split.is_manual,
        rule_id=strawberry.ID(str(split.rule_id)) if split.rule_id else None,
    )


def _make_counterparty_type(cp) -> CounterpartyType:
    """Convert a Counterparty model to CounterpartyType."""
    dcc = getattr(cp, "default_cost_center", None)
    return CounterpartyType(
        id=strawberry.ID(str(cp.id)),
        name=cp.name,
        iban=cp.iban,
        bic=cp.bic,
        transaction_count=getattr(cp, "txn_count", cp.transactions.count()),
        customer_id=cp.customer_id,
        customer_name=cp.customer.name if cp.customer_id and hasattr(cp, "customer") and cp.customer else None,
        default_cost_center=_make_cost_center_type(dcc),
    )


def _make_transaction_type(t, include_invoice_match: bool = True) -> BankTransactionType:
    """Convert a BankTransaction model to BankTransactionType."""
    matched_invoice = None
    if include_invoice_match:
        # Check for invoice matches
        match = getattr(t, "first_invoice_match", None)
        if match is None and hasattr(t, "invoice_matches"):
            match = t.invoice_matches.first()
        if match:
            if match.invoice_id:
                matched_invoice = InvoiceMatchInfoType(
                    invoice_id=strawberry.ID(str(match.invoice_id)),
                    invoice_number=match.invoice.invoice_number or "",
                    match_type=match.match_type,
                    confidence=match.confidence,
                    contract_id=match.invoice.contract_id,
                    customer_id=match.invoice.customer_id,
                    invoice_type="imported",
                )
            elif match.invoice_record_id:
                matched_invoice = InvoiceMatchInfoType(
                    invoice_id=strawberry.ID(str(match.invoice_record_id)),
                    invoice_number=match.invoice_record.invoice_number or "",
                    match_type=match.match_type,
                    confidence=match.confidence,
                    contract_id=match.invoice_record.contract_id,
                    customer_id=match.invoice_record.customer_id,
                    invoice_type="generated",
                )
            elif match.incoming_invoice_id:
                inc = match.incoming_invoice
                matched_invoice = InvoiceMatchInfoType(
                    invoice_id=strawberry.ID(str(inc.id)),
                    invoice_number=inc.invoice_number or inc.original_filename,
                    match_type=match.match_type,
                    confidence=match.confidence,
                    contract_id=None,
                    customer_id=None,
                    invoice_type="incoming",
                )

    return BankTransactionType(
        id=t.id,
        entry_date=t.entry_date,
        value_date=t.value_date,
        amount=t.amount,
        currency=t.currency,
        transaction_type=t.transaction_type,
        counterparty=_make_counterparty_type(t.counterparty),
        booking_text=t.booking_text,
        reference=t.reference,
        account_name=t.account.name,
        cost_center=_make_cost_center_type(getattr(t, "cost_center", None)),
        matched_invoice=matched_invoice,
    )


def _make_pattern_type(pattern) -> RecurringPatternType:
    """Convert a RecurringPattern model to RecurringPatternType."""
    return RecurringPatternType(
        id=pattern.id,
        counterparty=_make_counterparty_type(pattern.counterparty),
        average_amount=pattern.average_amount,
        frequency=pattern.frequency,
        day_of_month=pattern.day_of_month,
        confidence_score=pattern.confidence_score,
        is_confirmed=pattern.is_confirmed,
        is_ignored=pattern.is_ignored,
        is_paused=pattern.is_paused,
        last_occurrence=pattern.last_occurrence,
        projected_next_date=get_pattern_next_date(pattern),
        source_transaction_count=pattern.source_transactions.count(),
    )


@strawberry.type
class MatchDetailType:
    """A single invoice match on a transaction."""

    id: int
    invoice_id: strawberry.ID | None = None
    invoice_record_id: int | None = None
    invoice_number: str
    invoice_amount: Decimal
    customer_name: str
    invoice_type: str  # "imported" or "generated"
    match_type: str
    confidence: Decimal
    matched_at: str


@strawberry.type
class TransactionMatchDetailsType:
    """Full transaction with all its invoice matches and balance info."""

    id: int
    entry_date: date
    value_date: date | None
    amount: Decimal
    currency: str
    counterparty_name: str
    booking_text: str
    reference: str
    account_name: str
    matches: List[MatchDetailType]
    total_matched: Decimal
    difference: Decimal
    customer_id: int | None = None


@strawberry.type
class SuggestedMatchType:
    """An invoice candidate suggested for matching based on counterparty-customer link."""

    id: strawberry.ID
    invoice_number: str
    amount: Decimal
    customer_name: str
    invoice_type: str  # "imported" or "generated"
    status: str
    invoice_date: date | None = None
    is_paid: bool = False
    amount_difference: Decimal = Decimal("0")


@strawberry.type
class SuggestedMatchesResultType:
    """Suggested invoice matches for a transaction."""

    items: List[SuggestedMatchType]
    customer_name: str
    customer_id: int



# --- Incoming Invoice Types ---


@strawberry.type
class InvoiceInboxType:
    id: strawberry.ID
    name: str
    inbox_type: str
    host: str
    port: int
    username: str
    folder: str
    m365_mailbox: str
    is_active: bool
    poll_interval_minutes: int
    last_polled_at: str | None = None
    use_ssl: bool = True


@strawberry.type
class InvoiceInboxResult:
    success: bool
    error: str | None = None
    inbox: InvoiceInboxType | None = None


@strawberry.type
class TestConnectionResult:
    success: bool
    message: str
    email_count: int | None = None


@strawberry.input
class CreateInvoiceInboxInput:
    name: str
    inbox_type: str = "imap"
    host: str = ""
    port: int = 993
    username: str = ""
    password: str = ""
    folder: str = "INBOX"
    use_ssl: bool = True
    m365_mailbox: str = ""
    is_active: bool = True
    poll_interval_minutes: int = 15


@strawberry.input
class UpdateInvoiceInboxInput:
    id: strawberry.ID
    name: str | None = None
    inbox_type: str | None = None
    host: str | None = None
    port: int | None = None
    username: str | None = None
    password: str | None = None
    folder: str | None = None
    use_ssl: bool | None = None
    m365_mailbox: str | None = None
    is_active: bool | None = None
    poll_interval_minutes: int | None = None


@strawberry.type
class IncomingInvoiceType:
    id: strawberry.ID
    supplier_name: str
    invoice_number: str
    invoice_date: date | None
    due_date: date | None
    net_amount: Decimal | None
    vat_amount: Decimal | None
    gross_amount: Decimal | None
    currency: str
    original_filename: str
    file_size: int
    extraction_status: str
    extraction_error: str
    email_message_id: str
    source_email_subject: str
    source_email_date: str | None
    counterparty_id: strawberry.ID | None = None
    counterparty_name: str | None = None
    inbox_name: str | None = None
    pdf_url: str | None = None
    created_at: str = ""


@strawberry.type
class IncomingInvoicePage:
    items: List[IncomingInvoiceType]
    total_count: int
    page: int
    page_size: int
    has_next_page: bool


@strawberry.type
class IncomingInvoiceResult:
    success: bool
    error: str | None = None
    invoice: IncomingInvoiceType | None = None


@strawberry.input
class UpdateIncomingInvoiceInput:
    id: strawberry.ID
    supplier_name: str | None = None
    invoice_number: str | None = None
    invoice_date: date | None = strawberry.UNSET
    due_date: date | None = strawberry.UNSET
    net_amount: Decimal | None = strawberry.UNSET
    vat_amount: Decimal | None = strawberry.UNSET
    gross_amount: Decimal | None = strawberry.UNSET
    currency: str | None = None
    counterparty_id: strawberry.ID | None = strawberry.UNSET
    extraction_status: str | None = None


@strawberry.input
class UploadIncomingInvoiceFileInput:
    file_content: str  # Base64-encoded
    filename: str


@strawberry.type
class UploadIncomingInvoiceItemResult:
    filename: str
    success: bool
    error: str | None = None


@strawberry.type
class UploadIncomingInvoicesResult:
    success: bool
    error: str | None = None
    total_uploaded: int = 0
    total_failed: int = 0
    results: List[UploadIncomingInvoiceItemResult] = strawberry.field(default_factory=list)


def _make_inbox_type(inbox) -> InvoiceInboxType:
    return InvoiceInboxType(
        id=strawberry.ID(str(inbox.id)),
        name=inbox.name,
        inbox_type=inbox.inbox_type,
        host=inbox.host,
        port=inbox.port,
        username=inbox.username,
        folder=inbox.folder,
        m365_mailbox=inbox.m365_mailbox,
        is_active=inbox.is_active,
        poll_interval_minutes=inbox.poll_interval_minutes,
        last_polled_at=inbox.last_polled_at.isoformat() if inbox.last_polled_at else None,
        use_ssl=inbox.use_ssl,
    )


def _make_incoming_invoice_type(inv) -> IncomingInvoiceType:
    return IncomingInvoiceType(
        id=strawberry.ID(str(inv.id)),
        supplier_name=inv.supplier_name,
        invoice_number=inv.invoice_number,
        invoice_date=inv.invoice_date,
        due_date=inv.due_date,
        net_amount=inv.net_amount,
        vat_amount=inv.vat_amount,
        gross_amount=inv.gross_amount,
        currency=inv.currency,
        original_filename=inv.original_filename,
        file_size=inv.file_size,
        extraction_status=inv.extraction_status,
        extraction_error=inv.extraction_error,
        email_message_id=inv.email_message_id,
        source_email_subject=inv.source_email_subject,
        source_email_date=inv.source_email_date.isoformat() if inv.source_email_date else None,
        counterparty_id=strawberry.ID(str(inv.counterparty_id)) if inv.counterparty_id else None,
        counterparty_name=inv.counterparty.name if inv.counterparty_id and inv.counterparty else None,
        inbox_name=inv.inbox.name if inv.inbox_id and inv.inbox else None,
        pdf_url=inv.pdf_file.url if inv.pdf_file else None,
        created_at=inv.created_at.isoformat() if inv.created_at else "",
    )


# --- Queries ---


@strawberry.type
class BankingQuery:
    @strawberry.field
    def cost_centers(
        self, info: Info[Context, None], is_active: bool | None = None,
    ) -> List[CostCenterType]:
        user = require_perm(info, "cost_centers", "read")
        from apps.banking.models import CostCenter
        qs = CostCenter.objects.filter(tenant=user.tenant)
        if is_active is not None:
            qs = qs.filter(is_active=is_active)
        return [_make_cost_center_type(cc) for cc in qs]

    @strawberry.field
    def cost_center_split_rules(
        self,
        info: Info[Context, None],
        counterparty_id: strawberry.ID | None = None,
        is_active: bool | None = None,
    ) -> List[CostCenterSplitRuleType]:
        """List cost center split rules, optionally filtered by counterparty."""
        user = require_perm(info, "cost_centers", "read")
        from apps.banking.models import CostCenterSplitRule

        qs = CostCenterSplitRule.objects.filter(
            tenant=user.tenant
        ).select_related("counterparty", "counterparty__customer", "counterparty__default_cost_center").prefetch_related(
            "allocations__cost_center"
        )
        if counterparty_id is not None:
            qs = qs.filter(counterparty_id=str(counterparty_id))
        if is_active is not None:
            qs = qs.filter(is_active=is_active)
        return [_make_split_rule_type(r) for r in qs]

    @strawberry.field
    def transaction_cost_center_splits(
        self,
        info: Info[Context, None],
        transaction_id: int,
    ) -> List[TransactionCostCenterSplitType]:
        """Get cost center splits for a transaction."""
        user = require_perm(info, "cost_centers", "read")
        from apps.banking.models import TransactionCostCenterSplit

        splits = TransactionCostCenterSplit.objects.filter(
            transaction_id=transaction_id,
            transaction__tenant=user.tenant,
        ).select_related("cost_center")
        return [_make_split_type(s) for s in splits]

    @strawberry.field
    def cost_center_report(
        self,
        info: Info[Context, None],
        date_from: date,
        date_to: date,
    ) -> CostCenterReportType:
        """Aggregate transaction splits by cost center for a date range."""
        user = require_perm(info, "cost_centers", "read")
        from apps.banking.models import BankTransaction, CostCenter, TransactionCostCenterSplit

        # Transactions in range for this tenant
        txn_qs = BankTransaction.objects.filter(
            tenant=user.tenant,
            entry_date__gte=date_from,
            entry_date__lte=date_to,
        )
        txn_ids = set(txn_qs.values_list("id", flat=True))

        # Aggregate splits
        split_agg = (
            TransactionCostCenterSplit.objects.filter(transaction_id__in=txn_ids)
            .values("cost_center_id")
            .annotate(
                total_amount=Sum("amount"),
                transaction_count=Count("transaction_id", distinct=True),
            )
        )

        cc_ids = [row["cost_center_id"] for row in split_agg]
        cc_map = {cc.id: cc for cc in CostCenter.objects.filter(id__in=cc_ids)}

        rows = []
        split_txn_ids = set(
            TransactionCostCenterSplit.objects.filter(transaction_id__in=txn_ids)
            .values_list("transaction_id", flat=True)
        )

        for row in split_agg:
            cc = cc_map.get(row["cost_center_id"])
            rows.append(CostCenterReportRow(
                cost_center=_make_cost_center_type(cc) if cc else None,
                label=f"{cc.code} – {cc.name}" if cc else "Unknown",
                total_amount=row["total_amount"] or Decimal("0"),
                transaction_count=row["transaction_count"],
            ))

        # Unassigned: transactions without any splits
        unassigned_txn_ids = txn_ids - split_txn_ids
        if unassigned_txn_ids:
            unassigned_total = (
                txn_qs.filter(id__in=unassigned_txn_ids).aggregate(
                    total=Sum("amount")
                )["total"]
                or Decimal("0")
            )
            rows.append(CostCenterReportRow(
                cost_center=None,
                label="Unassigned",
                total_amount=unassigned_total,
                transaction_count=len(unassigned_txn_ids),
            ))

        rows.sort(key=lambda r: r.label)
        return CostCenterReportType(rows=rows, date_from=date_from, date_to=date_to)

    @strawberry.field
    def fte_distribution_snapshots(
        self, info: Info[Context, None], year: int | None = None,
    ) -> List[FteDistributionSnapshotType]:
        """List FTE distribution snapshots, optionally filtered by year."""
        user = require_perm(info, "cost_centers", "read")
        from apps.banking.models import FteDistributionSnapshot

        qs = FteDistributionSnapshot.objects.filter(
            tenant=user.tenant
        ).select_related("captured_by").prefetch_related("entries__cost_center")
        if year is not None:
            qs = qs.filter(year_month__startswith=str(year))

        results = []
        for snap in qs:
            entries = [
                FteDistributionEntryType(
                    id=strawberry.ID(str(e.id)),
                    department_name=e.department_name,
                    cost_center_code=e.cost_center_code,
                    fte_percentage=e.fte_percentage,
                    monthly_income_total=e.monthly_income_total,
                    hours_total=e.hours_total,
                )
                for e in snap.entries.all()
            ]
            results.append(FteDistributionSnapshotType(
                id=strawberry.ID(str(snap.id)),
                year_month=snap.year_month,
                captured_at=snap.captured_at.isoformat(),
                captured_by_name=snap.captured_by.get_full_name() if snap.captured_by else None,
                entries=entries,
            ))
        return results

    @strawberry.field
    def transaction_match_details(
        self,
        info: Info[Context, None],
        transaction_id: int,
    ) -> TransactionMatchDetailsType | None:
        """Get a transaction with all its invoice matches and balance totals."""
        user = require_perm(info, "banking", "read")
        from apps.banking.models import BankTransaction

        try:
            txn = (
                BankTransaction.objects.filter(tenant=user.tenant)
                .select_related("account", "counterparty__customer")
                .prefetch_related(
                    "invoice_matches__invoice__customer",
                    "invoice_matches__invoice_record__customer",
                    "invoice_matches__incoming_invoice__counterparty",
                )
                .get(id=transaction_id)
            )
        except BankTransaction.DoesNotExist:
            return None

        matches = []
        total_matched = Decimal("0")
        for m in txn.invoice_matches.all():
            if m.invoice_id:
                inv = m.invoice
                matches.append(MatchDetailType(
                    id=m.id,
                    invoice_id=strawberry.ID(str(inv.id)),
                    invoice_number=inv.invoice_number or "",
                    invoice_amount=inv.total_amount or Decimal("0"),
                    customer_name=inv.customer.name if inv.customer else inv.customer_name or "",
                    invoice_type="imported",
                    match_type=m.match_type,
                    confidence=m.confidence,
                    matched_at=m.matched_at.isoformat() if m.matched_at else "",
                ))
                total_matched += inv.total_amount or Decimal("0")
            elif m.invoice_record_id:
                rec = m.invoice_record
                matches.append(MatchDetailType(
                    id=m.id,
                    invoice_record_id=rec.id,
                    invoice_number=rec.invoice_number or "",
                    invoice_amount=rec.total_gross or Decimal("0"),
                    customer_name=rec.customer.name if rec.customer else "",
                    invoice_type="generated",
                    match_type=m.match_type,
                    confidence=m.confidence,
                    matched_at=m.matched_at.isoformat() if m.matched_at else "",
                ))
                total_matched += rec.total_gross or Decimal("0")
            elif m.incoming_invoice_id:
                inc = m.incoming_invoice
                matches.append(MatchDetailType(
                    id=m.id,
                    invoice_id=strawberry.ID(str(inc.id)),
                    invoice_number=inc.invoice_number or inc.original_filename,
                    invoice_amount=inc.gross_amount or Decimal("0"),
                    customer_name=inc.supplier_name or (inc.counterparty.name if inc.counterparty else ""),
                    invoice_type="incoming",
                    match_type=m.match_type,
                    confidence=m.confidence,
                    matched_at=m.matched_at.isoformat() if m.matched_at else "",
                ))
                total_matched += inc.gross_amount or Decimal("0")

        return TransactionMatchDetailsType(
            id=txn.id,
            entry_date=txn.entry_date,
            value_date=txn.value_date,
            amount=txn.amount,
            currency=txn.currency,
            counterparty_name=txn.counterparty.name if txn.counterparty else "",
            booking_text=txn.booking_text,
            reference=txn.reference,
            account_name=txn.account.name,
            matches=matches,
            total_matched=total_matched,
            difference=abs(txn.amount) - total_matched,
            customer_id=txn.counterparty.customer_id if txn.counterparty else None,
        )

    @strawberry.field
    def suggested_invoice_matches(
        self,
        info: Info[Context, None],
        transaction_id: int,
    ) -> SuggestedMatchesResultType | None:
        """Suggest invoice candidates based on counterparty link.

        For credit transactions (amount > 0): suggest outgoing invoices (ImportedInvoice, InvoiceRecord)
        matched via counterparty → customer link.

        For debit transactions (amount < 0): suggest incoming invoices (IncomingInvoice)
        matched via counterparty link, plus our credit notes (storno).
        """
        user = require_perm(info, "banking", "read")
        from apps.banking.models import BankTransaction, IncomingInvoice
        from apps.invoices.models import ImportedInvoice, InvoiceRecord, InvoicePaymentMatch

        try:
            txn = (
                BankTransaction.objects.filter(tenant=user.tenant)
                .select_related("counterparty__customer")
                .get(id=transaction_id)
            )
        except BankTransaction.DoesNotExist:
            return None

        if not txn.counterparty:
            return None

        txn_amount = abs(txn.amount)
        is_debit = txn.amount < 0
        counterparty = txn.counterparty
        candidates: list[SuggestedMatchType] = []

        # Already matched IDs
        matched_imported_ids = set(
            InvoicePaymentMatch.objects.filter(
                transaction=txn, invoice__isnull=False
            ).values_list("invoice_id", flat=True)
        )
        matched_record_ids = set(
            InvoicePaymentMatch.objects.filter(
                transaction=txn, invoice_record__isnull=False
            ).values_list("invoice_record_id", flat=True)
        )
        matched_incoming_ids = set(
            InvoicePaymentMatch.objects.filter(
                transaction=txn, incoming_invoice__isnull=False
            ).values_list("incoming_invoice_id", flat=True)
        )

        if is_debit:
            # --- Debit: suggest incoming invoices (supplier) matched via counterparty ---
            incoming_qs = IncomingInvoice.objects.filter(
                tenant=user.tenant,
                counterparty=counterparty,
                extraction_status__in=["extracted", "confirmed", "matched"],
            ).filter(
                Q(invoice_date__lte=txn.entry_date) | Q(invoice_date__isnull=True)
            ).exclude(id__in=matched_incoming_ids)

            for inv in incoming_qs:
                amt = inv.gross_amount or Decimal("0")
                candidates.append(SuggestedMatchType(
                    id=strawberry.ID(str(inv.id)),
                    invoice_number=inv.invoice_number or inv.original_filename,
                    amount=amt,
                    customer_name=inv.supplier_name or counterparty.name,
                    invoice_type="incoming",
                    status=inv.extraction_status,
                    invoice_date=inv.invoice_date,
                    is_paid=inv.payment_matches.exists(),
                    amount_difference=amt - txn_amount,
                ))

            # Also suggest our credit notes (storno) if counterparty is linked to a customer
            if counterparty.customer_id:
                storno_qs = InvoiceRecord.objects.filter(
                    tenant=user.tenant,
                    customer_id=counterparty.customer_id,
                    document_type="storno",
                ).exclude(
                    status="voided"
                ).filter(
                    Q(invoice_date__lte=txn.entry_date) | Q(invoice_date__isnull=True)
                ).exclude(id__in=matched_record_ids)

                for rec in storno_qs:
                    amt = rec.total_gross or Decimal("0")
                    candidates.append(SuggestedMatchType(
                        id=strawberry.ID(str(rec.id)),
                        invoice_number=rec.invoice_number or "",
                        amount=amt,
                        customer_name=rec.customer.name if rec.customer else "",
                        invoice_type="generated",
                        status=rec.status,
                        invoice_date=rec.invoice_date,
                        is_paid=False,
                        amount_difference=amt - txn_amount,
                    ))

            counterparty_label = counterparty.name
            counterparty_id = counterparty.customer_id or 0
        else:
            # --- Credit: suggest outgoing invoices matched via counterparty → customer ---
            if not counterparty.customer_id:
                return None

            customer = counterparty.customer
            counterparty_label = customer.name
            counterparty_id = customer.id

            # Imported invoices
            imported_qs = ImportedInvoice.objects.filter(
                tenant=user.tenant,
                customer=customer,
                extraction_status__in=["confirmed", "sent"],
            ).filter(
                Q(invoice_date__lte=txn.entry_date) | Q(invoice_date__isnull=True)
            ).exclude(id__in=matched_imported_ids)

            for inv in imported_qs:
                amt = inv.total_amount or Decimal("0")
                candidates.append(SuggestedMatchType(
                    id=strawberry.ID(str(inv.id)),
                    invoice_number=inv.invoice_number or "",
                    amount=amt,
                    customer_name=customer.name,
                    invoice_type="imported",
                    status=inv.extraction_status,
                    invoice_date=inv.invoice_date,
                    is_paid=False,
                    amount_difference=amt - txn_amount,
                ))

            # Generated invoice records (exclude voided, paid, and credit notes)
            record_qs = InvoiceRecord.objects.filter(
                tenant=user.tenant,
                customer=customer,
            ).exclude(
                status__in=["voided", "paid"]
            ).exclude(
                document_type="storno"
            ).filter(
                Q(invoice_date__lte=txn.entry_date) | Q(invoice_date__isnull=True)
            ).exclude(id__in=matched_record_ids)

            for rec in record_qs:
                amt = rec.total_gross or Decimal("0")
                candidates.append(SuggestedMatchType(
                    id=strawberry.ID(str(rec.id)),
                    invoice_number=rec.invoice_number or "",
                    amount=amt,
                    customer_name=customer.name,
                    invoice_type="generated",
                    status=rec.status,
                    invoice_date=rec.invoice_date,
                    is_paid=False,
                    amount_difference=amt - txn_amount,
                ))

        # Sort by amount proximity, cap at 20
        candidates.sort(key=lambda c: abs(c.amount_difference))
        candidates = candidates[:20]

        return SuggestedMatchesResultType(
            items=candidates,
            customer_name=counterparty_label,
            customer_id=counterparty_id,
        )

    @strawberry.field
    def bank_accounts(self, info: Info[Context, None]) -> List[BankAccountType]:
        user = require_perm(info, "banking", "read")
        from apps.banking.models import BankAccount

        accounts = (
            BankAccount.objects.filter(tenant=user.tenant)
            .annotate(txn_count=Count("transactions"))
            .order_by("name")
        )
        return [
            BankAccountType(
                id=a.id,
                name=a.name,
                bank_code=a.bank_code,
                account_number=a.account_number,
                iban=a.iban,
                bic=a.bic,
                transaction_count=a.txn_count,
            )
            for a in accounts
        ]

    @strawberry.field
    def bank_transactions(
        self,
        info: Info[Context, None],
        account_id: int | None = None,
        search: str | None = None,
        counterparty_id: strawberry.ID | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        amount_min: Decimal | None = None,
        amount_max: Decimal | None = None,
        direction: str | None = None,
        cost_center_id: strawberry.ID | None = None,
        unmatched_credits_only: bool = False,
        sort_by: str | None = None,
        sort_order: str | None = None,
        page: int = 1,
        page_size: int = 50,
        center_on_id: int | None = None,
    ) -> BankTransactionPage:
        user = require_perm(info, "banking", "read")
        from apps.banking.models import BankTransaction

        qs = BankTransaction.objects.filter(
            tenant=user.tenant
        ).select_related("account", "counterparty", "counterparty__customer", "counterparty__default_cost_center", "cost_center").prefetch_related(
            "invoice_matches__invoice",
            "invoice_matches__invoice_record",
            "invoice_matches__incoming_invoice",
        )

        # Filters
        if account_id:
            qs = qs.filter(account_id=account_id)
        if counterparty_id is not None:
            qs = qs.filter(counterparty_id=str(counterparty_id))
        if search:
            q = Q(counterparty__name__icontains=search) | Q(booking_text__icontains=search)
            # Also match by amount if the search term looks numeric
            try:
                amount_val = Decimal(search.replace(",", ".").strip())
                q = q | Q(amount=amount_val) | Q(amount=-amount_val)
            except Exception:
                pass
            qs = qs.filter(q)
        if date_from:
            qs = qs.filter(entry_date__gte=date_from)
        if date_to:
            qs = qs.filter(entry_date__lte=date_to)
        if amount_min is not None:
            qs = qs.filter(
                Q(amount__gte=amount_min) | Q(amount__lte=-amount_min)
            )
        if amount_max is not None:
            qs = qs.filter(
                Q(amount__lte=amount_max) & Q(amount__gte=-amount_max)
            )
        if cost_center_id is not None:
            qs = qs.filter(cost_center_id=str(cost_center_id))
        if direction == "debit":
            qs = qs.filter(amount__lt=0)
        elif direction == "credit":
            qs = qs.filter(amount__gt=0)

        # Filter for unmatched credits (incoming payments without invoice match)
        if unmatched_credits_only:
            qs = qs.filter(amount__gt=0).exclude(invoice_matches__isnull=False)

        # Sorting
        sort_field = "entry_date"
        if sort_by in ("date", "entry_date"):
            sort_field = "entry_date"
        elif sort_by == "amount":
            sort_field = "amount"
        elif sort_by in ("counterparty", "counterparty_name"):
            sort_field = "counterparty__name"

        if sort_order == "asc":
            qs = qs.order_by(sort_field, "id")
        else:
            qs = qs.order_by(f"-{sort_field}", "-id")

        total_count = qs.count()

        # If centering on a specific transaction, find its position and adjust page
        if center_on_id is not None:
            # Get list of IDs in sort order to find position
            all_ids = list(qs.values_list("id", flat=True))
            try:
                position = all_ids.index(center_on_id)
                # Calculate page that contains this transaction (centered)
                # Put the target transaction roughly in the middle of the page
                offset = max(0, position - page_size // 2)
                # Align to page boundary for cleaner pagination
                page = (offset // page_size) + 1
                offset = (page - 1) * page_size
            except ValueError:
                # Transaction not found, use default pagination
                offset = (page - 1) * page_size
        else:
            offset = (page - 1) * page_size

        items = list(qs[offset : offset + page_size])

        return BankTransactionPage(
            items=[_make_transaction_type(t) for t in items],
            total_count=total_count,
            page=page,
            page_size=page_size,
            has_next_page=(offset + page_size) < total_count,
        )

    @strawberry.field
    def counterparty(
        self,
        info: Info[Context, None],
        id: strawberry.ID,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> CounterpartySummaryType | None:
        """Get a single counterparty by ID with summary stats."""
        user = require_perm(info, "banking", "read")
        from apps.banking.models import Counterparty

        txn_date_filter = Q()
        if date_from:
            txn_date_filter &= Q(transactions__entry_date__gte=date_from)
        if date_to:
            txn_date_filter &= Q(transactions__entry_date__lte=date_to)

        try:
            cp = (
                Counterparty.objects.filter(tenant=user.tenant, id=str(id))
                .select_related("customer", "default_cost_center")
                .annotate(
                    total_debit=Sum(
                        "transactions__amount",
                        filter=Q(transactions__amount__lt=0) & txn_date_filter,
                        default=Decimal("0"),
                    ),
                    total_credit=Sum(
                        "transactions__amount",
                        filter=Q(transactions__amount__gt=0) & txn_date_filter,
                        default=Decimal("0"),
                    ),
                    txn_count=Count("transactions", filter=txn_date_filter),
                    first_date=Min("transactions__entry_date", filter=txn_date_filter),
                    last_date=Max("transactions__entry_date", filter=txn_date_filter),
                )
                .get()
            )
        except Counterparty.DoesNotExist:
            return None

        # Aggregate incoming invoices for this counterparty
        from apps.banking.models import IncomingInvoice
        inv_filter = Q(counterparty=cp)
        if date_from:
            inv_filter &= Q(invoice_date__gte=date_from)
        if date_to:
            inv_filter &= Q(invoice_date__lte=date_to)
        inv_agg = IncomingInvoice.objects.filter(
            inv_filter, tenant=user.tenant,
        ).aggregate(
            total=Sum("gross_amount", default=Decimal("0")),
            count=Count("id"),
        )

        return CounterpartySummaryType(
            id=strawberry.ID(str(cp.id)),
            name=cp.name,
            iban=cp.iban,
            bic=cp.bic,
            total_debit=cp.total_debit,
            total_credit=cp.total_credit,
            transaction_count=cp.txn_count,
            first_date=cp.first_date,
            last_date=cp.last_date,
            total_invoiced=inv_agg["total"],
            invoice_count=inv_agg["count"],
            customer=LinkedCustomerType(id=cp.customer.id, name=cp.customer.name) if cp.customer else None,
            default_cost_center=_make_cost_center_type(cp.default_cost_center),
        )

    @strawberry.field
    def counterparties(
        self,
        info: Info[Context, None],
        search: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        sort_by: str | None = None,
        sort_order: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> CounterpartyPage:
        """List all counterparties with summary stats."""
        user = require_perm(info, "banking", "read")
        from apps.banking.models import Counterparty

        txn_date_filter = Q()
        if date_from:
            txn_date_filter &= Q(transactions__entry_date__gte=date_from)
        if date_to:
            txn_date_filter &= Q(transactions__entry_date__lte=date_to)

        qs = (
            Counterparty.objects.filter(tenant=user.tenant)
            .select_related("default_cost_center")
            .annotate(
                total_debit=Sum(
                    "transactions__amount",
                    filter=Q(transactions__amount__lt=0) & txn_date_filter,
                    default=Decimal("0"),
                ),
                total_credit=Sum(
                    "transactions__amount",
                    filter=Q(transactions__amount__gt=0) & txn_date_filter,
                    default=Decimal("0"),
                ),
                txn_count=Count("transactions", filter=txn_date_filter),
                first_date=Min("transactions__entry_date", filter=txn_date_filter),
                last_date=Max("transactions__entry_date", filter=txn_date_filter),
                abs_total=Abs(Sum("transactions__amount", filter=txn_date_filter, default=Decimal("0"))),
            )
        )

        if search:
            qs = qs.filter(name__icontains=search)

        # Sorting
        sort_field = "-abs_total"
        if sort_by == "name":
            sort_field = "name"
        elif sort_by == "totalAmount":
            sort_field = "abs_total"
        elif sort_by == "transactionCount":
            sort_field = "txn_count"
        elif sort_by == "lastDate":
            sort_field = "last_date"

        if sort_order == "asc":
            if sort_field.startswith("-"):
                sort_field = sort_field[1:]
        else:
            if not sort_field.startswith("-"):
                sort_field = f"-{sort_field}"

        qs = qs.order_by(sort_field, "name")

        total_count = qs.count()
        offset = (page - 1) * page_size
        items = qs[offset : offset + page_size]

        return CounterpartyPage(
            items=[
                CounterpartySummaryType(
                    id=strawberry.ID(str(cp.id)),
                    name=cp.name,
                    iban=cp.iban,
                    bic=cp.bic,
                    total_debit=cp.total_debit,
                    total_credit=cp.total_credit,
                    transaction_count=cp.txn_count,
                    first_date=cp.first_date,
                    last_date=cp.last_date,
                    default_cost_center=_make_cost_center_type(getattr(cp, "default_cost_center", None)),
                )
                for cp in items
            ],
            total_count=total_count,
            page=page,
            page_size=page_size,
            has_next_page=(offset + page_size) < total_count,
        )

    @strawberry.field
    def recurring_patterns(
        self,
        info: Info[Context, None],
        include_confirmed: bool = True,
        include_unconfirmed: bool = True,
        include_ignored: bool = False,
    ) -> List[RecurringPatternType]:
        user = require_perm(info, "banking", "read")
        from apps.banking.models import RecurringPattern

        qs = RecurringPattern.objects.filter(tenant=user.tenant).select_related(
            "counterparty"
        )

        if not include_ignored:
            qs = qs.filter(is_ignored=False)

        filters = Q()
        if include_confirmed and not include_unconfirmed:
            filters = Q(is_confirmed=True)
        elif include_unconfirmed and not include_confirmed:
            filters = Q(is_confirmed=False)

        if filters:
            qs = qs.filter(filters)

        patterns = qs.order_by("-confidence_score", "-last_occurrence")

        return [_make_pattern_type(p) for p in patterns]

    @strawberry.field
    def liquidity_forecast(
        self,
        info: Info[Context, None],
        months: int = 12,
    ) -> LiquidityForecastType:
        user = require_perm(info, "banking", "read")
        from apps.banking.models import RecurringPattern

        current_balance, balance_date = get_current_balance(user.tenant)
        forecast = get_liquidity_forecast(user.tenant, months)

        # Build a cache of counterparties for the patterns
        pattern_ids = set()
        for m in forecast:
            for t in m.transactions:
                pattern_ids.add(t.pattern_id)

        patterns = RecurringPattern.objects.filter(id__in=pattern_ids).select_related(
            "counterparty"
        )
        pattern_map = {p.id: p for p in patterns}

        return LiquidityForecastType(
            current_balance=current_balance,
            balance_as_of=balance_date,
            months=[
                MonthlyForecastType(
                    month=m.month,
                    starting_balance=m.starting_balance,
                    projected_costs=m.projected_costs,
                    projected_income=m.projected_income,
                    ending_balance=m.ending_balance,
                    transactions=[
                        ProjectedTransactionType(
                            pattern_id=t.pattern_id,
                            counterparty=_make_counterparty_type(
                                pattern_map[t.pattern_id].counterparty
                            ),
                            amount=t.amount,
                            projected_date=t.projected_date,
                            is_confirmed=t.is_confirmed,
                        )
                        for t in m.transactions
                        if t.pattern_id in pattern_map
                    ],
                )
                for m in forecast
            ],
        )

    @strawberry.field
    def liquidity_analysis(
        self,
        info: Info[Context, None],
        year: int,
    ) -> LiquidityAnalysisType:
        user = require_perm(info, "banking", "read")
        analysis = get_liquidity_analysis(user.tenant, year)

        # Compute cumulative balance
        running = analysis.current_balance
        month_types = []
        for m in analysis.months:
            running += m.net
            month_types.append(
                LiquidityMonthType(
                    month=m.month,
                    actual_costs=m.actual_costs,
                    actual_income=m.actual_income,
                    projected_costs=m.projected_costs,
                    projected_income=m.projected_income,
                    total_costs=m.total_costs,
                    total_income=m.total_income,
                    net=m.net,
                    cumulative_balance=running,
                    is_past=m.is_past,
                )
            )

        return LiquidityAnalysisType(
            year=analysis.year,
            current_balance=analysis.current_balance,
            balance_as_of=analysis.balance_as_of,
            months=month_types,
        )



    # --- Incoming Invoice Queries ---

    @strawberry.field
    def invoice_inboxes(self, info: Info[Context, None]) -> List[InvoiceInboxType]:
        user = require_perm(info, "incoming_invoices", "config")
        from apps.banking.models import InvoiceInbox
        return [_make_inbox_type(i) for i in InvoiceInbox.objects.filter(tenant=user.tenant).order_by("name")]

    @strawberry.field
    def incoming_invoices(self, info: Info[Context, None], status: str | None = None, counterparty_id: strawberry.ID | None = None, inbox_id: strawberry.ID | None = None, date_from: date | None = None, date_to: date | None = None, search: str | None = None, sort_by: str | None = None, sort_order: str | None = None, page: int = 1, page_size: int = 50) -> IncomingInvoicePage:
        user = require_perm(info, "incoming_invoices", "read")
        from apps.banking.models import IncomingInvoice
        qs = IncomingInvoice.objects.filter(tenant=user.tenant).select_related("counterparty", "inbox")
        if status: qs = qs.filter(extraction_status=status)
        if inbox_id is not None: qs = qs.filter(inbox_id=str(inbox_id))
        if counterparty_id is not None: qs = qs.filter(counterparty_id=str(counterparty_id))
        if date_from: qs = qs.filter(invoice_date__gte=date_from)
        if date_to: qs = qs.filter(invoice_date__lte=date_to)
        if search: qs = qs.filter(Q(supplier_name__icontains=search) | Q(invoice_number__icontains=search) | Q(source_email_subject__icontains=search))
        # Sorting
        sort_map = {
            "invoice_date": "invoice_date",
            "supplier_name": "supplier_name",
            "invoice_number": "invoice_number",
            "gross_amount": "gross_amount",
            "extraction_status": "extraction_status",
            "created_at": "created_at",
        }
        order_field = sort_map.get(sort_by or "", "created_at")
        if (sort_order or "desc") == "asc":
            qs = qs.order_by(order_field)
        else:
            qs = qs.order_by(f"-{order_field}")
        total_count = qs.count()
        offset = (page - 1) * page_size
        items = list(qs[offset:offset + page_size])
        return IncomingInvoicePage(items=[_make_incoming_invoice_type(inv) for inv in items], total_count=total_count, page=page, page_size=page_size, has_next_page=(offset + page_size) < total_count)

    @strawberry.field
    def incoming_invoice(self, info: Info[Context, None], id: strawberry.ID) -> IncomingInvoiceType | None:
        user = require_perm(info, "incoming_invoices", "read")
        from apps.banking.models import IncomingInvoice
        try:
            inv = IncomingInvoice.objects.filter(tenant=user.tenant).select_related("counterparty", "inbox").get(id=str(id))
        except IncomingInvoice.DoesNotExist:
            return None
        return _make_incoming_invoice_type(inv)


# --- Mutations ---


@strawberry.type
class BankingMutation:
    @strawberry.mutation
    def create_bank_account(
        self, info: Info[Context, None], input: CreateBankAccountInput
    ) -> BankAccountResult:
        user, err = check_perm(info, "banking", "write")
        if err:
            return BankAccountResult(success=False, error=err)

        from apps.banking.models import BankAccount

        # Check for duplicate
        if BankAccount.objects.filter(
            tenant=user.tenant,
            bank_code=input.bank_code,
            account_number=input.account_number,
        ).exists():
            return BankAccountResult(
                success=False,
                error="An account with this bank code and account number already exists.",
            )

        account = BankAccount.objects.create(
            tenant=user.tenant,
            name=input.name,
            bank_code=input.bank_code,
            account_number=input.account_number,
            iban=input.iban,
            bic=input.bic,
        )
        return BankAccountResult(
            success=True,
            account=BankAccountType(
                id=account.id,
                name=account.name,
                bank_code=account.bank_code,
                account_number=account.account_number,
                iban=account.iban,
                bic=account.bic,
                transaction_count=0,
            ),
        )

    @strawberry.mutation
    def update_bank_account(
        self, info: Info[Context, None], input: UpdateBankAccountInput
    ) -> BankAccountResult:
        user, err = check_perm(info, "banking", "write")
        if err:
            return BankAccountResult(success=False, error=err)

        from apps.banking.models import BankAccount

        try:
            account = BankAccount.objects.get(
                id=input.id, tenant=user.tenant
            )
        except BankAccount.DoesNotExist:
            return BankAccountResult(success=False, error="Account not found.")

        account.name = input.name
        account.iban = input.iban
        account.bic = input.bic
        account.save(update_fields=["name", "iban", "bic", "updated_at"])

        txn_count = account.transactions.count()
        return BankAccountResult(
            success=True,
            account=BankAccountType(
                id=account.id,
                name=account.name,
                bank_code=account.bank_code,
                account_number=account.account_number,
                iban=account.iban,
                bic=account.bic,
                transaction_count=txn_count,
            ),
        )

    @strawberry.mutation
    def delete_bank_account(
        self, info: Info[Context, None], id: int
    ) -> DeleteResult:
        user, err = check_perm(info, "banking", "write")
        if err:
            return DeleteResult(success=False, error=err)

        from apps.banking.models import BankAccount

        try:
            account = BankAccount.objects.get(id=id, tenant=user.tenant)
        except BankAccount.DoesNotExist:
            return DeleteResult(success=False, error="Account not found.")

        account.delete()
        return DeleteResult(success=True)

    @strawberry.mutation
    def create_counterparty(
        self, info: Info[Context, None], input: CreateCounterpartyInput
    ) -> CounterpartyResult:
        """Create a new counterparty."""
        user, err = check_perm(info, "banking", "write")
        if err:
            return CounterpartyResult(success=False, error=err)

        from apps.banking.models import Counterparty

        name = input.name.strip()
        if not name:
            return CounterpartyResult(success=False, error="Name is required.")

        # Check for duplicate name
        if Counterparty.objects.filter(tenant=user.tenant, name=name).exists():
            return CounterpartyResult(
                success=False,
                error="A counterparty with this name already exists.",
            )

        cp = Counterparty.objects.create(
            tenant=user.tenant,
            name=name,
            iban=input.iban.strip(),
            bic=input.bic.strip(),
        )

        return CounterpartyResult(
            success=True,
            counterparty=_make_counterparty_type(cp),
        )

    @strawberry.mutation
    def update_transaction_counterparty(
        self, info: Info[Context, None], input: UpdateTransactionCounterpartyInput
    ) -> DeleteResult:
        """Update a transaction's counterparty."""
        user, err = check_perm(info, "banking", "write")
        if err:
            return DeleteResult(success=False, error=err)

        from apps.banking.models import BankTransaction, Counterparty

        try:
            txn = BankTransaction.objects.get(id=input.transaction_id, tenant=user.tenant)
        except BankTransaction.DoesNotExist:
            return DeleteResult(success=False, error="Transaction not found.")

        try:
            cp = Counterparty.objects.get(id=str(input.counterparty_id), tenant=user.tenant)
        except Counterparty.DoesNotExist:
            return DeleteResult(success=False, error="Counterparty not found.")

        txn.counterparty = cp
        txn.save(update_fields=["counterparty", "updated_at"])

        return DeleteResult(success=True)

    @strawberry.mutation
    def update_counterparty(
        self, info: Info[Context, None], input: UpdateCounterpartyInput
    ) -> CounterpartyResult:
        """Update a counterparty's name, IBAN, or BIC."""
        user, err = check_perm(info, "banking", "write")
        if err:
            return CounterpartyResult(success=False, error=err)

        from apps.banking.models import Counterparty

        try:
            cp = Counterparty.objects.get(id=str(input.id), tenant=user.tenant)
        except Counterparty.DoesNotExist:
            return CounterpartyResult(success=False, error="Counterparty not found.")

        update_fields = ["updated_at"]

        if input.name is not None:
            # Check for duplicate name
            if (
                Counterparty.objects.filter(tenant=user.tenant, name=input.name)
                .exclude(id=cp.id)
                .exists()
            ):
                return CounterpartyResult(
                    success=False,
                    error="A counterparty with this name already exists.",
                )
            cp.name = input.name
            update_fields.append("name")

        if input.iban is not None:
            cp.iban = input.iban
            update_fields.append("iban")

        if input.bic is not None:
            cp.bic = input.bic
            update_fields.append("bic")

        if input.default_cost_center_id is not strawberry.UNSET:
            if input.default_cost_center_id is None:
                cp.default_cost_center = None
            else:
                from apps.banking.models import CostCenter as CostCenterModel
                try:
                    cc = CostCenterModel.objects.get(id=str(input.default_cost_center_id), tenant=user.tenant)
                    cp.default_cost_center = cc
                except CostCenterModel.DoesNotExist:
                    return CounterpartyResult(success=False, error="Cost center not found.")
            update_fields.append("default_cost_center")

        cp.save(update_fields=update_fields)
        cp = Counterparty.objects.select_related("customer", "default_cost_center").get(id=cp.id)

        return CounterpartyResult(
            success=True,
            counterparty=_make_counterparty_type(cp),
        )

    @strawberry.mutation
    def merge_counterparties(
        self,
        info: Info[Context, None],
        source_id: strawberry.ID,
        target_id: strawberry.ID,
    ) -> MergeCounterpartiesResult:
        """Merge source counterparty into target. All transactions move to target."""
        user, err = check_perm(info, "banking", "write")
        if err:
            return MergeCounterpartiesResult(success=False, error=err)

        from apps.banking.models import Counterparty, BankTransaction, RecurringPattern

        if str(source_id) == str(target_id):
            return MergeCounterpartiesResult(
                success=False, error="Cannot merge a counterparty into itself."
            )

        try:
            source = Counterparty.objects.get(id=str(source_id), tenant=user.tenant)
            target = Counterparty.objects.get(id=str(target_id), tenant=user.tenant)
        except Counterparty.DoesNotExist:
            return MergeCounterpartiesResult(
                success=False, error="Counterparty not found."
            )

        # Move all transactions from source to target
        txn_count = BankTransaction.objects.filter(counterparty=source).update(
            counterparty=target
        )

        # Move all patterns from source to target
        RecurringPattern.objects.filter(counterparty=source).update(counterparty=target)

        # Delete source
        source.delete()

        return MergeCounterpartiesResult(
            success=True,
            target=_make_counterparty_type(target),
            merged_transaction_count=txn_count,
        )

    @strawberry.mutation
    def detect_patterns(self, info: Info[Context, None]) -> DetectPatternsResult:
        user, err = check_perm(info, "banking", "write")
        if err:
            return DetectPatternsResult(success=False, error=err)

        patterns = detect_recurring_patterns(user.tenant)
        return DetectPatternsResult(success=True, detected_count=len(patterns))

    @strawberry.mutation
    def confirm_pattern(
        self, info: Info[Context, None], pattern_id: int
    ) -> RecurringPatternResult:
        user, err = check_perm(info, "banking", "write")
        if err:
            return RecurringPatternResult(success=False, error=err)

        from apps.banking.models import RecurringPattern

        try:
            pattern = RecurringPattern.objects.select_related("counterparty").get(
                id=pattern_id, tenant=user.tenant
            )
        except RecurringPattern.DoesNotExist:
            return RecurringPatternResult(success=False, error="Pattern not found.")

        pattern.is_confirmed = True
        pattern.save(update_fields=["is_confirmed", "updated_at"])

        return RecurringPatternResult(success=True, pattern=_make_pattern_type(pattern))

    @strawberry.mutation
    def ignore_pattern(
        self, info: Info[Context, None], pattern_id: int
    ) -> RecurringPatternResult:
        user, err = check_perm(info, "banking", "write")
        if err:
            return RecurringPatternResult(success=False, error=err)

        from apps.banking.models import RecurringPattern

        try:
            pattern = RecurringPattern.objects.select_related("counterparty").get(
                id=pattern_id, tenant=user.tenant
            )
        except RecurringPattern.DoesNotExist:
            return RecurringPatternResult(success=False, error="Pattern not found.")

        pattern.is_ignored = True
        pattern.save(update_fields=["is_ignored", "updated_at"])

        return RecurringPatternResult(success=True, pattern=_make_pattern_type(pattern))

    @strawberry.mutation
    def restore_pattern(
        self, info: Info[Context, None], pattern_id: int
    ) -> RecurringPatternResult:
        user, err = check_perm(info, "banking", "write")
        if err:
            return RecurringPatternResult(success=False, error=err)

        from apps.banking.models import RecurringPattern

        try:
            pattern = RecurringPattern.objects.select_related("counterparty").get(
                id=pattern_id, tenant=user.tenant
            )
        except RecurringPattern.DoesNotExist:
            return RecurringPatternResult(success=False, error="Pattern not found.")

        pattern.is_ignored = False
        pattern.save(update_fields=["is_ignored", "updated_at"])

        return RecurringPatternResult(success=True, pattern=_make_pattern_type(pattern))

    @strawberry.mutation
    def update_pattern(
        self, info: Info[Context, None], input: UpdatePatternInput
    ) -> RecurringPatternResult:
        user, err = check_perm(info, "banking", "write")
        if err:
            return RecurringPatternResult(success=False, error=err)

        from apps.banking.models import RecurringPattern

        try:
            pattern = RecurringPattern.objects.select_related("counterparty").get(
                id=input.id, tenant=user.tenant
            )
        except RecurringPattern.DoesNotExist:
            return RecurringPatternResult(success=False, error="Pattern not found.")

        update_fields = ["updated_at"]
        if input.amount is not None:
            pattern.average_amount = input.amount
            update_fields.append("average_amount")
        if input.frequency is not None:
            pattern.frequency = input.frequency
            update_fields.append("frequency")
        if input.day_of_month is not None:
            pattern.day_of_month = input.day_of_month
            update_fields.append("day_of_month")

        pattern.save(update_fields=update_fields)

        return RecurringPatternResult(success=True, pattern=_make_pattern_type(pattern))

    @strawberry.mutation
    def pause_pattern(
        self, info: Info[Context, None], pattern_id: int
    ) -> RecurringPatternResult:
        user, err = check_perm(info, "banking", "write")
        if err:
            return RecurringPatternResult(success=False, error=err)

        from apps.banking.models import RecurringPattern

        try:
            pattern = RecurringPattern.objects.select_related("counterparty").get(
                id=pattern_id, tenant=user.tenant
            )
        except RecurringPattern.DoesNotExist:
            return RecurringPatternResult(success=False, error="Pattern not found.")

        pattern.is_paused = True
        pattern.save(update_fields=["is_paused", "updated_at"])

        return RecurringPatternResult(success=True, pattern=_make_pattern_type(pattern))

    @strawberry.mutation
    def resume_pattern(
        self, info: Info[Context, None], pattern_id: int
    ) -> RecurringPatternResult:
        user, err = check_perm(info, "banking", "write")
        if err:
            return RecurringPatternResult(success=False, error=err)

        from apps.banking.models import RecurringPattern

        try:
            pattern = RecurringPattern.objects.select_related("counterparty").get(
                id=pattern_id, tenant=user.tenant
            )
        except RecurringPattern.DoesNotExist:
            return RecurringPatternResult(success=False, error="Pattern not found.")

        pattern.is_paused = False
        pattern.save(update_fields=["is_paused", "updated_at"])

        return RecurringPatternResult(success=True, pattern=_make_pattern_type(pattern))

    @strawberry.mutation
    def link_counterparty_to_customer(
        self, info: Info[Context, None], counterparty_id: strawberry.ID, customer_id: int
    ) -> CounterpartyResult:
        """Link a counterparty to a customer for payment matching."""
        user, err = check_perm(info, "banking", "write")
        if err:
            return CounterpartyResult(success=False, error=err)

        from apps.banking.models import Counterparty
        from apps.customers.models import Customer

        try:
            cp = Counterparty.objects.get(id=str(counterparty_id), tenant=user.tenant)
        except Counterparty.DoesNotExist:
            return CounterpartyResult(success=False, error="Counterparty not found.")

        try:
            customer = Customer.objects.get(id=customer_id, tenant=user.tenant)
        except Customer.DoesNotExist:
            return CounterpartyResult(success=False, error="Customer not found.")

        cp.customer = customer
        cp.save(update_fields=["customer", "updated_at"])

        # Reload to get customer name
        cp = Counterparty.objects.select_related("customer").get(id=str(counterparty_id))

        return CounterpartyResult(
            success=True,
            counterparty=_make_counterparty_type(cp),
        )

    @strawberry.mutation
    def unlink_counterparty_from_customer(
        self, info: Info[Context, None], counterparty_id: strawberry.ID
    ) -> CounterpartyResult:
        """Remove the customer link from a counterparty."""
        user, err = check_perm(info, "banking", "write")
        if err:
            return CounterpartyResult(success=False, error=err)

        from apps.banking.models import Counterparty

        try:
            cp = Counterparty.objects.get(id=str(counterparty_id), tenant=user.tenant)
        except Counterparty.DoesNotExist:
            return CounterpartyResult(success=False, error="Counterparty not found.")

        cp.customer = None
        cp.save(update_fields=["customer", "updated_at"])

        return CounterpartyResult(
            success=True,
            counterparty=_make_counterparty_type(cp),
        )

    # --- Invoice Inbox Mutations ---

    @strawberry.mutation
    def create_invoice_inbox(self, info: Info[Context, None], input: CreateInvoiceInboxInput) -> InvoiceInboxResult:
        user, err = check_perm(info, "incoming_invoices", "config")
        if err: return InvoiceInboxResult(success=False, error=err)
        from apps.banking.models import InvoiceInbox
        inbox = InvoiceInbox.objects.create(tenant=user.tenant, name=input.name, inbox_type=input.inbox_type, host=input.host, port=input.port, username=input.username, password=input.password, folder=input.folder, use_ssl=input.use_ssl, m365_mailbox=input.m365_mailbox, is_active=input.is_active, poll_interval_minutes=input.poll_interval_minutes)
        return InvoiceInboxResult(success=True, inbox=_make_inbox_type(inbox))

    @strawberry.mutation
    def update_invoice_inbox(self, info: Info[Context, None], input: UpdateInvoiceInboxInput) -> InvoiceInboxResult:
        user, err = check_perm(info, "incoming_invoices", "config")
        if err: return InvoiceInboxResult(success=False, error=err)
        from apps.banking.models import InvoiceInbox
        try:
            inbox = InvoiceInbox.objects.get(id=str(input.id), tenant=user.tenant)
        except InvoiceInbox.DoesNotExist:
            return InvoiceInboxResult(success=False, error="Inbox not found.")
        fields = ["updated_at"]
        for field in ["name", "inbox_type", "host", "port", "username", "password", "folder", "use_ssl", "m365_mailbox", "is_active", "poll_interval_minutes"]:
            val = getattr(input, field)
            if val is not None:
                setattr(inbox, field, val)
                fields.append(field)
        inbox.save(update_fields=fields)
        return InvoiceInboxResult(success=True, inbox=_make_inbox_type(inbox))

    @strawberry.mutation
    def delete_invoice_inbox(self, info: Info[Context, None], id: strawberry.ID) -> DeleteResult:
        user, err = check_perm(info, "incoming_invoices", "config")
        if err: return DeleteResult(success=False, error=err)
        from apps.banking.models import InvoiceInbox
        try:
            inbox = InvoiceInbox.objects.get(id=str(id), tenant=user.tenant)
        except InvoiceInbox.DoesNotExist:
            return DeleteResult(success=False, error="Inbox not found.")
        inbox.delete()
        return DeleteResult(success=True)

    @strawberry.mutation
    def test_invoice_inbox_connection(self, info: Info[Context, None], id: strawberry.ID) -> TestConnectionResult:
        user, err = check_perm(info, "incoming_invoices", "config")
        if err: return TestConnectionResult(success=False, message=err)
        from apps.banking.models import InvoiceInbox
        from apps.banking.services.inbox_polling import InboxPollingService
        try:
            inbox = InvoiceInbox.objects.get(id=str(id), tenant=user.tenant)
        except InvoiceInbox.DoesNotExist:
            return TestConnectionResult(success=False, message="Inbox not found.")
        success, message, email_count = InboxPollingService().test_connection(inbox)
        return TestConnectionResult(success=success, message=message, email_count=email_count)

    # --- Incoming Invoice Mutations ---

    @strawberry.mutation
    def update_incoming_invoice(self, info: Info[Context, None], input: UpdateIncomingInvoiceInput) -> IncomingInvoiceResult:
        user, err = check_perm(info, "incoming_invoices", "write")
        if err: return IncomingInvoiceResult(success=False, error=err)
        from apps.banking.models import IncomingInvoice, Counterparty
        try:
            inv = IncomingInvoice.objects.filter(tenant=user.tenant).select_related("counterparty", "inbox").get(id=str(input.id))
        except IncomingInvoice.DoesNotExist:
            return IncomingInvoiceResult(success=False, error="Invoice not found.")
        fields = ["updated_at"]
        for field in ["supplier_name", "invoice_number", "currency", "extraction_status"]:
            val = getattr(input, field)
            if val is not None:
                setattr(inv, field, val)
                fields.append(field)
        for field in ["invoice_date", "due_date", "net_amount", "vat_amount", "gross_amount"]:
            val = getattr(input, field)
            if val is not strawberry.UNSET:
                setattr(inv, field, val)
                fields.append(field)
        if input.counterparty_id is not strawberry.UNSET:
            if input.counterparty_id is None:
                inv.counterparty = None
            else:
                try:
                    inv.counterparty = Counterparty.objects.get(id=str(input.counterparty_id), tenant=user.tenant)
                except Counterparty.DoesNotExist:
                    return IncomingInvoiceResult(success=False, error="Counterparty not found.")
            fields.append("counterparty")
        inv.save(update_fields=fields)
        return IncomingInvoiceResult(success=True, invoice=_make_incoming_invoice_type(inv))

    @strawberry.mutation
    def delete_incoming_invoice(self, info: Info[Context, None], id: strawberry.ID) -> DeleteResult:
        user, err = check_perm(info, "incoming_invoices", "write")
        if err: return DeleteResult(success=False, error=err)
        from apps.banking.models import IncomingInvoice
        try:
            inv = IncomingInvoice.objects.get(id=str(id), tenant=user.tenant)
        except IncomingInvoice.DoesNotExist:
            return DeleteResult(success=False, error="Invoice not found.")
        if inv.pdf_file:
            inv.pdf_file.delete(save=False)
        inv.delete()
        return DeleteResult(success=True)

    @strawberry.mutation
    def upload_incoming_invoices(
        self, info: Info[Context, None], files: List[UploadIncomingInvoiceFileInput]
    ) -> UploadIncomingInvoicesResult:
        """Upload PDFs or a ZIP file containing PDFs as incoming invoices."""
        import base64
        import hashlib
        import io
        import zipfile

        from django.core.files.base import ContentFile

        from apps.banking.models import IncomingInvoice
        from apps.banking.services.incoming_extraction import run_incoming_extraction

        user = require_perm(info, "incoming_invoices", "write")
        tenant = user.tenant

        # Collect all PDFs (expand ZIPs)
        pdf_files: list[tuple[str, bytes]] = []
        for f in files:
            try:
                raw = base64.b64decode(f.file_content)
            except Exception:
                continue

            if f.filename.lower().endswith(".zip"):
                try:
                    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
                        for name in zf.namelist():
                            if name.lower().endswith(".pdf") and not name.startswith("__MACOSX"):
                                pdf_files.append((name.split("/")[-1], zf.read(name)))
                except zipfile.BadZipFile:
                    return UploadIncomingInvoicesResult(success=False, error=f"Invalid ZIP file: {f.filename}")
            elif f.filename.lower().endswith(".pdf"):
                pdf_files.append((f.filename, raw))

        if not pdf_files:
            return UploadIncomingInvoicesResult(success=False, error="No PDF files found.")

        results = []
        uploaded = 0
        failed = 0

        for filename, pdf_data in pdf_files:
            try:
                # Skip duplicates by content hash
                content_hash = hashlib.sha256(pdf_data).hexdigest()
                if IncomingInvoice.objects.filter(
                    tenant=tenant, content_hash=content_hash
                ).exists():
                    results.append(UploadIncomingInvoiceItemResult(
                        filename=filename, success=True, error="duplicate_skipped"
                    ))
                    continue

                invoice = IncomingInvoice(
                    tenant=tenant,
                    original_filename=filename,
                    file_size=len(pdf_data),
                    content_hash=content_hash,
                    extraction_status=IncomingInvoice.ExtractionStatus.PENDING,
                )
                invoice.pdf_file.save(filename, ContentFile(pdf_data), save=False)
                invoice.save()

                try:
                    extracted = run_incoming_extraction(invoice)
                    if not extracted and not IncomingInvoice.objects.filter(id=invoice.id).exists():
                        # Invoice was deleted as duplicate during extraction
                        results.append(UploadIncomingInvoiceItemResult(
                            filename=filename, success=True, error="duplicate_skipped"
                        ))
                        continue
                except Exception:
                    pass  # extraction errors are stored on the invoice

                uploaded += 1
                results.append(UploadIncomingInvoiceItemResult(filename=filename, success=True))
            except Exception as e:
                failed += 1
                results.append(UploadIncomingInvoiceItemResult(filename=filename, success=False, error=str(e)))

        return UploadIncomingInvoicesResult(
            success=True,
            total_uploaded=uploaded,
            total_failed=failed,
            results=results,
        )

    # --- Cost Center CRUD ---

    @strawberry.mutation
    def create_cost_center(
        self, info: Info[Context, None], input: CreateCostCenterInput
    ) -> CostCenterResult:
        user, err = check_perm(info, "cost_centers", "config")
        if err:
            return CostCenterResult(success=False, error=err)
        from apps.banking.models import CostCenter
        code = input.code.strip()
        name = input.name.strip()
        if not code or not name:
            return CostCenterResult(success=False, error="Code and name are required.")
        if CostCenter.objects.filter(tenant=user.tenant, code=code).exists():
            return CostCenterResult(success=False, error="A cost center with this code already exists.")
        cc = CostCenter.objects.create(tenant=user.tenant, code=code, name=name, is_active=input.is_active)
        return CostCenterResult(success=True, cost_center=_make_cost_center_type(cc))

    @strawberry.mutation
    def update_cost_center(
        self, info: Info[Context, None], input: UpdateCostCenterInput
    ) -> CostCenterResult:
        user, err = check_perm(info, "cost_centers", "config")
        if err:
            return CostCenterResult(success=False, error=err)
        from apps.banking.models import CostCenter
        try:
            cc = CostCenter.objects.get(id=str(input.id), tenant=user.tenant)
        except CostCenter.DoesNotExist:
            return CostCenterResult(success=False, error="Cost center not found.")
        update_fields = ["updated_at"]
        if input.code is not None:
            code = input.code.strip()
            if CostCenter.objects.filter(tenant=user.tenant, code=code).exclude(id=cc.id).exists():
                return CostCenterResult(success=False, error="A cost center with this code already exists.")
            cc.code = code
            update_fields.append("code")
        if input.name is not None:
            cc.name = input.name.strip()
            update_fields.append("name")
        if input.is_active is not None:
            cc.is_active = input.is_active
            update_fields.append("is_active")
        cc.save(update_fields=update_fields)
        return CostCenterResult(success=True, cost_center=_make_cost_center_type(cc))

    @strawberry.mutation
    def delete_cost_center(
        self, info: Info[Context, None], id: strawberry.ID, force: bool = False,
    ) -> DeleteCostCenterResult:
        user, err = check_perm(info, "cost_centers", "config")
        if err:
            return DeleteCostCenterResult(success=False, error=err)
        from apps.banking.models import CostCenter, BankTransaction, Counterparty
        try:
            cc = CostCenter.objects.get(id=str(id), tenant=user.tenant)
        except CostCenter.DoesNotExist:
            return DeleteCostCenterResult(success=False, error="Cost center not found.")
        txn_count = BankTransaction.objects.filter(cost_center=cc).count()
        cp_count = Counterparty.objects.filter(default_cost_center=cc).count()
        total_usage = txn_count + cp_count
        if total_usage > 0 and not force:
            return DeleteCostCenterResult(
                success=False,
                error=f"Cost center is in use ({txn_count} transactions, {cp_count} counterparties).",
                in_use=True, usage_count=total_usage,
            )
        BankTransaction.objects.filter(cost_center=cc).update(cost_center=None)
        Counterparty.objects.filter(default_cost_center=cc).update(default_cost_center=None)
        cc.delete()
        return DeleteCostCenterResult(success=True)

    # --- Cost Center Split Rule CRUD ---

    @strawberry.mutation
    def create_cost_center_split_rule(
        self, info: Info[Context, None], input: CreateSplitRuleInput
    ) -> CostCenterSplitRuleResult:
        user, err = check_perm(info, "cost_centers", "config")
        if err:
            return CostCenterSplitRuleResult(success=False, error=err)

        from apps.banking.models import CostCenter, CostCenterSplitRule, CostCenterSplitAllocation, Counterparty

        if not input.counterparty_id and not input.booking_text_pattern:
            return CostCenterSplitRuleResult(
                success=False, error="Either counterparty or booking text pattern is required."
            )

        is_fte_mode = input.mode == "fte_distribution"

        if not is_fte_mode and not input.allocations:
            return CostCenterSplitRuleResult(
                success=False, error="At least one allocation is required."
            )

        # Validate allocations total 100% for percentage rules
        if not is_fte_mode:
            has_pct = any(a.percentage is not None for a in input.allocations)
            if has_pct:
                total_pct = sum(a.percentage or Decimal("0") for a in input.allocations)
                if total_pct != Decimal("100"):
                    return CostCenterSplitRuleResult(
                        success=False,
                        error=f"Allocation percentages must total 100% (got {total_pct}%).",
                    )

        counterparty = None
        if input.counterparty_id:
            try:
                counterparty = Counterparty.objects.get(id=str(input.counterparty_id), tenant=user.tenant)
            except Counterparty.DoesNotExist:
                return CostCenterSplitRuleResult(success=False, error="Counterparty not found.")

        rule = CostCenterSplitRule.objects.create(
            tenant=user.tenant,
            counterparty=counterparty,
            booking_text_pattern=input.booking_text_pattern or None,
            priority=input.priority,
            is_active=input.is_active,
            mode=input.mode,
        )

        for alloc_input in input.allocations:
            try:
                cc = CostCenter.objects.get(id=str(alloc_input.cost_center_id), tenant=user.tenant)
            except CostCenter.DoesNotExist:
                rule.delete()
                return CostCenterSplitRuleResult(success=False, error=f"Cost center not found: {alloc_input.cost_center_id}")
            CostCenterSplitAllocation.objects.create(
                rule=rule,
                cost_center=cc,
                percentage=alloc_input.percentage,
                fixed_amount=alloc_input.fixed_amount,
            )

        return CostCenterSplitRuleResult(success=True, rule=_make_split_rule_type(rule))

    @strawberry.mutation
    def update_cost_center_split_rule(
        self, info: Info[Context, None], input: UpdateSplitRuleInput
    ) -> CostCenterSplitRuleResult:
        user, err = check_perm(info, "cost_centers", "config")
        if err:
            return CostCenterSplitRuleResult(success=False, error=err)

        from apps.banking.models import CostCenter, CostCenterSplitRule, CostCenterSplitAllocation, Counterparty

        try:
            rule = CostCenterSplitRule.objects.get(id=str(input.id), tenant=user.tenant)
        except CostCenterSplitRule.DoesNotExist:
            return CostCenterSplitRuleResult(success=False, error="Split rule not found.")

        update_fields = ["updated_at"]

        if input.counterparty_id is not strawberry.UNSET:
            if input.counterparty_id is None:
                rule.counterparty = None
            else:
                try:
                    rule.counterparty = Counterparty.objects.get(id=str(input.counterparty_id), tenant=user.tenant)
                except Counterparty.DoesNotExist:
                    return CostCenterSplitRuleResult(success=False, error="Counterparty not found.")
            update_fields.append("counterparty")

        if input.booking_text_pattern is not strawberry.UNSET:
            rule.booking_text_pattern = input.booking_text_pattern or None
            update_fields.append("booking_text_pattern")

        if input.priority is not None:
            rule.priority = input.priority
            update_fields.append("priority")

        if input.is_active is not None:
            rule.is_active = input.is_active
            update_fields.append("is_active")

        rule.save(update_fields=update_fields)

        # Replace allocations if provided
        if input.allocations is not None:
            has_pct = any(a.percentage is not None for a in input.allocations)
            if has_pct:
                total_pct = sum(a.percentage or Decimal("0") for a in input.allocations)
                if total_pct != Decimal("100"):
                    return CostCenterSplitRuleResult(
                        success=False,
                        error=f"Allocation percentages must total 100% (got {total_pct}%).",
                    )

            rule.allocations.all().delete()
            for alloc_input in input.allocations:
                try:
                    cc = CostCenter.objects.get(id=str(alloc_input.cost_center_id), tenant=user.tenant)
                except CostCenter.DoesNotExist:
                    return CostCenterSplitRuleResult(success=False, error=f"Cost center not found: {alloc_input.cost_center_id}")
                CostCenterSplitAllocation.objects.create(
                    rule=rule,
                    cost_center=cc,
                    percentage=alloc_input.percentage,
                    fixed_amount=alloc_input.fixed_amount,
                )

        return CostCenterSplitRuleResult(success=True, rule=_make_split_rule_type(rule))

    @strawberry.mutation
    def delete_cost_center_split_rule(
        self, info: Info[Context, None], id: strawberry.ID
    ) -> DeleteResult:
        user, err = check_perm(info, "cost_centers", "config")
        if err:
            return DeleteResult(success=False, error=err)

        from apps.banking.models import CostCenterSplitRule

        try:
            rule = CostCenterSplitRule.objects.get(id=str(id), tenant=user.tenant)
        except CostCenterSplitRule.DoesNotExist:
            return DeleteResult(success=False, error="Split rule not found.")

        rule.delete()
        return DeleteResult(success=True)

    @strawberry.mutation
    def capture_fte_distribution_snapshot(
        self, info: Info[Context, None], year_month: str,
    ) -> FteSnapshotResult:
        """Manually capture an FTE distribution snapshot for a given month."""
        user, err = check_perm(info, "cost_centers", "config")
        if err:
            return FteSnapshotResult(success=False, error=err)
        if not user.tenant:
            return FteSnapshotResult(success=False, error="No tenant assigned")

        from apps.banking.services.fte_snapshot import capture_snapshot

        try:
            snapshot = capture_snapshot(user.tenant, year_month, user=user)
        except ValueError as e:
            return FteSnapshotResult(success=False, error=str(e))

        entries = [
            FteDistributionEntryType(
                id=strawberry.ID(str(e.id)),
                department_name=e.department_name,
                cost_center_code=e.cost_center_code,
                fte_percentage=e.fte_percentage,
                monthly_income_total=e.monthly_income_total,
                hours_total=e.hours_total,
            )
            for e in snapshot.entries.all()
        ]
        return FteSnapshotResult(
            success=True,
            snapshot=FteDistributionSnapshotType(
                id=strawberry.ID(str(snapshot.id)),
                year_month=snapshot.year_month,
                captured_at=snapshot.captured_at.isoformat(),
                captured_by_name=user.get_full_name() if user else None,
                entries=entries,
            ),
        )

    @strawberry.mutation
    def split_transaction_cost_centers(
        self,
        info: Info[Context, None],
        transaction_id: int,
        splits: List[ManualSplitInput],
    ) -> ManualSplitResult:
        """Manually split a transaction across cost centers."""
        user, err = check_perm(info, "cost_centers", "write")
        if err:
            return ManualSplitResult(success=False, error=err)

        from apps.banking.models import BankTransaction, CostCenter, TransactionCostCenterSplit

        try:
            txn = BankTransaction.objects.get(id=transaction_id, tenant=user.tenant)
        except BankTransaction.DoesNotExist:
            return ManualSplitResult(success=False, error="Transaction not found.")

        # Validate amounts sum to abs(transaction.amount)
        total = sum(s.amount for s in splits)
        expected = abs(txn.amount)
        if total != expected:
            return ManualSplitResult(
                success=False,
                error=f"Split amounts must equal {expected} (got {total}).",
            )

        # Validate cost centers exist
        cc_map = {}
        for s in splits:
            try:
                cc_map[str(s.cost_center_id)] = CostCenter.objects.get(
                    id=str(s.cost_center_id), tenant=user.tenant
                )
            except CostCenter.DoesNotExist:
                return ManualSplitResult(
                    success=False, error=f"Cost center not found: {s.cost_center_id}"
                )

        # Remove all existing splits
        TransactionCostCenterSplit.objects.filter(transaction=txn).delete()

        # Create manual splits
        created = []
        for s in splits:
            split = TransactionCostCenterSplit.objects.create(
                transaction=txn,
                cost_center=cc_map[str(s.cost_center_id)],
                amount=s.amount,
                is_manual=True,
            )
            created.append(split)

        return ManualSplitResult(
            success=True,
            splits=[_make_split_type(s) for s in created],
        )

    @strawberry.mutation
    def assign_transaction_cost_center(
        self, info: Info[Context, None], transaction_id: int, cost_center_id: strawberry.ID | None = None,
    ) -> DeleteResult:
        user, err = check_perm(info, "cost_centers", "write")
        if err:
            return DeleteResult(success=False, error=err)
        from apps.banking.models import BankTransaction, CostCenter
        try:
            txn = BankTransaction.objects.get(id=transaction_id, tenant=user.tenant)
        except BankTransaction.DoesNotExist:
            return DeleteResult(success=False, error="Transaction not found.")
        if cost_center_id is None:
            txn.cost_center = None
        else:
            try:
                cc = CostCenter.objects.get(id=str(cost_center_id), tenant=user.tenant)
            except CostCenter.DoesNotExist:
                return DeleteResult(success=False, error="Cost center not found.")
            txn.cost_center = cc
        txn.save(update_fields=["cost_center", "updated_at"])
        return DeleteResult(success=True)
