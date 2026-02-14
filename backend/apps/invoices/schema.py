"""GraphQL schema for invoices."""
import base64
import os
import uuid
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import List, Optional

import strawberry
import strawberry_django
from django.conf import settings
from django.core.files.base import ContentFile
from django.db.models import Q
from strawberry.types import Info

from apps.core.context import Context
from apps.core.permissions import check_perm, get_current_user, require_perm
from apps.core.schema import DeleteResult
from apps.invoices.models import ImportedInvoice, InvoiceImportBatch, InvoicePaymentMatch, UploadStatus
from apps.invoices.services import InvoiceService
from apps.invoices.types import InvoiceData, InvoiceLineItem


# =========================================================================
# Existing types (unchanged)
# =========================================================================


@strawberry.type
class InvoiceLineItemType:
    """A line item in an invoice."""

    item_id: int
    product_name: str
    description: str
    quantity: int
    unit_price: Decimal
    amount: Decimal
    is_prorated: bool
    prorate_factor: Decimal | None
    is_one_off: bool


@strawberry.type
class InvoiceType:
    """Invoice data for preview (calculated, not persisted)."""

    contract_id: int
    contract_name: str
    customer_id: int
    customer_name: str
    customer_address: strawberry.scalars.JSON
    billing_date: date
    billing_period_start: date
    billing_period_end: date
    line_items: List[InvoiceLineItemType]
    total_amount: Decimal
    line_item_count: int
    invoice_text: str


def _convert_line_item(item: InvoiceLineItem) -> InvoiceLineItemType:
    """Convert InvoiceLineItem dataclass to GraphQL type."""
    return InvoiceLineItemType(
        item_id=item.item_id,
        product_name=item.product_name,
        description=item.description,
        quantity=item.quantity,
        unit_price=item.unit_price,
        amount=item.amount,
        is_prorated=item.is_prorated,
        prorate_factor=item.prorate_factor,
        is_one_off=item.is_one_off,
    )


def _convert_invoice(invoice: InvoiceData) -> InvoiceType:
    """Convert InvoiceData dataclass to GraphQL type."""
    return InvoiceType(
        contract_id=invoice.contract_id,
        contract_name=invoice.contract_name,
        customer_id=invoice.customer_id,
        customer_name=invoice.customer_name,
        customer_address=invoice.customer_address,
        billing_date=invoice.billing_date,
        billing_period_start=invoice.billing_period_start,
        billing_period_end=invoice.billing_period_end,
        line_items=[_convert_line_item(item) for item in invoice.line_items],
        total_amount=invoice.total_amount,
        line_item_count=invoice.line_item_count,
        invoice_text=invoice.invoice_text,
    )


# =========================================================================
# Company Legal Data types
# =========================================================================


@strawberry.type
class CompanyLegalDataType:
    """Company legal data for German HGB/UStG compliance."""

    company_name: str
    street: str
    zip_code: str
    city: str
    country: str
    tax_number: str
    vat_id: str
    commercial_register_court: str
    commercial_register_number: str
    managing_directors: List[str]
    bank_name: str
    iban: str
    bic: str
    phone: str
    email: str
    website: str
    share_capital: str
    default_tax_rate: Decimal


@strawberry.input
class CompanyLegalDataInput:
    """Input for saving company legal data."""

    company_name: str
    street: str
    zip_code: str
    city: str
    country: str = "Deutschland"
    tax_number: str = ""
    vat_id: str = ""
    commercial_register_court: str = ""
    commercial_register_number: str = ""
    managing_directors: List[str] = strawberry.field(default_factory=list)
    bank_name: str = ""
    iban: str = ""
    bic: str = ""
    phone: str = ""
    email: str = ""
    website: str = ""
    share_capital: str = ""
    default_tax_rate: Decimal = Decimal("19.00")


@strawberry.type
class CompanyLegalDataResult:
    success: bool
    error: str | None = None
    data: CompanyLegalDataType | None = None


# =========================================================================
# Invoice Number Scheme types
# =========================================================================


@strawberry.type
class InvoiceNumberSchemeType:
    """Invoice number scheme configuration."""

    pattern: str
    next_counter: int
    reset_period: str
    preview: str  # Preview of next number


@strawberry.input
class InvoiceNumberSchemeInput:
    """Input for saving number scheme."""

    pattern: str
    reset_period: str = "yearly"
    next_counter: int | None = None  # Only set if explicitly changing


@strawberry.type
class InvoiceNumberSchemeResult:
    success: bool
    error: str | None = None
    data: InvoiceNumberSchemeType | None = None


# =========================================================================
# Invoice Template types
# =========================================================================


@strawberry.type
class InvoiceTemplateReferenceType:
    """Uploaded reference PDF info."""

    id: int
    original_filename: str
    file_size: int
    created_at: str
    extraction_status: str
    extracted_data: strawberry.scalars.JSON | None


@strawberry.type
class InvoiceTemplateType:
    """Invoice template settings."""

    accent_color: str
    header_text: str
    footer_text: str
    has_logo: bool
    logo_url: str | None
    references: List[InvoiceTemplateReferenceType]


@strawberry.input
class InvoiceTemplateInput:
    """Input for saving template settings."""

    accent_color: str = "#2563eb"
    header_text: str = ""
    footer_text: str = ""


@strawberry.input
class UploadLogoInput:
    """Input for uploading a logo image."""

    file_content: str  # Base64-encoded
    filename: str


@strawberry.input
class UploadReferencePdfInput:
    """Input for uploading a reference PDF."""

    file_content: str  # Base64-encoded
    filename: str


@strawberry.type
class InvoiceTemplateResult:
    success: bool
    error: str | None = None
    data: InvoiceTemplateType | None = None


# =========================================================================
# Invoice Record types
# =========================================================================


@strawberry.type
class InvoiceRecordType:
    """A persisted invoice record."""

    id: int
    invoice_number: str
    contract_id: int | None
    contract_name: str
    customer_id: int | None
    customer_name: str
    billing_date: date
    period_start: date
    period_end: date
    total_net: Decimal
    tax_rate: Decimal
    tax_amount: Decimal
    total_gross: Decimal
    status: str
    generated_at: str
    line_items_snapshot: strawberry.scalars.JSON
    invoice_text: str


@strawberry.type
class GenerateInvoicesResult:
    success: bool
    error: str | None = None
    count: int = 0
    records: List[InvoiceRecordType] = strawberry.field(default_factory=list)


@strawberry.type
class CancelInvoiceResult:
    success: bool
    error: str | None = None


@strawberry.type
class AnalyzeReferenceResult:
    success: bool
    error: str | None = None
    extracted_data: strawberry.scalars.JSON | None = None


# =========================================================================
# Legal Data Completeness Check
# =========================================================================


@strawberry.type
class LegalDataCheckResult:
    is_complete: bool
    missing_fields: List[str]


# =========================================================================
# Imported Invoice types
# =========================================================================


@strawberry.type
class PaymentMatchType:
    """A match between an imported invoice and a bank transaction."""

    id: int
    transaction_id: int
    transaction_date: date
    transaction_amount: Decimal
    counterparty_name: str
    match_type: str
    confidence: Decimal
    matched_at: str
    matched_by_name: str | None


@strawberry.type
class ImportedInvoiceType:
    """An imported outgoing invoice with extracted metadata."""

    id: strawberry.ID
    invoice_number: str
    invoice_date: date | None
    total_amount: Decimal | None
    currency: str
    customer_name: str
    customer_id: int | None
    customer_display_name: str | None
    contract_id: int | None
    contract_name: str | None
    original_filename: str
    file_size: int
    pdf_url: str | None
    extraction_status: str
    extraction_error: str
    is_paid: bool
    paid_at: date | None  # Date of first payment match
    first_payment_transaction_id: int | None  # Transaction ID of first payment match
    payment_matches: List[PaymentMatchType]
    created_at: str
    created_by_name: str | None
    # New fields for receiver mapping
    expected_filename: str
    receiver_emails: List[str]
    upload_status: str
    import_batch_id: int | None


