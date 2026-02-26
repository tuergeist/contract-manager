"""GraphQL schema for accounting (SKR04 revenue accounts, bookings, DATEV export)."""
from datetime import date
from decimal import Decimal
from typing import List, Optional

import strawberry
from strawberry.types import Info

from apps.core.context import Context
from apps.core.permissions import require_perm
from apps.core.schema import DeleteResult


# ─── Types ────────────────────────────────────────────────────────────────────


@strawberry.type
class RevenueAccountType:
    id: int
    account_number: str
    name: str
    description: str
    tax_rate: Decimal | None
    vat_classification: str
    is_active: bool
    sort_order: int
    mapping_count: int = 0


@strawberry.type
class TaxAccountType:
    id: int
    account_number: str
    name: str
    tax_rate: Decimal
    is_active: bool


@strawberry.type
class RevenueAccountMappingType:
    id: int
    product_id: int | None
    product_name: str | None
    product_category_name: str | None
    tax_rate: Decimal | None
    vat_classification: str
    revenue_account: RevenueAccountType


@strawberry.type
class DebitorAccountType:
    id: int
    customer_id: int
    customer_name: str
    customer_number: str
    account_number: str
    notes: str


@strawberry.type
class DebitorAccountSchemeType:
    prefix: str
    start_number: int
    next_number: int
    end_number: int


@strawberry.type
class BookingEntryType:
    id: int
    booking_date: date
    debit_account: str
    credit_account: str
    amount: Decimal
    tax_rate: Decimal
    tax_key: str
    description: str
    cost_center: str
    invoice_number: str
    customer_name: str


@strawberry.type
class AccountingExportType:
    id: int
    period_start: date
    period_end: date
    export_format: str
    entry_count: int
    total_amount: Decimal
    created_at: str
    notes: str
    download_url: str | None


@strawberry.type
class AccountingValidationType:
    total_invoices: int
    invoices_with_bookings: int
    invoices_without_bookings: int
    customers_without_debitor_count: int
    unmapped_line_items: List["UnmappedLineItemType"]


@strawberry.type
class UnmappedLineItemType:
    invoice_number: str
    product_name: str
    amount: str
    reason: str


@strawberry.type
class GenerateBookingsResultType:
    created: int
    skipped: int
    errors: List[str]


@strawberry.type
class BulkAssignResultType:
    assigned: int
    skipped: int
    errors: List[str]


@strawberry.type
class DebitorImportConflictType:
    customer_name: str
    imported_number: str
    existing_number: str
    reason: str


@strawberry.type
class DebitorImportResultType:
    matched: int
    created: int
    conflicts: List[DebitorImportConflictType]


# ─── Inputs ───────────────────────────────────────────────────────────────────


@strawberry.input
class RevenueAccountInput:
    account_number: str
    name: str
    description: str = ""
    tax_rate: Decimal | None = None
    vat_classification: str = "any"
    is_active: bool = True
    sort_order: int = 0


@strawberry.input
class TaxAccountInput:
    account_number: str
    name: str
    tax_rate: Decimal
    is_active: bool = True


@strawberry.input
class RevenueAccountMappingInput:
    product_id: int | None = None
    tax_rate: Decimal | None = None
    vat_classification: str = "any"
    revenue_account_id: int = 0


@strawberry.input
class DebitorAccountSchemeInput:
    prefix: str | None = None
    start_number: int | None = None
    next_number: int | None = None
    end_number: int | None = None


@strawberry.input
class DebitorImportMappingInput:
    customer_number: str = ""
    customer_name: str = ""
    account_number: str = ""


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _to_revenue_account_type(ra) -> RevenueAccountType:
    return RevenueAccountType(
        id=ra.id,
        account_number=ra.account_number,
        name=ra.name,
        description=ra.description,
        tax_rate=ra.tax_rate,
        vat_classification=ra.vat_classification,
        is_active=ra.is_active,
        sort_order=ra.sort_order,
        mapping_count=ra.mappings.count(),
    )


