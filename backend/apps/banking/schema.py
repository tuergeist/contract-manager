"""GraphQL schema for banking (bank accounts and transactions)."""
from datetime import date
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
class CounterpartyType:
    """A counterparty entity with UUID identifier."""

    id: strawberry.ID
    name: str
    iban: str
    bic: str
    transaction_count: int
    customer_id: int | None = None
    customer_name: str | None = None


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
    customer: LinkedCustomerType | None = None


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


@strawberry.input
class UpdateTransactionCounterpartyInput:
    transaction_id: int
    counterparty_id: strawberry.ID


@strawberry.type
class CounterpartyResult:
    success: bool
    error: str | None = None
    counterparty: CounterpartyType | None = None


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


def _make_counterparty_type(cp) -> CounterpartyType:
    """Convert a Counterparty model to CounterpartyType."""
    return CounterpartyType(
        id=strawberry.ID(str(cp.id)),
        name=cp.name,
        iban=cp.iban,
        bic=cp.bic,
        transaction_count=getattr(cp, "txn_count", cp.transactions.count()),
        customer_id=cp.customer_id,
        customer_name=cp.customer.name if cp.customer_id and hasattr(cp, "customer") and cp.customer else None,
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
            matched_invoice = InvoiceMatchInfoType(
                invoice_id=strawberry.ID(str(match.invoice_id)),
                invoice_number=match.invoice.invoice_number or "",
                match_type=match.match_type,
                confidence=match.confidence,
                contract_id=match.invoice.contract_id,
                customer_id=match.invoice.customer_id,
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


# --- Queries ---


@strawberry.type
class BankingQuery:
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
        ).select_related("account", "counterparty", "counterparty__customer").prefetch_related(
            "invoice_matches__invoice"
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
    ) -> CounterpartySummaryType | None:
        """Get a single counterparty by ID with summary stats."""
        user = require_perm(info, "banking", "read")
        from apps.banking.models import Counterparty

        try:
            cp = (
                Counterparty.objects.filter(tenant=user.tenant, id=str(id))
                .select_related("customer")
                .annotate(
                    total_debit=Sum(
                        "transactions__amount",
                        filter=Q(transactions__amount__lt=0),
                        default=Decimal("0"),
                    ),
                    total_credit=Sum(
                        "transactions__amount",
                        filter=Q(transactions__amount__gt=0),
                        default=Decimal("0"),
                    ),
                    txn_count=Count("transactions"),
                    first_date=Min("transactions__entry_date"),
                    last_date=Max("transactions__entry_date"),
                )
                .get()
            )
        except Counterparty.DoesNotExist:
            return None

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
            customer=LinkedCustomerType(id=cp.customer.id, name=cp.customer.name) if cp.customer else None,
        )

    @strawberry.field
    def counterparties(
        self,
        info: Info[Context, None],
        search: str | None = None,
        sort_by: str | None = None,
        sort_order: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> CounterpartyPage:
        """List all counterparties with summary stats."""
        user = require_perm(info, "banking", "read")
        from apps.banking.models import Counterparty

        qs = (
            Counterparty.objects.filter(tenant=user.tenant)
            .annotate(
                total_debit=Sum(
                    "transactions__amount",
                    filter=Q(transactions__amount__lt=0),
                    default=Decimal("0"),
                ),
                total_credit=Sum(
                    "transactions__amount",
                    filter=Q(transactions__amount__gt=0),
                    default=Decimal("0"),
                ),
                txn_count=Count("transactions"),
                first_date=Min("transactions__entry_date"),
                last_date=Max("transactions__entry_date"),
                abs_total=Abs(Sum("transactions__amount", default=Decimal("0"))),
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

        cp.save(update_fields=update_fields)

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