@strawberry.type
class ImportedInvoiceConnection:
    """Paginated list of imported invoices."""

    items: List[ImportedInvoiceType]
    total_count: int
    has_next_page: bool


@strawberry.input
class UploadInvoiceInput:
    """Input for uploading an invoice PDF."""

    file_content: str  # Base64-encoded
    filename: str


@strawberry.input
class UpdateImportedInvoiceInput:
    """Input for correcting extracted invoice fields."""

    invoice_number: str | None = None
    invoice_date: date | None = None
    total_amount: Decimal | None = None
    currency: str | None = None
    customer_name: str | None = None
    customer_id: int | None = None


@strawberry.type
class ImportedInvoiceResult:
    """Result of imported invoice operations."""

    success: bool
    error: str | None = None
    invoice: ImportedInvoiceType | None = None


@strawberry.enum
class PaymentStatusFilter(Enum):
    """Filter for invoice payment status."""

    ALL = "all"
    PAID = "paid"
    UNPAID = "unpaid"


@strawberry.enum
class UploadStatusFilter(Enum):
    """Filter for invoice upload status."""

    ALL = "all"
    PENDING = "pending"
    UPLOADED = "uploaded"


# =========================================================================
# Import Batch types
# =========================================================================


@strawberry.type
class InvoiceImportBatchType:
    """An import batch from CSV upload."""

    id: strawberry.ID
    name: str
    total_expected: int
    total_uploaded: int
    pending_count: int
    created_at: str
    created_by_name: str | None


@strawberry.type
class InvoiceImportBatchConnection:
    """Paginated list of import batches."""

    items: List[InvoiceImportBatchType]
    total_count: int
    has_next_page: bool


@strawberry.input
class UploadInvoiceCsvInput:
    """Input for uploading a CSV with invoice receiver mapping."""

    file_content: str  # Base64-encoded
    filename: str


@strawberry.type
class UploadInvoiceCsvResult:
    """Result of CSV upload."""

    success: bool
    error: str | None = None
    batch: InvoiceImportBatchType | None = None
    rows_processed: int = 0


@strawberry.input
class BulkUploadInvoiceInput:
    """Input for a single invoice in bulk upload."""

    file_content: str  # Base64-encoded
    filename: str


@strawberry.type
class BulkUploadItemResult:
    """Result for a single file in bulk upload."""

    filename: str
    success: bool
    error: str | None = None
    invoice: ImportedInvoiceType | None = None
    matched_expected: bool = False


@strawberry.type
class BulkUploadInvoicesResult:
    """Result of bulk PDF upload."""

    success: bool
    error: str | None = None
    results: List[BulkUploadItemResult] = strawberry.field(default_factory=list)
    total_uploaded: int = 0
    total_failed: int = 0


# =========================================================================
# Customer Matching types
# =========================================================================


@strawberry.type
class CustomerMatchSuggestionType:
    """A potential customer match suggestion."""

    customer_id: int
    customer_name: str
    city: str | None
    similarity: Decimal
    hubspot_id: str | None


# =========================================================================
# Payment Matching types
# =========================================================================


@strawberry.type
class PaymentMatchCandidateType:
    """A potential payment match candidate."""

    transaction_id: int
    transaction_date: date
    amount: Decimal
    counterparty_name: str
    booking_text: str
    match_type: str
    confidence: Decimal


@strawberry.type
class CreatePaymentMatchResult:
    """Result of creating a payment match."""

    success: bool
    error: str | None = None
    match: PaymentMatchType | None = None


# =========================================================================
# Queries
# =========================================================================


