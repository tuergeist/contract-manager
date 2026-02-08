"""Invoice models for persistent invoices, templates, numbering, and legal data."""
import os
import uuid

from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models import TenantModel, TimestampedModel


def logo_upload_path(instance, filename):
    """Upload path: uploads/{tenant_id}/invoices/logos/{uuid}_{ext}"""
    ext = os.path.splitext(filename)[1]
    unique_filename = f"{uuid.uuid4().hex}{ext}"
    return f"uploads/{instance.tenant_id}/invoices/logos/{unique_filename}"


def reference_pdf_upload_path(instance, filename):
    """Upload path: uploads/{tenant_id}/invoices/references/{uuid}.pdf"""
    unique_filename = f"{uuid.uuid4().hex}.pdf"
    tenant_id = instance.template.tenant_id
    return f"uploads/{tenant_id}/invoices/references/{unique_filename}"


class CompanyLegalData(TimestampedModel):
    """German HGB/UStG §14 mandatory company data for invoices."""

    tenant = models.OneToOneField(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        related_name="legal_data",
    )

    # Company identification
    company_name = models.CharField(
        max_length=255,
        help_text="Full legal name including legal form (e.g., 'Muster GmbH')",
    )
    street = models.CharField(max_length=255)
    zip_code = models.CharField(max_length=20)
    city = models.CharField(max_length=255)
    country = models.CharField(max_length=100, default="Deutschland")

    # Tax identification (at least one required)
    tax_number = models.CharField(
        max_length=50,
        blank=True,
        help_text="Steuernummer",
    )
    vat_id = models.CharField(
        max_length=50,
        blank=True,
        help_text="USt-IdNr.",
    )

    # Commercial register (required for GmbH)
    commercial_register_court = models.CharField(
        max_length=255,
        help_text="e.g., 'Amtsgericht München'",
    )
    commercial_register_number = models.CharField(
        max_length=50,
        help_text="e.g., 'HRB 12345'",
    )

    # Managing directors (required for GmbH)
    managing_directors = models.JSONField(
        default=list,
        help_text="List of managing director names (Geschäftsführer)",
    )

    # Bank details (optional but standard)
    bank_name = models.CharField(max_length=255, blank=True)
    iban = models.CharField(max_length=50, blank=True)
    bic = models.CharField(max_length=20, blank=True)

    # Contact (optional)
    phone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True)

    # Share capital (optional, required if not fully paid in)
    share_capital = models.CharField(
        max_length=50,
        blank=True,
        help_text="Stammkapital (e.g., '25.000,00 EUR')",
    )

    # Default tax rate
    default_tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=19.00,
        help_text="Default tax rate in % (e.g., 19.00)",
    )

    class Meta:
        verbose_name = "Company Legal Data"
        verbose_name_plural = "Company Legal Data"

    def __str__(self):
        return f"Legal data for {self.company_name}"

    def clean(self):
        errors = {}
        if not self.tax_number and not self.vat_id:
            errors["tax_number"] = (
                "At least one of Tax Number or VAT ID is required."
            )
            errors["vat_id"] = (
                "At least one of Tax Number or VAT ID is required."
            )
        if not self.managing_directors:
            errors["managing_directors"] = (
                "At least one managing director is required."
            )
        if errors:
            raise ValidationError(errors)

    def to_snapshot(self) -> dict:
        """Capture current state as a JSON-serializable dict for invoice records."""
        return {
            "company_name": self.company_name,
            "street": self.street,
            "zip_code": self.zip_code,
            "city": self.city,
            "country": self.country,
            "tax_number": self.tax_number,
            "vat_id": self.vat_id,
            "commercial_register_court": self.commercial_register_court,
            "commercial_register_number": self.commercial_register_number,
            "managing_directors": self.managing_directors,
            "bank_name": self.bank_name,
            "iban": self.iban,
            "bic": self.bic,
            "phone": self.phone,
            "email": self.email,
            "website": self.website,
            "share_capital": self.share_capital,
            "default_tax_rate": str(self.default_tax_rate),
        }