def _to_mapping_type(m) -> RevenueAccountMappingType:
    product_name = None
    product_category_name = None
    if m.product:
        product_name = m.product.name
        if m.product.category:
            product_category_name = m.product.category.name

    return RevenueAccountMappingType(
        id=m.id,
        product_id=m.product_id,
        product_name=product_name,
        product_category_name=product_category_name,
        tax_rate=m.tax_rate,
        vat_classification=m.vat_classification,
        revenue_account=_to_revenue_account_type(m.revenue_account),
    )


def _to_debitor_type(d) -> DebitorAccountType:
    return DebitorAccountType(
        id=d.id,
        customer_id=d.customer_id,
        customer_name=d.customer.name,
        customer_number=d.customer.netsuite_customer_number or "",
        account_number=d.account_number,
        notes=d.notes,
    )


# ─── Queries ──────────────────────────────────────────────────────────────────


@strawberry.type
class AccountingQuery:

    @strawberry.field
    def revenue_accounts(
        self,
        info: Info[Context, None],
        is_active: bool | None = None,
    ) -> List[RevenueAccountType]:
        from apps.accounting.models import RevenueAccount
        user = require_perm(info, "accounting", "read")
        if not user.tenant:
            return []
        qs = RevenueAccount.objects.filter(tenant=user.tenant)
        if is_active is not None:
            qs = qs.filter(is_active=is_active)
        return [_to_revenue_account_type(ra) for ra in qs]

    @strawberry.field
    def revenue_account(
        self,
        info: Info[Context, None],
        id: strawberry.ID,
    ) -> RevenueAccountType | None:
        from apps.accounting.models import RevenueAccount
        user = require_perm(info, "accounting", "read")
        if not user.tenant:
            return None
        ra = RevenueAccount.objects.filter(tenant=user.tenant, id=id).first()
        return _to_revenue_account_type(ra) if ra else None

    @strawberry.field
    def tax_accounts(
        self,
        info: Info[Context, None],
        is_active: bool | None = None,
    ) -> List[TaxAccountType]:
        from apps.accounting.models import TaxAccount
        user = require_perm(info, "accounting", "read")
        if not user.tenant:
            return []
        qs = TaxAccount.objects.filter(tenant=user.tenant)
        if is_active is not None:
            qs = qs.filter(is_active=is_active)
        return [
            TaxAccountType(
                id=ta.id,
                account_number=ta.account_number,
                name=ta.name,
                tax_rate=ta.tax_rate,
                is_active=ta.is_active,
            )
            for ta in qs
        ]

    @strawberry.field
    def revenue_account_mappings(
        self, info: Info[Context, None],
    ) -> List[RevenueAccountMappingType]:
        from apps.accounting.models import RevenueAccountMapping
        user = require_perm(info, "accounting", "read")
        if not user.tenant:
            return []
        qs = RevenueAccountMapping.objects.filter(
            tenant=user.tenant,
        ).select_related("product", "product__category", "revenue_account")
        return [_to_mapping_type(m) for m in qs]

    @strawberry.field
    def debitor_accounts(
        self,
        info: Info[Context, None],
        has_number: bool | None = None,
    ) -> List[DebitorAccountType]:
        from apps.accounting.models import DebitorAccount
        user = require_perm(info, "accounting", "read")
        if not user.tenant:
            return []
        qs = DebitorAccount.objects.filter(
            tenant=user.tenant,
        ).select_related("customer")
        if has_number is True:
            qs = qs.exclude(account_number="")
        elif has_number is False:
            qs = qs.filter(account_number="")
        return [_to_debitor_type(d) for d in qs]

    @strawberry.field
    def debitor_account_scheme(
        self, info: Info[Context, None],
    ) -> DebitorAccountSchemeType | None:
        from apps.accounting.models import DebitorAccountScheme
        user = require_perm(info, "accounting", "read")
        if not user.tenant:
            return None
        scheme = DebitorAccountScheme.objects.filter(tenant=user.tenant).first()
        if not scheme:
            return DebitorAccountSchemeType(
                prefix="", start_number=10000, next_number=10001, end_number=69999,
            )
        return DebitorAccountSchemeType(
            prefix=scheme.prefix,
            start_number=scheme.start_number,
            next_number=scheme.next_number,
            end_number=scheme.end_number,
        )

    @strawberry.field
    def booking_entries(
        self,
        info: Info[Context, None],
        period_start: date,
        period_end: date,
        account_number: str | None = None,
    ) -> List[BookingEntryType]:
        from apps.accounting.models import BookingEntry
        user = require_perm(info, "accounting", "read")
        if not user.tenant:
            return []
        qs = BookingEntry.objects.filter(
            tenant=user.tenant,
            booking_date__gte=period_start,
            booking_date__lte=period_end,
        ).select_related("invoice_record")
        if account_number:
            from django.db.models import Q
            qs = qs.filter(
                Q(debit_account=account_number) |
                Q(credit_account=account_number)
            )
        return [
            BookingEntryType(
                id=e.id,
                booking_date=e.booking_date,
                debit_account=e.debit_account,
                credit_account=e.credit_account,
                amount=e.amount,
                tax_rate=e.tax_rate,
                tax_key=e.tax_key,
                description=e.description,
                cost_center=e.cost_center,
                invoice_number=e.invoice_record.invoice_number if e.invoice_record else "",
                customer_name=e.invoice_record.customer_name if e.invoice_record else "",
            )
            for e in qs
        ]

    @strawberry.field
    def booking_entries_for_invoice(
        self,
        info: Info[Context, None],
        invoice_record_id: strawberry.ID,
    ) -> List[BookingEntryType]:
        from apps.accounting.models import BookingEntry
        user = require_perm(info, "accounting", "read")
        if not user.tenant:
            return []
        qs = BookingEntry.objects.filter(
            tenant=user.tenant,
            invoice_record_id=invoice_record_id,
        ).select_related("invoice_record")
        return [
            BookingEntryType(
                id=e.id,
                booking_date=e.booking_date,
                debit_account=e.debit_account,
                credit_account=e.credit_account,
                amount=e.amount,
                tax_rate=e.tax_rate,
                tax_key=e.tax_key,
                description=e.description,
                cost_center=e.cost_center,
                invoice_number=e.invoice_record.invoice_number if e.invoice_record else "",
                customer_name=e.invoice_record.customer_name if e.invoice_record else "",
            )
            for e in qs
        ]

    @strawberry.field
    def accounting_exports(
        self, info: Info[Context, None],
    ) -> List[AccountingExportType]:
        from apps.accounting.models import AccountingExport
        user = require_perm(info, "accounting", "read")
        if not user.tenant:
            return []
        qs = AccountingExport.objects.filter(tenant=user.tenant)[:20]
        return [
            AccountingExportType(
                id=e.id,
                period_start=e.period_start,
                period_end=e.period_end,
                export_format=e.export_format,
                entry_count=e.entry_count,
                total_amount=e.total_amount,
                created_at=str(e.created_at),
                notes=e.notes,
                download_url=e.file.url if e.file else None,
            )
            for e in qs
        ]

    @strawberry.field
    def accounting_validation(
        self,
        info: Info[Context, None],
        period_start: date,
        period_end: date,
    ) -> AccountingValidationType:
        from apps.accounting.services import BookingService
        user = require_perm(info, "accounting", "read")
        if not user.tenant:
            return AccountingValidationType(
                total_invoices=0,
                invoices_with_bookings=0,
                invoices_without_bookings=0,
                customers_without_debitor_count=0,
                unmapped_line_items=[],
            )
        result = BookingService().validate_period(user.tenant, period_start, period_end)
        return AccountingValidationType(
            total_invoices=result["total_invoices"],
            invoices_with_bookings=result["invoices_with_bookings"],
            invoices_without_bookings=result["invoices_without_bookings"],
            customers_without_debitor_count=len(result["customers_without_debitor"]),
            unmapped_line_items=[
                UnmappedLineItemType(**item) for item in result["unmapped_line_items"]
            ],
        )