@strawberry.type
class InvoiceQuery:
    """Invoice-related queries."""

    @strawberry.field
    def invoices_for_month(
        self, info: Info, year: int, month: int
    ) -> List[InvoiceType]:
        """Get all calculated invoices due for a specific month."""
        user = require_perm(info, "invoices", "read")
        service = InvoiceService(user.tenant)
        invoices = service.get_invoices_for_month(year, month)
        return [_convert_invoice(inv) for inv in invoices]

    @strawberry.field
    def invoice_records_for_month(
        self, info: Info, year: int, month: int, status: str | None = None
    ) -> List[InvoiceRecordType]:
        """Get persisted invoice records for a specific month."""
        user = require_perm(info, "invoices", "read")
        service = InvoiceService(user.tenant)
        records = service.get_persisted_invoices(year, month, status=status)
        return [_convert_record(r) for r in records]

    @strawberry.field
    def company_legal_data(self, info: Info) -> CompanyLegalDataType | None:
        """Get the tenant's company legal data."""
        user = require_perm(info, "settings", "read")
        try:
            ld = user.tenant.legal_data
        except Exception:
            return None
        return _convert_legal_data(ld)

    @strawberry.field
    def invoice_number_scheme(self, info: Info) -> InvoiceNumberSchemeType:
        """Get the tenant's invoice number scheme."""
        user = require_perm(info, "settings", "read")
        from apps.invoices.numbering import InvoiceNumberService

        service = InvoiceNumberService(user.tenant)
        scheme = service._get_or_create_scheme()
        preview = service.preview_next_number()
        return InvoiceNumberSchemeType(
            pattern=scheme.pattern,
            next_counter=scheme.next_counter,
            reset_period=scheme.reset_period,
            preview=preview,
        )

    @strawberry.field
    def invoice_template(self, info: Info) -> InvoiceTemplateType:
        """Get the tenant's invoice template settings."""
        user = require_perm(info, "settings", "read")
        return _get_template_type(user.tenant)

    @strawberry.field
    def pdf_analysis_available(self, info: Info) -> bool:
        """Check if PDF analysis (Claude API) is configured."""
        require_perm(info, "settings", "read")
        return bool(settings.ANTHROPIC_API_KEY)

    @strawberry.field
    def check_legal_data_complete(self, info: Info) -> LegalDataCheckResult:
        """Check if company legal data is complete for invoice generation."""
        user = require_perm(info, "invoices", "read")
        missing = []
        try:
            ld = user.tenant.legal_data
        except Exception:
            return LegalDataCheckResult(
                is_complete=False,
                missing_fields=["Company legal data not configured"],
            )

        if not ld.company_name:
            missing.append("company_name")
        if not ld.street:
            missing.append("street")
        if not ld.zip_code:
            missing.append("zip_code")
        if not ld.city:
            missing.append("city")
        if not ld.tax_number and not ld.vat_id:
            missing.append("tax_number or vat_id")
        if not ld.commercial_register_court:
            missing.append("commercial_register_court")
        if not ld.commercial_register_number:
            missing.append("commercial_register_number")
        if not ld.managing_directors:
            missing.append("managing_directors")

        return LegalDataCheckResult(
            is_complete=len(missing) == 0,
            missing_fields=missing,
        )

    @strawberry.field
    def zugferd_enabled(self, info: Info) -> bool:
        """Check if ZUGFeRD is enabled as default PDF format for the tenant."""
        user = require_perm(info, "settings", "read")
        return user.tenant.settings.get("zugferd_default", False)

    # ----- Imported Invoices -----

    # ----- Import Batches -----

    @strawberry.field
    def import_batches(
        self,
        info: Info,
        offset: int = 0,
        limit: int = 50,
    ) -> InvoiceImportBatchConnection:
        """Get paginated list of import batches."""
        user = require_perm(info, "invoices", "read")

        qs = InvoiceImportBatch.objects.filter(tenant=user.tenant).select_related(
            "uploaded_by"
        ).order_by("-created_at")

        total_count = qs.count()
        items = qs[offset : offset + limit]
        has_next_page = offset + limit < total_count

        return InvoiceImportBatchConnection(
            items=[_convert_import_batch(batch) for batch in items],
            total_count=total_count,
            has_next_page=has_next_page,
        )

    @strawberry.field
    def import_batch(
        self, info: Info, id: strawberry.ID
    ) -> InvoiceImportBatchType | None:
        """Get a single import batch by ID."""
        user = require_perm(info, "invoices", "read")

        try:
            batch = InvoiceImportBatch.objects.select_related(
                "uploaded_by"
            ).get(id=id, tenant=user.tenant)
        except InvoiceImportBatch.DoesNotExist:
            return None

        return _convert_import_batch(batch)

    @strawberry.field
    def pending_invoices(
        self,
        info: Info,
        batch_id: strawberry.ID,
        offset: int = 0,
        limit: int = 50,
    ) -> ImportedInvoiceConnection:
        """Get pending invoices for a specific batch."""
        user = require_perm(info, "invoices", "read")

        qs = ImportedInvoice.objects.filter(
            tenant=user.tenant,
            import_batch_id=batch_id,
            upload_status=UploadStatus.PENDING,
        ).select_related("customer", "created_by", "contract")

        total_count = qs.count()
        items = qs[offset : offset + limit]
        has_next_page = offset + limit < total_count

        return ImportedInvoiceConnection(
            items=[_convert_imported_invoice(inv) for inv in items],
            total_count=total_count,
            has_next_page=has_next_page,
        )

    # ----- Imported Invoices -----

    @strawberry.field
    def imported_invoices(
        self,
        info: Info,
        search: str | None = None,
        customer_id: int | None = None,
        contract_id: int | None = None,
        payment_status: PaymentStatusFilter | None = None,
        upload_status: UploadStatusFilter | None = None,
        sort_by: str | None = None,
        sort_order: str | None = "desc",
        offset: int = 0,
        limit: int = 50,
    ) -> ImportedInvoiceConnection:
        """Get paginated list of imported invoices with optional filters."""
        user = require_perm(info, "invoices", "read")

        qs = ImportedInvoice.objects.filter(tenant=user.tenant).select_related(
            "customer", "created_by", "contract"
        ).prefetch_related("payment_matches__transaction__counterparty")

        # Filter by customer
        if customer_id:
            qs = qs.filter(customer_id=customer_id)

        # Filter by contract
        if contract_id:
            qs = qs.filter(contract_id=contract_id)

        # Search by invoice number
        if search:
            qs = qs.filter(invoice_number__icontains=search)

        # Filter by payment status
        if payment_status == PaymentStatusFilter.PAID:
            qs = qs.filter(payment_matches__isnull=False).distinct()
        elif payment_status == PaymentStatusFilter.UNPAID:
            qs = qs.exclude(payment_matches__isnull=False)

        # Filter by upload status
        if upload_status == UploadStatusFilter.PENDING:
            qs = qs.filter(upload_status=UploadStatus.PENDING)
        elif upload_status == UploadStatusFilter.UPLOADED:
            qs = qs.filter(upload_status=UploadStatus.UPLOADED)

        # Sorting
        allowed_sort_fields = {
            "invoiceNumber": "invoice_number",
            "invoiceDate": "invoice_date",
            "customerName": "customer_name",
            "totalAmount": "total_amount",
            "createdAt": "created_at",
        }
        if sort_by and sort_by in allowed_sort_fields:
            order_field = allowed_sort_fields[sort_by]
            if sort_order == "desc":
                order_field = f"-{order_field}"
            qs = qs.order_by(order_field)
        else:
            qs = qs.order_by("-created_at")

        total_count = qs.count()
        items = qs[offset : offset + limit]
        has_next_page = offset + limit < total_count

        return ImportedInvoiceConnection(
            items=[_convert_imported_invoice(inv) for inv in items],
            total_count=total_count,
            has_next_page=has_next_page,
        )

    @strawberry.field
    def imported_invoice(
        self, info: Info, id: strawberry.ID
    ) -> ImportedInvoiceType | None:
        """Get a single imported invoice by ID."""
        user = require_perm(info, "invoices", "read")

        try:
            inv = ImportedInvoice.objects.select_related(
                "customer", "created_by"
            ).prefetch_related(
                "payment_matches__transaction__counterparty",
                "payment_matches__matched_by",
            ).get(id=id, tenant=user.tenant)
        except ImportedInvoice.DoesNotExist:
            return None

        return _convert_imported_invoice(inv)

    @strawberry.field
    def customer_match_suggestions(
        self, info: Info, invoice_id: strawberry.ID
    ) -> List[CustomerMatchSuggestionType]:
        """Get customer match suggestions for an imported invoice based on extracted name."""
        user = require_perm(info, "invoices", "read")

        try:
            invoice = ImportedInvoice.objects.get(id=invoice_id, tenant=user.tenant)
        except ImportedInvoice.DoesNotExist:
            return []

        if not invoice.customer_name:
            return []

        from apps.invoices.customer_matching import match_customer_by_name

        matches = match_customer_by_name(
            tenant=user.tenant,
            extracted_name=invoice.customer_name,
            min_similarity=0.3,
            limit=5,
        )

        return [
            CustomerMatchSuggestionType(
                customer_id=m.customer_id,
                customer_name=m.customer_name,
                city=m.city,
                similarity=m.similarity,
                hubspot_id=m.hubspot_id,
            )
            for m in matches
        ]

    @strawberry.field
    def find_payment_matches(
        self,
        info: Info,
        invoice_id: strawberry.ID,
        days_after: int = 90,
    ) -> List[PaymentMatchCandidateType]:
        """Find potential payment matches for an imported invoice."""
        user = require_perm(info, "invoices", "read")

        try:
            invoice = ImportedInvoice.objects.select_related("customer").get(
                id=invoice_id, tenant=user.tenant
            )
        except ImportedInvoice.DoesNotExist:
            return []

        from apps.invoices.payment_matching import PaymentMatcher

        matcher = PaymentMatcher()
        matches = matcher.find_matches(invoice, days_after=days_after)

        return [
            PaymentMatchCandidateType(
                transaction_id=m.transaction_id,
                transaction_date=m.transaction_date,
                amount=m.amount,
                counterparty_name=m.counterparty_name,
                booking_text=m.booking_text,
                match_type=m.match_type,
                confidence=m.confidence,
            )
            for m in matches
        ]


# =========================================================================
# Mutations
# =========================================================================