class InvoiceNumberScheme(TimestampedModel):
    """Configurable invoice number pattern per tenant."""

    class ResetPeriod(models.TextChoices):
        YEARLY = "yearly", "Yearly"
        MONTHLY = "monthly", "Monthly"
        NEVER = "never", "Never"

    tenant = models.OneToOneField(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        related_name="invoice_number_scheme",
    )
    pattern = models.CharField(
        max_length=100,
        default="{YYYY}-{NNNN}",
        help_text="Pattern with placeholders: {YYYY}, {YY}, {MM}, {NNN}, {NNNN}, {NNNNN}",
    )
    next_counter = models.PositiveIntegerField(default=1)
    reset_period = models.CharField(
        max_length=10,
        choices=ResetPeriod.choices,
        default=ResetPeriod.YEARLY,
    )
    last_reset_year = models.PositiveIntegerField(null=True, blank=True)
    last_reset_month = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        verbose_name = "Invoice Number Scheme"

    def __str__(self):
        return f"Number scheme for {self.tenant.name}: {self.pattern}"


class InvoiceTemplate(TenantModel):
    """Configurable invoice template settings per tenant."""

    logo = models.FileField(
        upload_to=logo_upload_path,
        blank=True,
        null=True,
        help_text="Company logo for invoice header (PNG, JPG, SVG, max 5MB)",
    )
    accent_color = models.CharField(
        max_length=7,
        default="#2563eb",
        help_text="Hex color code for accents (e.g., #2563eb)",
    )
    header_text = models.TextField(
        blank=True,
        help_text="Custom text below company name in header",
    )
    footer_text = models.TextField(
        blank=True,
        help_text="Custom text at bottom of invoice (e.g., payment terms)",
    )

    class Meta:
        verbose_name = "Invoice Template"

    def __str__(self):
        return f"Invoice template for {self.tenant.name}"


class InvoiceTemplateReference(TimestampedModel):
    """Uploaded reference invoice PDF for data extraction and visual reference."""

    class ExtractionStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    template = models.ForeignKey(
        InvoiceTemplate,
        on_delete=models.CASCADE,
        related_name="references",
    )
    file = models.FileField(
        upload_to=reference_pdf_upload_path,
        help_text="Reference invoice PDF (max 20MB)",
    )
    original_filename = models.CharField(
        max_length=255,
        help_text="Original filename as uploaded by user",
    )
    file_size = models.PositiveIntegerField(
        help_text="File size in bytes",
    )
    extraction_status = models.CharField(
        max_length=10,
        choices=ExtractionStatus.choices,
        blank=True,
        default="",
        help_text="Status of data extraction from this PDF",
    )
    extracted_data = models.JSONField(
        null=True,
        blank=True,
        help_text="Extracted legal data, design, and layout from Claude API",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.original_filename


class InvoiceRecord(TenantModel):
    """A persisted invoice with assigned number and frozen data."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        FINALIZED = "finalized", "Finalized"
        CANCELLED = "cancelled", "Cancelled"

    contract = models.ForeignKey(
        "contracts.Contract",
        on_delete=models.SET_NULL,
        null=True,
        related_name="invoice_records",
    )
    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.SET_NULL,
        null=True,
        related_name="invoice_records",
    )

    # Invoice identification
    invoice_number = models.CharField(
        max_length=100,
        help_text="Assigned sequential invoice number",
    )

    # Billing period
    billing_date = models.DateField()
    period_start = models.DateField()
    period_end = models.DateField()

    # Amounts
    total_net = models.DecimalField(max_digits=12, decimal_places=2)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2)
    total_gross = models.DecimalField(max_digits=12, decimal_places=2)

    # Frozen snapshots
    line_items_snapshot = models.JSONField(
        help_text="Frozen copy of line items at generation time",
    )
    company_data_snapshot = models.JSONField(
        help_text="Frozen copy of company legal data at generation time",
    )

    # Metadata
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    generated_at = models.DateTimeField(auto_now_add=True)

    # Extra fields for display/export
    customer_name = models.CharField(max_length=255)
    contract_name = models.CharField(max_length=255)
    invoice_text = models.TextField(blank=True)

    class Meta:
        ordering = ["-billing_date", "-generated_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "invoice_number"],
                name="unique_invoice_number_per_tenant",
            ),
        ]

    def __str__(self):
        return f"Invoice {self.invoice_number} - {self.customer_name}"
