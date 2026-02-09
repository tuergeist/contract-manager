"""GraphQL schema for invoices."""
import base64
import os
from datetime import date
from decimal import Decimal
from typing import List, Optional

import strawberry
from django.conf import settings
from django.core.files.base import ContentFile
from strawberry.types import Info

from apps.core.context import Context
from apps.core.permissions import check_perm, get_current_user, require_perm
from apps.core.schema import DeleteResult
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