@strawberry.type
class InvoiceMutation:
    """Invoice-related mutations."""

    # ----- Company Legal Data -----

    @strawberry.mutation
    def save_company_legal_data(
        self, info: Info[Context, None], input: CompanyLegalDataInput
    ) -> CompanyLegalDataResult:
        """Save company legal data for the tenant."""
        user, err = check_perm(info, "invoices", "settings")
        if err:
            return CompanyLegalDataResult(success=False, error=err)

        from apps.invoices.models import CompanyLegalData

        # Validate: at least one tax ID
        if not input.tax_number and not input.vat_id:
            return CompanyLegalDataResult(
                success=False,
                error="At least one of Tax Number or VAT ID is required.",
            )
        if not input.managing_directors:
            return CompanyLegalDataResult(
                success=False,
                error="At least one managing director is required.",
            )

        try:
            ld, created = CompanyLegalData.objects.update_or_create(
                tenant=user.tenant,
                defaults={
                    "company_name": input.company_name,
                    "street": input.street,
                    "zip_code": input.zip_code,
                    "city": input.city,
                    "country": input.country,
                    "tax_number": input.tax_number,
                    "vat_id": input.vat_id,
                    "commercial_register_court": input.commercial_register_court,
                    "commercial_register_number": input.commercial_register_number,
                    "managing_directors": input.managing_directors,
                    "bank_name": input.bank_name,
                    "iban": input.iban,
                    "bic": input.bic,
                    "phone": input.phone,
                    "email": input.email,
                    "website": input.website,
                    "share_capital": input.share_capital,
                    "default_tax_rate": input.default_tax_rate,
                },
            )
        except Exception as e:
            return CompanyLegalDataResult(success=False, error=str(e))
        return CompanyLegalDataResult(
            success=True,
            data=_convert_legal_data(ld),
        )

    # ----- Invoice Number Scheme -----

    @strawberry.mutation
    def save_invoice_number_scheme(
        self, info: Info[Context, None], input: InvoiceNumberSchemeInput
    ) -> InvoiceNumberSchemeResult:
        """Save invoice number scheme for the tenant."""
        user, err = check_perm(info, "invoices", "settings")
        if err:
            return InvoiceNumberSchemeResult(success=False, error=err)

        from apps.invoices.models import InvoiceNumberScheme
        from apps.invoices.numbering import InvoiceNumberService

        # Validate pattern
        errors = InvoiceNumberService.validate_pattern(input.pattern)
        if errors:
            return InvoiceNumberSchemeResult(
                success=False, error="; ".join(errors)
            )

        # Validate reset period
        valid_periods = [c[0] for c in InvoiceNumberScheme.ResetPeriod.choices]
        if input.reset_period not in valid_periods:
            return InvoiceNumberSchemeResult(
                success=False,
                error=f"Invalid reset period. Must be one of: {', '.join(valid_periods)}",
            )

        defaults = {
            "pattern": input.pattern,
            "reset_period": input.reset_period,
        }
        if input.next_counter is not None:
            if input.next_counter < 1:
                return InvoiceNumberSchemeResult(
                    success=False, error="Counter must be at least 1."
                )
            defaults["next_counter"] = input.next_counter

        scheme, created = InvoiceNumberScheme.objects.update_or_create(
            tenant=user.tenant,
            defaults=defaults,
        )

        service = InvoiceNumberService(user.tenant)
        preview = service.preview_next_number()

        return InvoiceNumberSchemeResult(
            success=True,
            data=InvoiceNumberSchemeType(
                pattern=scheme.pattern,
                next_counter=scheme.next_counter,
                reset_period=scheme.reset_period,
                preview=preview,
            ),
        )

    # ----- Invoice Template -----

    @strawberry.mutation
    def save_invoice_template(
        self, info: Info[Context, None], input: InvoiceTemplateInput
    ) -> InvoiceTemplateResult:
        """Save invoice template settings."""
        user, err = check_perm(info, "invoices", "settings")
        if err:
            return InvoiceTemplateResult(success=False, error=err)

        from apps.invoices.models import InvoiceTemplate

        template, created = InvoiceTemplate.objects.update_or_create(
            tenant=user.tenant,
            defaults={
                "accent_color": input.accent_color,
                "header_text": input.header_text,
                "footer_text": input.footer_text,
            },
        )
        return InvoiceTemplateResult(
            success=True,
            data=_get_template_type(user.tenant),
        )

    @strawberry.mutation
    def upload_invoice_logo(
        self, info: Info[Context, None], input: UploadLogoInput
    ) -> InvoiceTemplateResult:
        """Upload a logo image for invoice template."""
        user, err = check_perm(info, "invoices", "settings")
        if err:
            return InvoiceTemplateResult(success=False, error=err)

        from apps.invoices.models import InvoiceTemplate

        # Validate extension
        ext = os.path.splitext(input.filename)[1].lower()
        if ext not in settings.ALLOWED_LOGO_EXTENSIONS:
            return InvoiceTemplateResult(
                success=False,
                error=f"File type {ext} not allowed. Accepted: {', '.join(settings.ALLOWED_LOGO_EXTENSIONS)}",
            )

        # Decode base64
        try:
            file_bytes = base64.b64decode(input.file_content, validate=True)
        except Exception:
            return InvoiceTemplateResult(
                success=False, error="Invalid base64 file content"
            )

        # Validate size
        if len(file_bytes) > settings.MAX_LOGO_SIZE:
            max_mb = settings.MAX_LOGO_SIZE / (1024 * 1024)
            return InvoiceTemplateResult(
                success=False,
                error=f"File too large. Maximum size is {max_mb:.0f}MB",
            )

        template, created = InvoiceTemplate.objects.get_or_create(
            tenant=user.tenant,
            defaults={"accent_color": "#2563eb"},
        )

        # Delete old logo if exists
        if template.logo:
            template.logo.delete(save=False)

        template.logo.save(input.filename, ContentFile(file_bytes), save=True)

        return InvoiceTemplateResult(
            success=True,
            data=_get_template_type(user.tenant),
        )

    @strawberry.mutation
    def upload_invoice_reference_pdf(
        self, info: Info[Context, None], input: UploadReferencePdfInput
    ) -> InvoiceTemplateResult:
        """Upload a reference PDF for the invoice template."""
        user, err = check_perm(info, "invoices", "settings")
        if err:
            return InvoiceTemplateResult(success=False, error=err)

        from apps.invoices.models import InvoiceTemplate, InvoiceTemplateReference

        # Validate extension
        ext = os.path.splitext(input.filename)[1].lower()
        if ext != ".pdf":
            return InvoiceTemplateResult(
                success=False,
                error="Only PDF files are accepted for reference uploads.",
            )

        # Decode base64
        try:
            file_bytes = base64.b64decode(input.file_content, validate=True)
        except Exception:
            return InvoiceTemplateResult(
                success=False, error="Invalid base64 file content"
            )

        # Validate size
        if len(file_bytes) > settings.MAX_REFERENCE_PDF_SIZE:
            max_mb = settings.MAX_REFERENCE_PDF_SIZE / (1024 * 1024)
            return InvoiceTemplateResult(
                success=False,
                error=f"File too large. Maximum size is {max_mb:.0f}MB",
            )

        template, created = InvoiceTemplate.objects.get_or_create(
            tenant=user.tenant,
            defaults={"accent_color": "#2563eb"},
        )

        ref = InvoiceTemplateReference(
            template=template,
            original_filename=input.filename,
            file_size=len(file_bytes),
        )
        ref.file.save(input.filename, ContentFile(file_bytes), save=False)
        ref.save()

        return InvoiceTemplateResult(
            success=True,
            data=_get_template_type(user.tenant),
        )

    @strawberry.mutation
    def delete_invoice_template_logo(
        self, info: Info[Context, None]
    ) -> DeleteResult:
        """Delete the invoice template logo."""
        user, err = check_perm(info, "invoices", "settings")
        if err:
            return DeleteResult(success=False, error=err)

        from apps.invoices.models import InvoiceTemplate

        try:
            template = InvoiceTemplate.objects.get(tenant=user.tenant)
        except InvoiceTemplate.DoesNotExist:
            return DeleteResult(success=False, error="No template configured")

        if template.logo:
            template.logo.delete(save=False)
            template.logo = None
            template.save(update_fields=["logo", "updated_at"])

        return DeleteResult(success=True)

    @strawberry.mutation
    def delete_invoice_template_reference(
        self, info: Info[Context, None], reference_id: int
    ) -> DeleteResult:
        """Delete a reference PDF from the template."""
        user, err = check_perm(info, "invoices", "settings")
        if err:
            return DeleteResult(success=False, error=err)

        from apps.invoices.models import InvoiceTemplate, InvoiceTemplateReference

        try:
            template = InvoiceTemplate.objects.get(tenant=user.tenant)
            ref = template.references.get(id=reference_id)
        except (InvoiceTemplate.DoesNotExist, InvoiceTemplateReference.DoesNotExist):
            return DeleteResult(success=False, error="Reference not found")

        ref.file.delete(save=False)
        ref.delete()
        return DeleteResult(success=True)

    # ----- Invoice Generation -----

    @strawberry.mutation
    def generate_invoices(
        self, info: Info[Context, None], year: int, month: int
    ) -> GenerateInvoicesResult:
        """Generate and persist invoices for a month."""
        user, err = check_perm(info, "invoices", "generate")
        if err:
            return GenerateInvoicesResult(success=False, error=err)

        service = InvoiceService(user.tenant)
        try:
            records = service.generate_and_persist(year, month)
        except ValueError as e:
            return GenerateInvoicesResult(success=False, error=str(e))

        return GenerateInvoicesResult(
            success=True,
            count=len(records),
            records=[_convert_record(r) for r in records],
        )

    @strawberry.mutation
    def cancel_invoice(
        self, info: Info[Context, None], invoice_id: int
    ) -> CancelInvoiceResult:
        """Cancel a finalized invoice."""
        user, err = check_perm(info, "invoices", "generate")
        if err:
            return CancelInvoiceResult(success=False, error=err)

        from apps.invoices.models import InvoiceRecord

        try:
            record = InvoiceRecord.objects.get(
                id=invoice_id, tenant=user.tenant
            )
        except InvoiceRecord.DoesNotExist:
            return CancelInvoiceResult(
                success=False, error="Invoice not found"
            )

        try:
            InvoiceService.cancel_invoice(record)
        except ValueError as e:
            return CancelInvoiceResult(success=False, error=str(e))

        return CancelInvoiceResult(success=True)

    @strawberry.mutation
    def set_zugferd_default(
        self, info: Info[Context, None], enabled: bool
    ) -> CancelInvoiceResult:
        """Enable or disable ZUGFeRD as the default PDF export format."""
        user, err = check_perm(info, "invoices", "settings")
        if err:
            return CancelInvoiceResult(success=False, error=err)

        tenant = user.tenant
        tenant_settings = tenant.settings or {}
        tenant_settings["zugferd_default"] = enabled
        tenant.settings = tenant_settings
        tenant.save(update_fields=["settings"])

        return CancelInvoiceResult(success=True)

    # ----- PDF Analysis -----

    @strawberry.mutation
    def analyze_reference_pdf(
        self, info: Info[Context, None], reference_id: int
    ) -> AnalyzeReferenceResult:
        """Analyze a reference invoice PDF to extract legal data, design, and layout."""
        user, err = check_perm(info, "invoices", "settings")
        if err:
            return AnalyzeReferenceResult(success=False, error=err)

        from apps.invoices.models import InvoiceTemplate, InvoiceTemplateReference
        from apps.invoices.pdf_analysis import analyze_reference

        try:
            template = InvoiceTemplate.objects.get(tenant=user.tenant)
            reference = InvoiceTemplateReference.objects.get(
                id=reference_id, template=template
            )
        except (InvoiceTemplate.DoesNotExist, InvoiceTemplateReference.DoesNotExist):
            return AnalyzeReferenceResult(
                success=False, error="Reference PDF not found"
            )

        result = analyze_reference(reference)

        if "error" in result:
            return AnalyzeReferenceResult(
                success=False, error=result["error"]
            )

        return AnalyzeReferenceResult(
            success=True, extracted_data=result
        )

    # ----- Imported Invoices -----

    @strawberry.mutation
    def upload_invoice(
        self, info: Info[Context, None], input: UploadInvoiceInput
    ) -> ImportedInvoiceResult:
        """Upload an invoice PDF for extraction."""
        user, err = check_perm(info, "invoices", "generate")
        if err:
            return ImportedInvoiceResult(success=False, error=err)

        # Validate extension
        ext = os.path.splitext(input.filename)[1].lower()
        if ext != ".pdf":
            return ImportedInvoiceResult(
                success=False,
                error="Only PDF files are accepted.",
            )

        # Decode base64
        try:
            file_bytes = base64.b64decode(input.file_content, validate=True)
        except Exception:
            return ImportedInvoiceResult(
                success=False, error="Invalid base64 file content"
            )

        # Validate size (20MB max)
        max_size = 20 * 1024 * 1024
        if len(file_bytes) > max_size:
            return ImportedInvoiceResult(
                success=False,
                error="File too large. Maximum size is 20MB",
            )

        # Create the imported invoice record
        invoice = ImportedInvoice(
            tenant=user.tenant,
            original_filename=input.filename,
            file_size=len(file_bytes),
            extraction_status=ImportedInvoice.ExtractionStatus.EXTRACTING,
            created_by=user,
        )
        invoice.pdf_file.save(input.filename, ContentFile(file_bytes), save=False)
        invoice.save()

        # Trigger background extraction
        from apps.invoices.tasks import extract_invoice_task
        extract_invoice_task.delay(invoice.id)

        return ImportedInvoiceResult(
            success=True,
            invoice=_convert_imported_invoice(invoice),
        )

    @strawberry.mutation
    def update_imported_invoice(
        self, info: Info[Context, None], id: strawberry.ID, input: UpdateImportedInvoiceInput
    ) -> ImportedInvoiceResult:
        """Update/correct fields on an imported invoice."""
        user, err = check_perm(info, "invoices", "generate")
        if err:
            return ImportedInvoiceResult(success=False, error=err)

        try:
            invoice = ImportedInvoice.objects.get(id=id, tenant=user.tenant)
        except ImportedInvoice.DoesNotExist:
            return ImportedInvoiceResult(
                success=False, error="Invoice not found"
            )

        # Update only provided fields
        if input.invoice_number is not None:
            invoice.invoice_number = input.invoice_number
        if input.invoice_date is not None:
            invoice.invoice_date = input.invoice_date
        if input.total_amount is not None:
            invoice.total_amount = input.total_amount
        if input.currency is not None:
            invoice.currency = input.currency
        if input.customer_name is not None:
            invoice.customer_name = input.customer_name
        if input.customer_id is not None:
            from apps.customers.models import Customer
            try:
                customer = Customer.objects.get(id=input.customer_id, tenant=user.tenant)
                invoice.customer = customer
            except Customer.DoesNotExist:
                return ImportedInvoiceResult(
                    success=False, error="Customer not found"
                )

        invoice.save()

        # Reload with relations
        invoice = ImportedInvoice.objects.select_related(
            "customer", "created_by"
        ).prefetch_related(
            "payment_matches__transaction__counterparty"
        ).get(id=id)

        return ImportedInvoiceResult(
            success=True,
            invoice=_convert_imported_invoice(invoice),
        )

    @strawberry.mutation
    def delete_imported_invoice(
        self, info: Info[Context, None], id: strawberry.ID
    ) -> DeleteResult:
        """Delete an imported invoice and its PDF."""
        user, err = check_perm(info, "invoices", "delete")
        if err:
            return DeleteResult(success=False, error=err)

        try:
            invoice = ImportedInvoice.objects.get(id=id, tenant=user.tenant)
        except ImportedInvoice.DoesNotExist:
            return DeleteResult(success=False, error="Invoice not found")

        # Delete the PDF file
        if invoice.pdf_file:
            invoice.pdf_file.delete(save=False)

        invoice.delete()
        return DeleteResult(success=True)

    @strawberry.mutation
    def confirm_imported_invoice(
        self, info: Info[Context, None], id: strawberry.ID
    ) -> ImportedInvoiceResult:
        """Confirm an extracted invoice, marking it as ready for payment matching."""
        user, err = check_perm(info, "invoices", "generate")
        if err:
            return ImportedInvoiceResult(success=False, error=err)

        try:
            invoice = ImportedInvoice.objects.get(id=id, tenant=user.tenant)
        except ImportedInvoice.DoesNotExist:
            return ImportedInvoiceResult(
                success=False, error="Invoice not found"
            )

        # Only allow confirming extracted invoices
        if invoice.extraction_status not in [
            ImportedInvoice.ExtractionStatus.EXTRACTED,
            ImportedInvoice.ExtractionStatus.EXTRACTION_FAILED,
        ]:
            return ImportedInvoiceResult(
                success=False,
                error="Invoice must be extracted before confirmation",
            )

        invoice.extraction_status = ImportedInvoice.ExtractionStatus.CONFIRMED
        invoice.save(update_fields=["extraction_status", "updated_at"])

        # Reload with relations
        invoice = ImportedInvoice.objects.select_related(
            "customer", "created_by"
        ).prefetch_related(
            "payment_matches__transaction__counterparty"
        ).get(id=id)

        return ImportedInvoiceResult(
            success=True,
            invoice=_convert_imported_invoice(invoice),
        )

    @strawberry.mutation
    def extract_invoice(
        self, info: Info[Context, None], id: strawberry.ID
    ) -> ImportedInvoiceResult:
        """Run extraction on a pending or failed invoice."""
        user, err = check_perm(info, "invoices", "generate")
        if err:
            return ImportedInvoiceResult(success=False, error=err)

        try:
            invoice = ImportedInvoice.objects.get(id=id, tenant=user.tenant)
        except ImportedInvoice.DoesNotExist:
            return ImportedInvoiceResult(
                success=False, error="Invoice not found"
            )

        # Only allow extraction on pending or failed
        if invoice.extraction_status not in [
            ImportedInvoice.ExtractionStatus.PENDING,
            ImportedInvoice.ExtractionStatus.EXTRACTION_FAILED,
        ]:
            return ImportedInvoiceResult(
                success=False,
                error=f"Cannot extract invoice in {invoice.extraction_status} status",
            )

        from apps.invoices.extraction import run_extraction

        success = run_extraction(invoice)

        # Reload with relations
        invoice = ImportedInvoice.objects.select_related(
            "customer", "created_by"
        ).prefetch_related(
            "payment_matches__transaction__counterparty"
        ).get(id=id)

        if not success:
            return ImportedInvoiceResult(
                success=False,
                error=invoice.extraction_error or "Extraction failed",
                invoice=_convert_imported_invoice(invoice),
            )

        return ImportedInvoiceResult(
            success=True,
            invoice=_convert_imported_invoice(invoice),
        )

    @strawberry.mutation
    def re_extract_invoice(
        self, info: Info[Context, None], id: strawberry.ID
    ) -> ImportedInvoiceResult:
        """Re-run extraction on an already extracted invoice."""
        user, err = check_perm(info, "invoices", "generate")
        if err:
            return ImportedInvoiceResult(success=False, error=err)

        try:
            invoice = ImportedInvoice.objects.get(id=id, tenant=user.tenant)
        except ImportedInvoice.DoesNotExist:
            return ImportedInvoiceResult(
                success=False, error="Invoice not found"
            )

        # Allow re-extraction on any status except extracting
        if invoice.extraction_status == ImportedInvoice.ExtractionStatus.EXTRACTING:
            return ImportedInvoiceResult(
                success=False,
                error="Extraction is already in progress",
            )

        from apps.invoices.extraction import run_extraction

        success = run_extraction(invoice)

        # Reload with relations
        invoice = ImportedInvoice.objects.select_related(
            "customer", "created_by"
        ).prefetch_related(
            "payment_matches__transaction__counterparty"
        ).get(id=id)

        if not success:
            return ImportedInvoiceResult(
                success=False,
                error=invoice.extraction_error or "Extraction failed",
                invoice=_convert_imported_invoice(invoice),
            )

        return ImportedInvoiceResult(
            success=True,
            invoice=_convert_imported_invoice(invoice),
        )

    @strawberry.mutation
    def confirm_customer_match(
        self, info: Info[Context, None], invoice_id: strawberry.ID, customer_id: int
    ) -> ImportedInvoiceResult:
        """Link an imported invoice to a customer and transfer receiver emails."""
        user, err = check_perm(info, "invoices", "write")
        if err:
            return ImportedInvoiceResult(success=False, error=err)

        try:
            invoice = ImportedInvoice.objects.get(id=invoice_id, tenant=user.tenant)
        except ImportedInvoice.DoesNotExist:
            return ImportedInvoiceResult(
                success=False, error="Invoice not found"
            )

        from apps.customers.models import Customer

        try:
            customer = Customer.objects.get(id=customer_id, tenant=user.tenant)
        except Customer.DoesNotExist:
            return ImportedInvoiceResult(
                success=False, error="Customer not found"
            )

        invoice.customer = customer
        invoice.save(update_fields=["customer", "updated_at"])

        # Transfer receiver_emails to customer.billing_emails (case-insensitive dedup)
        if invoice.receiver_emails:
            existing_emails = set(e.lower() for e in (customer.billing_emails or []))
            new_emails = []
            for email in invoice.receiver_emails:
                email_lower = email.strip().lower()
                if email_lower and email_lower not in existing_emails:
                    new_emails.append(email_lower)
                    existing_emails.add(email_lower)

            if new_emails:
                customer.billing_emails = sorted(existing_emails)
                customer.save(update_fields=["billing_emails", "updated_at"])

        # Reload with relations
        invoice = ImportedInvoice.objects.select_related(
            "customer", "created_by", "contract"
        ).prefetch_related(
            "payment_matches__transaction__counterparty"
        ).get(id=invoice_id)

        return ImportedInvoiceResult(
            success=True,
            invoice=_convert_imported_invoice(invoice),
        )

    @strawberry.mutation
    def unlink_customer_from_invoice(
        self, info: Info[Context, None], invoice_id: strawberry.ID
    ) -> ImportedInvoiceResult:
        """Unlink a customer from an imported invoice (only if no contract is assigned)."""
        user, err = check_perm(info, "invoices", "write")
        if err:
            return ImportedInvoiceResult(success=False, error=err)

        try:
            invoice = ImportedInvoice.objects.get(id=invoice_id, tenant=user.tenant)
        except ImportedInvoice.DoesNotExist:
            return ImportedInvoiceResult(success=False, error="Invoice not found")

        if invoice.contract_id is not None:
            return ImportedInvoiceResult(
                success=False, error="Cannot unlink customer while invoice is assigned to a contract"
            )

        invoice.customer = None
        invoice.save(update_fields=["customer", "updated_at"])

        invoice = ImportedInvoice.objects.select_related(
            "customer", "created_by", "contract"
        ).prefetch_related(
            "payment_matches__transaction__counterparty"
        ).get(id=invoice_id)

        return ImportedInvoiceResult(
            success=True,
            invoice=_convert_imported_invoice(invoice),
        )

    @strawberry.mutation
    def assign_invoice_contract(
        self,
        info: Info[Context, None],
        invoice_id: strawberry.ID,
        contract_id: int | None,
    ) -> ImportedInvoiceResult:
        """Assign a contract to an imported invoice, or remove the assignment."""
        user, err = check_perm(info, "invoices", "generate")
        if err:
            return ImportedInvoiceResult(success=False, error=err)

        try:
            invoice = ImportedInvoice.objects.get(id=invoice_id, tenant=user.tenant)
        except ImportedInvoice.DoesNotExist:
            return ImportedInvoiceResult(
                success=False, error="Invoice not found"
            )

        if contract_id is not None:
            from apps.contracts.models import Contract

            try:
                contract = Contract.objects.get(id=contract_id, tenant=user.tenant)
            except Contract.DoesNotExist:
                return ImportedInvoiceResult(
                    success=False, error="Contract not found"
                )

            # Optionally verify contract belongs to same customer if customer is set
            if invoice.customer_id and contract.customer_id != invoice.customer_id:
                return ImportedInvoiceResult(
                    success=False, error="Contract does not belong to this customer"
                )

            invoice.contract = contract
        else:
            invoice.contract = None

        invoice.save(update_fields=["contract", "updated_at"])

        # Reload with relations
        invoice = ImportedInvoice.objects.select_related(
            "customer", "created_by", "contract"
        ).prefetch_related(
            "payment_matches__transaction__counterparty"
        ).get(id=invoice_id)

        return ImportedInvoiceResult(
            success=True,
            invoice=_convert_imported_invoice(invoice),
        )

    @strawberry.mutation
    def create_payment_match(
        self,
        info: Info[Context, None],
        invoice_id: strawberry.ID,
        transaction_id: int,
        match_type: str = "manual",
    ) -> CreatePaymentMatchResult:
        """Create a payment match between an invoice and a transaction."""
        user, err = check_perm(info, "invoices", "generate")
        if err:
            return CreatePaymentMatchResult(success=False, error=err)

        try:
            invoice = ImportedInvoice.objects.get(id=invoice_id, tenant=user.tenant)
        except ImportedInvoice.DoesNotExist:
            return CreatePaymentMatchResult(
                success=False, error="Invoice not found"
            )

        from apps.banking.models import BankTransaction

        try:
            transaction = BankTransaction.objects.select_related("counterparty").get(
                id=transaction_id, tenant=user.tenant
            )
        except BankTransaction.DoesNotExist:
            return CreatePaymentMatchResult(
                success=False, error="Transaction not found"
            )

        # Check if match already exists
        if InvoicePaymentMatch.objects.filter(
            invoice=invoice, transaction=transaction
        ).exists():
            return CreatePaymentMatchResult(
                success=False, error="Match already exists"
            )

        # Validate match type
        valid_types = [c[0] for c in InvoicePaymentMatch.MatchType.choices]
        if match_type not in valid_types:
            match_type = InvoicePaymentMatch.MatchType.MANUAL

        # Set confidence based on match type
        confidence = Decimal("1.0") if match_type == "manual" else Decimal("0.8")

        match = InvoicePaymentMatch.objects.create(
            tenant=user.tenant,
            invoice=invoice,
            transaction=transaction,
            match_type=match_type,
            confidence=confidence,
            matched_by=user if match_type == "manual" else None,
        )

        return CreatePaymentMatchResult(
            success=True,
            match=_convert_payment_match(match),
        )

    @strawberry.mutation
    def delete_payment_match(
        self, info: Info[Context, None], match_id: int
    ) -> DeleteResult:
        """Delete a payment match."""
        user, err = check_perm(info, "invoices", "generate")
        if err:
            return DeleteResult(success=False, error=err)

        try:
            match = InvoicePaymentMatch.objects.get(id=match_id, tenant=user.tenant)
        except InvoicePaymentMatch.DoesNotExist:
            return DeleteResult(success=False, error="Match not found")

        match.delete()
        return DeleteResult(success=True)

    # ----- CSV Import / Bulk Upload -----

    @strawberry.mutation
    def upload_invoice_csv(
        self, info: Info[Context, None], input: UploadInvoiceCsvInput
    ) -> UploadInvoiceCsvResult:
        """Upload a CSV file with invoice receiver mapping."""
        import csv
        import io

        user, err = check_perm(info, "invoices", "generate")
        if err:
            return UploadInvoiceCsvResult(success=False, error=err)

        # Validate extension
        ext = os.path.splitext(input.filename)[1].lower()
        if ext != ".csv":
            return UploadInvoiceCsvResult(
                success=False,
                error="Only CSV files are accepted.",
            )

        # Decode base64
        try:
            file_bytes = base64.b64decode(input.file_content, validate=True)
            content = file_bytes.decode("utf-8")
        except Exception:
            return UploadInvoiceCsvResult(
                success=False, error="Invalid file content or encoding"
            )

        # Parse CSV
        try:
            reader = csv.DictReader(io.StringIO(content))
            fieldnames = reader.fieldnames or []

            # Validate required columns - accept 'emails' or 'receivers'
            has_filename = "filename" in fieldnames
            has_emails = "emails" in fieldnames or "receivers" in fieldnames
            if not has_filename or not has_emails:
                return UploadInvoiceCsvResult(
                    success=False,
                    error="CSV must contain 'filename' and 'emails' (or 'receivers') columns",
                )
            emails_column = "receivers" if "receivers" in fieldnames else "emails"

            rows = list(reader)

            # Validate row count
            if len(rows) > 1000:
                return UploadInvoiceCsvResult(
                    success=False,
                    error="CSV exceeds maximum of 1000 rows",
                )

        except csv.Error as e:
            return UploadInvoiceCsvResult(
                success=False, error=f"Invalid CSV format: {e}"
            )

        # Create the batch
        batch = InvoiceImportBatch.objects.create(
            tenant=user.tenant,
            name=input.filename,
            uploaded_by=user,
            total_expected=len(rows),
            total_uploaded=0,
        )

        # Create ImportedInvoice records for each row
        import re
        for row in rows:
            filename = row.get("filename", "").strip()
            emails_str = row.get(emails_column, "").strip()

            if not filename:
                continue

            # Parse emails (semicolon or comma-separated)
            emails = [
                e.strip().lower()
                for e in re.split(r"[;,]", emails_str)
                if e.strip()
            ]

            ImportedInvoice.objects.create(
                tenant=user.tenant,
                import_batch=batch,
                expected_filename=filename,
                receiver_emails=emails,
                upload_status=UploadStatus.PENDING,
                extraction_status=ImportedInvoice.ExtractionStatus.PENDING,
                original_filename=filename,
                file_size=0,
                created_by=user,
            )

        # Update batch counts
        batch.update_counts()

        return UploadInvoiceCsvResult(
            success=True,
            batch=_convert_import_batch(batch),
            rows_processed=len(rows),
        )

    @strawberry.mutation
    def upload_invoices(
        self, info: Info[Context, None], inputs: List[BulkUploadInvoiceInput]
    ) -> BulkUploadInvoicesResult:
        """Upload multiple invoice PDFs at once."""
        user, err = check_perm(info, "invoices", "generate")
        if err:
            return BulkUploadInvoicesResult(success=False, error=err)

        results = []
        total_uploaded = 0
        total_failed = 0

        for inp in inputs:
            # Validate extension
            ext = os.path.splitext(inp.filename)[1].lower()
            if ext != ".pdf":
                results.append(BulkUploadItemResult(
                    filename=inp.filename,
                    success=False,
                    error="Only PDF files are accepted.",
                ))
                total_failed += 1
                continue

            # Decode base64
            try:
                file_bytes = base64.b64decode(inp.file_content, validate=True)
            except Exception:
                results.append(BulkUploadItemResult(
                    filename=inp.filename,
                    success=False,
                    error="Invalid base64 file content",
                ))
                total_failed += 1
                continue

            # Validate size (20MB max)
            max_size = 20 * 1024 * 1024
            if len(file_bytes) > max_size:
                results.append(BulkUploadItemResult(
                    filename=inp.filename,
                    success=False,
                    error="File too large. Maximum size is 20MB",
                ))
                total_failed += 1
                continue

            # Try to match to expected invoice (case-insensitive, most recent pending)
            expected = ImportedInvoice.objects.filter(
                tenant=user.tenant,
                expected_filename__iexact=inp.filename,
                upload_status=UploadStatus.PENDING,
            ).order_by("-created_at").first()

            matched_expected = expected is not None

            if expected:
                # Update existing record
                invoice = expected
                invoice.pdf_file.save(inp.filename, ContentFile(file_bytes), save=False)
                invoice.file_size = len(file_bytes)
                invoice.upload_status = UploadStatus.UPLOADED
                invoice.extraction_status = ImportedInvoice.ExtractionStatus.EXTRACTING
                invoice.save()

                # Update batch counts
                if invoice.import_batch:
                    invoice.import_batch.update_counts()
            else:
                # Create new record
                invoice = ImportedInvoice(
                    tenant=user.tenant,
                    original_filename=inp.filename,
                    file_size=len(file_bytes),
                    upload_status=UploadStatus.UPLOADED,
                    extraction_status=ImportedInvoice.ExtractionStatus.EXTRACTING,
                    created_by=user,
                )
                invoice.pdf_file.save(inp.filename, ContentFile(file_bytes), save=False)
                invoice.save()

            # Trigger background extraction
            from apps.invoices.tasks import extract_invoice_task
            extract_invoice_task.delay(invoice.id)

            results.append(BulkUploadItemResult(
                filename=inp.filename,
                success=True,
                invoice=_convert_imported_invoice(invoice),
                matched_expected=matched_expected,
            ))
            total_uploaded += 1

        return BulkUploadInvoicesResult(
            success=True,
            results=results,
            total_uploaded=total_uploaded,
            total_failed=total_failed,
        )

    @strawberry.mutation
    def delete_import_batch(
        self, info: Info[Context, None], id: strawberry.ID
    ) -> DeleteResult:
        """Delete an import batch and its pending invoices."""
        user, err = check_perm(info, "invoices", "delete")
        if err:
            return DeleteResult(success=False, error=err)

        try:
            batch = InvoiceImportBatch.objects.get(id=id, tenant=user.tenant)
        except InvoiceImportBatch.DoesNotExist:
            return DeleteResult(success=False, error="Batch not found")

        # Delete pending invoices (those without PDFs)
        pending_invoices = ImportedInvoice.objects.filter(
            import_batch=batch,
            upload_status=UploadStatus.PENDING,
        )
        pending_invoices.delete()

        # Clear batch reference from uploaded invoices (keep them)
        ImportedInvoice.objects.filter(import_batch=batch).update(import_batch=None)

        # Delete the batch
        batch.delete()
        return DeleteResult(success=True)