# ─── Mutations ────────────────────────────────────────────────────────────────


@strawberry.type
class AccountingMutation:

    @strawberry.mutation
    def create_revenue_account(
        self, info: Info[Context, None], input: RevenueAccountInput,
    ) -> RevenueAccountType:
        from apps.accounting.models import RevenueAccount
        user = require_perm(info, "accounting", "write")
        ra = RevenueAccount.objects.create(
            tenant=user.tenant,
            account_number=input.account_number,
            name=input.name,
            description=input.description,
            tax_rate=input.tax_rate,
            vat_classification=input.vat_classification,
            is_active=input.is_active,
            sort_order=input.sort_order,
        )
        return _to_revenue_account_type(ra)

    @strawberry.mutation
    def update_revenue_account(
        self, info: Info[Context, None], id: strawberry.ID, input: RevenueAccountInput,
    ) -> RevenueAccountType | None:
        from apps.accounting.models import RevenueAccount
        user = require_perm(info, "accounting", "write")
        ra = RevenueAccount.objects.filter(tenant=user.tenant, id=id).first()
        if not ra:
            return None
        ra.account_number = input.account_number
        ra.name = input.name
        ra.description = input.description
        ra.tax_rate = input.tax_rate
        ra.vat_classification = input.vat_classification
        ra.is_active = input.is_active
        ra.sort_order = input.sort_order
        ra.save()
        return _to_revenue_account_type(ra)

    @strawberry.mutation
    def delete_revenue_account(
        self, info: Info[Context, None], id: strawberry.ID,
    ) -> DeleteResult:
        from apps.accounting.models import RevenueAccount
        user = require_perm(info, "accounting", "write")
        ra = RevenueAccount.objects.filter(tenant=user.tenant, id=id).first()
        if not ra:
            return DeleteResult(success=False, error="Not found")
        if ra.mappings.exists():
            return DeleteResult(success=False, error="Account has active mappings. Remove them first.")
        ra.delete()
        return DeleteResult(success=True)

    @strawberry.mutation
    def create_tax_account(
        self, info: Info[Context, None], input: TaxAccountInput,
    ) -> TaxAccountType:
        from apps.accounting.models import TaxAccount
        user = require_perm(info, "accounting", "write")
        ta = TaxAccount.objects.create(
            tenant=user.tenant,
            account_number=input.account_number,
            name=input.name,
            tax_rate=input.tax_rate,
            is_active=input.is_active,
        )
        return TaxAccountType(
            id=ta.id, account_number=ta.account_number,
            name=ta.name, tax_rate=ta.tax_rate, is_active=ta.is_active,
        )

    @strawberry.mutation
    def update_tax_account(
        self, info: Info[Context, None], id: strawberry.ID, input: TaxAccountInput,
    ) -> TaxAccountType | None:
        from apps.accounting.models import TaxAccount
        user = require_perm(info, "accounting", "write")
        ta = TaxAccount.objects.filter(tenant=user.tenant, id=id).first()
        if not ta:
            return None
        ta.account_number = input.account_number
        ta.name = input.name
        ta.tax_rate = input.tax_rate
        ta.is_active = input.is_active
        ta.save()
        return TaxAccountType(
            id=ta.id, account_number=ta.account_number,
            name=ta.name, tax_rate=ta.tax_rate, is_active=ta.is_active,
        )

    @strawberry.mutation
    def delete_tax_account(
        self, info: Info[Context, None], id: strawberry.ID,
    ) -> DeleteResult:
        from apps.accounting.models import TaxAccount
        user = require_perm(info, "accounting", "write")
        ta = TaxAccount.objects.filter(tenant=user.tenant, id=id).first()
        if not ta:
            return DeleteResult(success=False, error="Not found")
        ta.delete()
        return DeleteResult(success=True)

    @strawberry.mutation
    def create_revenue_account_mapping(
        self, info: Info[Context, None], input: RevenueAccountMappingInput,
    ) -> RevenueAccountMappingType | None:
        from apps.accounting.models import RevenueAccount, RevenueAccountMapping
        user = require_perm(info, "accounting", "write")
        ra = RevenueAccount.objects.filter(tenant=user.tenant, id=input.revenue_account_id).first()
        if not ra:
            return None
        m = RevenueAccountMapping.objects.create(
            tenant=user.tenant,
            product_id=input.product_id,
            tax_rate=input.tax_rate,
            vat_classification=input.vat_classification,
            revenue_account=ra,
        )
        return _to_mapping_type(
            RevenueAccountMapping.objects.select_related(
                "product", "product__category", "revenue_account",
            ).get(id=m.id)
        )

    @strawberry.mutation
    def update_revenue_account_mapping(
        self, info: Info[Context, None], id: strawberry.ID, input: RevenueAccountMappingInput,
    ) -> RevenueAccountMappingType | None:
        from apps.accounting.models import RevenueAccount, RevenueAccountMapping
        user = require_perm(info, "accounting", "write")
        m = RevenueAccountMapping.objects.filter(tenant=user.tenant, id=id).first()
        if not m:
            return None
        ra = RevenueAccount.objects.filter(tenant=user.tenant, id=input.revenue_account_id).first()
        if not ra:
            return None
        m.product_id = input.product_id
        m.tax_rate = input.tax_rate
        m.vat_classification = input.vat_classification
        m.revenue_account = ra
        m.save()
        return _to_mapping_type(
            RevenueAccountMapping.objects.select_related(
                "product", "product__category", "revenue_account",
            ).get(id=m.id)
        )

    @strawberry.mutation
    def delete_revenue_account_mapping(
        self, info: Info[Context, None], id: strawberry.ID,
    ) -> DeleteResult:
        from apps.accounting.models import RevenueAccountMapping
        user = require_perm(info, "accounting", "write")
        m = RevenueAccountMapping.objects.filter(tenant=user.tenant, id=id).first()
        if not m:
            return DeleteResult(success=False, error="Not found")
        m.delete()
        return DeleteResult(success=True)

    @strawberry.mutation
    def seed_default_revenue_accounts(
        self, info: Info[Context, None],
    ) -> List[RevenueAccountType]:
        from django.core.management import call_command
        user = require_perm(info, "accounting", "write")
        if not user.tenant:
            return []
        call_command("seed_skr04_accounts", tenant_id=user.tenant.id)
        from apps.accounting.models import RevenueAccount
        return [
            _to_revenue_account_type(ra)
            for ra in RevenueAccount.objects.filter(tenant=user.tenant)
        ]

    @strawberry.mutation
    def update_debitor_account_scheme(
        self, info: Info[Context, None], input: DebitorAccountSchemeInput,
    ) -> DebitorAccountSchemeType:
        from apps.accounting.models import DebitorAccountScheme
        user = require_perm(info, "accounting", "write")
        scheme, _ = DebitorAccountScheme.objects.get_or_create(tenant=user.tenant)
        if input.prefix is not None:
            scheme.prefix = input.prefix
        if input.start_number is not None:
            scheme.start_number = input.start_number
        if input.next_number is not None:
            scheme.next_number = input.next_number
        if input.end_number is not None:
            scheme.end_number = input.end_number
        scheme.save()
        return DebitorAccountSchemeType(
            prefix=scheme.prefix,
            start_number=scheme.start_number,
            next_number=scheme.next_number,
            end_number=scheme.end_number,
        )

    @strawberry.mutation
    def assign_debitor_account(
        self,
        info: Info[Context, None],
        customer_id: strawberry.ID,
        account_number: str | None = None,
    ) -> DebitorAccountType | None:
        from apps.accounting.services import DebitorService
        user = require_perm(info, "accounting", "write")
        if not user.tenant:
            return None
        debitor = DebitorService().assign_number(
            user.tenant, int(customer_id), account_number,
        )
        from apps.accounting.models import DebitorAccount
        debitor = DebitorAccount.objects.select_related("customer").get(id=debitor.id)
        return _to_debitor_type(debitor)

    @strawberry.mutation
    def bulk_assign_debitor_accounts(
        self,
        info: Info[Context, None],
        customer_ids: List[strawberry.ID] | None = None,
    ) -> BulkAssignResultType:
        from apps.accounting.services import DebitorService
        user = require_perm(info, "accounting", "write")
        if not user.tenant:
            return BulkAssignResultType(assigned=0, skipped=0, errors=[])
        ids = [int(cid) for cid in customer_ids] if customer_ids else None
        result = DebitorService().bulk_assign(user.tenant, ids)
        return BulkAssignResultType(**result)

    @strawberry.mutation
    def import_debitor_accounts(
        self,
        info: Info[Context, None],
        mappings: List[DebitorImportMappingInput],
    ) -> DebitorImportResultType:
        from apps.accounting.services import DebitorService
        user = require_perm(info, "accounting", "write")
        if not user.tenant:
            return DebitorImportResultType(matched=0, created=0, conflicts=[])
        mapping_dicts = [
            {
                "customer_number": m.customer_number,
                "customer_name": m.customer_name,
                "account_number": m.account_number,
            }
            for m in mappings
        ]
        result = DebitorService().import_from_mappings(user.tenant, mapping_dicts)
        return DebitorImportResultType(
            matched=result["matched"],
            created=result["created"],
            conflicts=[
                DebitorImportConflictType(**c) for c in result["conflicts"]
            ],
        )

    @strawberry.mutation
    def generate_bookings(
        self,
        info: Info[Context, None],
        invoice_record_id: strawberry.ID,
    ) -> List[BookingEntryType]:
        from apps.accounting.services import BookingService
        from apps.invoices.models import InvoiceRecord
        user = require_perm(info, "accounting", "write")
        if not user.tenant:
            return []
        invoice = InvoiceRecord.objects.filter(
            tenant=user.tenant, id=invoice_record_id,
        ).first()
        if not invoice:
            return []
        entries = BookingService().generate_bookings(invoice)
        return [
            BookingEntryType(
                id=e.id,
                booking_date=e.booking_date,
                debit_account=e.debit_account,
                credit_account=e.credit_account,
                amount=e.amount,
                tax_rate=e.tax_rate,
                tax_key=e.tax_key,
                description=e.description,
                cost_center=e.cost_center,
                invoice_number=invoice.invoice_number,
                customer_name=invoice.customer_name,
            )
            for e in entries
        ]

    @strawberry.mutation
    def generate_bookings_for_period(
        self,
        info: Info[Context, None],
        period_start: date,
        period_end: date,
        regenerate: bool = False,
    ) -> GenerateBookingsResultType:
        from apps.accounting.services import BookingService
        user = require_perm(info, "accounting", "write")
        if not user.tenant:
            return GenerateBookingsResultType(created=0, skipped=0, errors=[])
        result = BookingService().generate_bookings_for_period(
            user.tenant, period_start, period_end, regenerate,
        )
        return GenerateBookingsResultType(**result)

    @strawberry.mutation
    def export_datev(
        self,
        info: Info[Context, None],
        period_start: date,
        period_end: date,
    ) -> AccountingExportType | None:
        from apps.accounting.datev_export import create_datev_export
        user = require_perm(info, "accounting", "write")
        if not user.tenant:
            return None
        export = create_datev_export(user.tenant, period_start, period_end, user)
        return AccountingExportType(
            id=export.id,
            period_start=export.period_start,
            period_end=export.period_end,
            export_format=export.export_format,
            entry_count=export.entry_count,
            total_amount=export.total_amount,
            created_at=str(export.created_at),
            notes=export.notes,
            download_url=export.file.url if export.file else None,
        )
