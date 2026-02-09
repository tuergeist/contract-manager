"""GraphQL schema for banking (bank accounts and transactions)."""
from datetime import date
from decimal import Decimal
from typing import List, Optional

import strawberry
from django.db.models import Count, Q
from strawberry.types import Info

from apps.core.context import Context
from apps.core.permissions import check_perm, require_perm
from apps.core.schema import DeleteResult


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