# =========================================================================
# Converters
# =========================================================================


def _convert_legal_data(ld) -> CompanyLegalDataType:
    return CompanyLegalDataType(
        company_name=ld.company_name,
        street=ld.street,
        zip_code=ld.zip_code,
        city=ld.city,
        country=ld.country,
        tax_number=ld.tax_number,
        vat_id=ld.vat_id,
        commercial_register_court=ld.commercial_register_court,
        commercial_register_number=ld.commercial_register_number,
        managing_directors=ld.managing_directors or [],
        bank_name=ld.bank_name,
        iban=ld.iban,
        bic=ld.bic,
        phone=ld.phone,
        email=ld.email,
        website=ld.website,
        share_capital=ld.share_capital,
        default_tax_rate=ld.default_tax_rate,
    )


def _convert_record(record) -> InvoiceRecordType:
    return InvoiceRecordType(
        id=record.id,
        invoice_number=record.invoice_number,
        contract_id=record.contract_id,
        contract_name=record.contract_name,
        customer_id=record.customer_id,
        customer_name=record.customer_name,
        billing_date=record.billing_date,
        period_start=record.period_start,
        period_end=record.period_end,
        total_net=record.total_net,
        tax_rate=record.tax_rate,
        tax_amount=record.tax_amount,
        total_gross=record.total_gross,
        status=record.status,
        generated_at=record.generated_at.isoformat(),
        line_items_snapshot=record.line_items_snapshot,
        invoice_text=record.invoice_text,
    )


