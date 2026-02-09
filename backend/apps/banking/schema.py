"""GraphQL schema for banking (bank accounts and transactions)."""
from datetime import date
from decimal import Decimal
from typing import List, Optional

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
class BankTransactionType:
    id: int
    entry_date: date
    value_date: date | None
    amount: Decimal
    currency: str
    transaction_type: str
    counterparty_name: str
    counterparty_iban: str
    counterparty_bic: str
    booking_text: str
    reference: str
    account_name: str


@strawberry.type
class BankTransactionPage:
    items: List[BankTransactionType]
    total_count: int
    page: int
    page_size: int
    has_next_page: bool


@strawberry.type
class BankCounterpartyType:
    name: str
    total_debit: Decimal
    total_credit: Decimal
    transaction_count: int
    first_date: date
    last_date: date


@strawberry.type
class BankCounterpartyPage:
    items: List[BankCounterpartyType]
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
class UpdateTransactionCounterpartyInput:
    transaction_id: int
    counterparty_name: str


@strawberry.type
class TransactionResult:
    success: bool
    error: str | None = None
    transaction: BankTransactionType | None = None


@strawberry.type
class RecurringPatternType:
    id: int
    counterparty_name: str
    counterparty_iban: str
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
    counterparty_name: str
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
        counterparty_name: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        amount_min: Decimal | None = None,
        amount_max: Decimal | None = None,
        direction: str | None = None,
        sort_by: str | None = None,
        sort_order: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> BankTransactionPage:
        user = require_perm(info, "banking", "read")
        from apps.banking.models import BankTransaction

        qs = BankTransaction.objects.filter(
            tenant=user.tenant
        ).select_related("account")

        # Filters
        if account_id:
            qs = qs.filter(account_id=account_id)
        if counterparty_name is not None:
            qs = qs.filter(counterparty_name=counterparty_name)
        if search:
            qs = qs.filter(
                Q(counterparty_name__icontains=search)
                | Q(booking_text__icontains=search)
            )
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

        # Sorting
        sort_field = "entry_date"
        if sort_by in ("date", "entry_date"):
            sort_field = "entry_date"
        elif sort_by == "amount":
            sort_field = "amount"
        elif sort_by in ("counterparty", "counterparty_name"):
            sort_field = "counterparty_name"

        if sort_order == "asc":
            qs = qs.order_by(sort_field, "id")
        else:
            qs = qs.order_by(f"-{sort_field}", "-id")

        # Pagination
        total_count = qs.count()
        offset = (page - 1) * page_size
        items = qs[offset : offset + page_size]

        return BankTransactionPage(
            items=[
                BankTransactionType(
                    id=t.id,
                    entry_date=t.entry_date,
                    value_date=t.value_date,
                    amount=t.amount,
                    currency=t.currency,
                    transaction_type=t.transaction_type,
                    counterparty_name=t.counterparty_name,
                    counterparty_iban=t.counterparty_iban,
                    counterparty_bic=t.counterparty_bic,
                    booking_text=t.booking_text,
                    reference=t.reference,
                    account_name=t.account.name,
                )
                for t in items
            ],
            total_count=total_count,
            page=page,
            page_size=page_size,
            has_next_page=(offset + page_size) < total_count,
        )

    @strawberry.field
    def bank_counterparties(
        self,
        info: Info[Context, None],
        search: str | None = None,
        sort_by: str | None = None,
        sort_order: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> BankCounterpartyPage:
        user = require_perm(info, "banking", "read")
        from apps.banking.models import BankTransaction

        qs = (
            BankTransaction.objects.filter(tenant=user.tenant)
            .exclude(counterparty_name="")
            .values("counterparty_name")
            .annotate(
                total_debit=Sum("amount", filter=Q(amount__lt=0), default=Decimal("0")),
                total_credit=Sum("amount", filter=Q(amount__gt=0), default=Decimal("0")),
                txn_count=Count("id"),
                first_date=Min("entry_date"),
                last_date=Max("entry_date"),
                abs_total=Abs(Sum("amount", default=Decimal("0"))),
            )
        )

        if search:
            qs = qs.filter(counterparty_name__icontains=search)

        # Sorting
        sort_field = "-abs_total"
        if sort_by == "name":
            sort_field = "counterparty_name"
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

        qs = qs.order_by(sort_field, "counterparty_name")

        total_count = qs.count()
        offset = (page - 1) * page_size
        items = qs[offset : offset + page_size]

        return BankCounterpartyPage(
            items=[
                BankCounterpartyType(
                    name=row["counterparty_name"],
                    total_debit=row["total_debit"],
                    total_credit=row["total_credit"],
                    transaction_count=row["txn_count"],
                    first_date=row["first_date"],
                    last_date=row["last_date"],
                )
                for row in items
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

        qs = RecurringPattern.objects.filter(tenant=user.tenant)

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

        return [
            RecurringPatternType(
                id=p.id,
                counterparty_name=p.counterparty_name,
                counterparty_iban=p.counterparty_iban,
                average_amount=p.average_amount,
                frequency=p.frequency,
                day_of_month=p.day_of_month,
                confidence_score=p.confidence_score,
                is_confirmed=p.is_confirmed,
                is_ignored=p.is_ignored,
                is_paused=p.is_paused,
                last_occurrence=p.last_occurrence,
                projected_next_date=get_pattern_next_date(p),
                source_transaction_count=p.source_transactions.count(),
            )
            for p in patterns
        ]

    @strawberry.field
    def liquidity_forecast(
        self,
        info: Info[Context, None],
        months: int = 12,
    ) -> LiquidityForecastType:
        user = require_perm(info, "banking", "read")

        current_balance, balance_date = get_current_balance(user.tenant)
        forecast = get_liquidity_forecast(user.tenant, months)

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
                            counterparty_name=t.counterparty_name,
                            amount=t.amount,
                            projected_date=t.projected_date,
                            is_confirmed=t.is_confirmed,
                        )
                        for t in m.transactions
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
            pattern = RecurringPattern.objects.get(id=pattern_id, tenant=user.tenant)
        except RecurringPattern.DoesNotExist:
            return RecurringPatternResult(success=False, error="Pattern not found.")

        pattern.is_confirmed = True
        pattern.save(update_fields=["is_confirmed", "updated_at"])

        return RecurringPatternResult(
            success=True,
            pattern=RecurringPatternType(
                id=pattern.id,
                counterparty_name=pattern.counterparty_name,
                counterparty_iban=pattern.counterparty_iban,
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
            ),
        )

    @strawberry.mutation
    def ignore_pattern(
        self, info: Info[Context, None], pattern_id: int
    ) -> RecurringPatternResult:
        user, err = check_perm(info, "banking", "write")
        if err:
            return RecurringPatternResult(success=False, error=err)

        from apps.banking.models import RecurringPattern

        try:
            pattern = RecurringPattern.objects.get(id=pattern_id, tenant=user.tenant)
        except RecurringPattern.DoesNotExist:
            return RecurringPatternResult(success=False, error="Pattern not found.")

        pattern.is_ignored = True
        pattern.save(update_fields=["is_ignored", "updated_at"])

        return RecurringPatternResult(
            success=True,
            pattern=RecurringPatternType(
                id=pattern.id,
                counterparty_name=pattern.counterparty_name,
                counterparty_iban=pattern.counterparty_iban,
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
            ),
        )

    @strawberry.mutation
    def restore_pattern(
        self, info: Info[Context, None], pattern_id: int
    ) -> RecurringPatternResult:
        user, err = check_perm(info, "banking", "write")
        if err:
            return RecurringPatternResult(success=False, error=err)

        from apps.banking.models import RecurringPattern

        try:
            pattern = RecurringPattern.objects.get(id=pattern_id, tenant=user.tenant)
        except RecurringPattern.DoesNotExist:
            return RecurringPatternResult(success=False, error="Pattern not found.")

        pattern.is_ignored = False
        pattern.save(update_fields=["is_ignored", "updated_at"])

        return RecurringPatternResult(
            success=True,
            pattern=RecurringPatternType(
                id=pattern.id,
                counterparty_name=pattern.counterparty_name,
                counterparty_iban=pattern.counterparty_iban,
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
            ),
        )

    @strawberry.mutation
    def update_pattern(
        self, info: Info[Context, None], input: UpdatePatternInput
    ) -> RecurringPatternResult:
        user, err = check_perm(info, "banking", "write")
        if err:
            return RecurringPatternResult(success=False, error=err)

        from apps.banking.models import RecurringPattern

        try:
            pattern = RecurringPattern.objects.get(id=input.id, tenant=user.tenant)
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

        return RecurringPatternResult(
            success=True,
            pattern=RecurringPatternType(
                id=pattern.id,
                counterparty_name=pattern.counterparty_name,
                counterparty_iban=pattern.counterparty_iban,
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
            ),
        )

    @strawberry.mutation
    def pause_pattern(
        self, info: Info[Context, None], pattern_id: int
    ) -> RecurringPatternResult:
        user, err = check_perm(info, "banking", "write")
        if err:
            return RecurringPatternResult(success=False, error=err)

        from apps.banking.models import RecurringPattern

        try:
            pattern = RecurringPattern.objects.get(id=pattern_id, tenant=user.tenant)
        except RecurringPattern.DoesNotExist:
            return RecurringPatternResult(success=False, error="Pattern not found.")

        pattern.is_paused = True
        pattern.save(update_fields=["is_paused", "updated_at"])

        return RecurringPatternResult(
            success=True,
            pattern=RecurringPatternType(
                id=pattern.id,
                counterparty_name=pattern.counterparty_name,
                counterparty_iban=pattern.counterparty_iban,
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
            ),
        )

    @strawberry.mutation
    def resume_pattern(
        self, info: Info[Context, None], pattern_id: int
    ) -> RecurringPatternResult:
        user, err = check_perm(info, "banking", "write")
        if err:
            return RecurringPatternResult(success=False, error=err)

        from apps.banking.models import RecurringPattern

        try:
            pattern = RecurringPattern.objects.get(id=pattern_id, tenant=user.tenant)
        except RecurringPattern.DoesNotExist:
            return RecurringPatternResult(success=False, error="Pattern not found.")

        pattern.is_paused = False
        pattern.save(update_fields=["is_paused", "updated_at"])

        return RecurringPatternResult(
            success=True,
            pattern=RecurringPatternType(
                id=pattern.id,
                counterparty_name=pattern.counterparty_name,
                counterparty_iban=pattern.counterparty_iban,
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
            ),
        )

    @strawberry.mutation
    def update_transaction_counterparty(
        self, info: Info[Context, None], input: UpdateTransactionCounterpartyInput
    ) -> TransactionResult:
        """Update the counterparty name on a bank transaction."""
        user, err = check_perm(info, "banking", "write")
        if err:
            return TransactionResult(success=False, error=err)

        from apps.banking.models import BankTransaction

        try:
            txn = BankTransaction.objects.select_related("account").get(
                id=input.transaction_id, tenant=user.tenant
            )
        except BankTransaction.DoesNotExist:
            return TransactionResult(success=False, error="Transaction not found.")

        txn.counterparty_name = input.counterparty_name
        txn.save(update_fields=["counterparty_name", "updated_at"])

        return TransactionResult(
            success=True,
            transaction=BankTransactionType(
                id=txn.id,
                entry_date=txn.entry_date,
                value_date=txn.value_date,
                amount=txn.amount,
                currency=txn.currency,
                transaction_type=txn.transaction_type,
                counterparty_name=txn.counterparty_name,
                counterparty_iban=txn.counterparty_iban,
                counterparty_bic=txn.counterparty_bic,
                booking_text=txn.booking_text,
                reference=txn.reference,
                account_name=txn.account.name,
            ),
        )