def _get_template_type(tenant) -> InvoiceTemplateType:
    from apps.invoices.models import InvoiceTemplate

    try:
        template = InvoiceTemplate.objects.get(tenant=tenant)
        refs = template.references.all()
        return InvoiceTemplateType(
            accent_color=template.accent_color,
            header_text=template.header_text,
            footer_text=template.footer_text,
            has_logo=bool(template.logo),
            logo_url=template.logo.url if template.logo else None,
            references=[
                InvoiceTemplateReferenceType(
                    id=r.id,
                    original_filename=r.original_filename,
                    file_size=r.file_size,
                    created_at=r.created_at.isoformat(),
                    extraction_status=r.extraction_status,
                    extracted_data=r.extracted_data,
                )
                for r in refs
            ],
        )
    except InvoiceTemplate.DoesNotExist:
        return InvoiceTemplateType(
            accent_color="#2563eb",
            header_text="",
            footer_text="",
            has_logo=False,
            logo_url=None,
            references=[],
        )


def _convert_payment_match(match: InvoicePaymentMatch) -> PaymentMatchType:
    """Convert InvoicePaymentMatch to GraphQL type."""
    return PaymentMatchType(
        id=match.id,
        transaction_id=match.transaction_id,
        transaction_date=match.transaction.entry_date,
        transaction_amount=match.transaction.amount,
        counterparty_name=match.transaction.counterparty.name,
        match_type=match.match_type,
        confidence=match.confidence,
        matched_at=match.matched_at.isoformat(),
        matched_by_name=match.matched_by.email if match.matched_by else None,
    )


def _convert_imported_invoice(inv: ImportedInvoice) -> ImportedInvoiceType:
    """Convert ImportedInvoice model to GraphQL type."""
    # Get first payment match for paid_at date and transaction ID
    payment_matches = list(inv.payment_matches.all())
    first_match = payment_matches[0] if payment_matches else None
    paid_at = first_match.transaction.entry_date if first_match else None
    first_payment_transaction_id = first_match.transaction_id if first_match else None

    return ImportedInvoiceType(
        id=strawberry.ID(str(inv.id)),
        invoice_number=inv.invoice_number or "",
        invoice_date=inv.invoice_date,
        total_amount=inv.total_amount,
        currency=inv.currency,
        customer_name=inv.customer_name or "",
        customer_id=inv.customer_id,
        customer_display_name=inv.customer.name if inv.customer else None,
        contract_id=inv.contract_id,
        contract_name=inv.contract.name if inv.contract else None,
        original_filename=inv.original_filename,
        file_size=inv.file_size,
        pdf_url=inv.pdf_file.url if inv.pdf_file else None,
        extraction_status=inv.extraction_status,
        extraction_error=inv.extraction_error or "",
        is_paid=inv.is_paid,
        paid_at=paid_at,
        first_payment_transaction_id=first_payment_transaction_id,
        payment_matches=[
            _convert_payment_match(m) for m in payment_matches
        ],
        created_at=inv.created_at.isoformat(),
        created_by_name=inv.created_by.email if inv.created_by else None,
        expected_filename=inv.expected_filename or "",
        receiver_emails=inv.receiver_emails or [],
        upload_status=inv.upload_status,
        import_batch_id=inv.import_batch_id,
    )


def _convert_import_batch(batch: InvoiceImportBatch) -> InvoiceImportBatchType:
    """Convert InvoiceImportBatch model to GraphQL type."""
    pending_count = batch.total_expected - batch.total_uploaded
    return InvoiceImportBatchType(
        id=strawberry.ID(str(batch.id)),
        name=batch.name,
        total_expected=batch.total_expected,
        total_uploaded=batch.total_uploaded,
        pending_count=pending_count,
        created_at=batch.created_at.isoformat(),
        created_by_name=batch.uploaded_by.email if batch.uploaded_by else None,
    )
