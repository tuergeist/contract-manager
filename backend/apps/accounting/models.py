"""Accounting models for SKR04 revenue account mapping and DATEV export."""
from django.db import models

from apps.core.models import TenantModel, TimestampedModel


class RevenueAccount(TenantModel):
    """SKR04 revenue account (Erlöskonto)."""

    account_number = models.CharField(
        max_length=10,
        help_text="SKR04 Kontonummer (z.B. '4400')",
    )
    name = models.CharField(
        max_length=255,
        help_text="Kontobezeichnung (z.B. 'Erlöse 19% USt')",
    )
    description = models.TextField(
        blank=True,
        help_text="Erläuterung / Hinweis zur Verwendung",
    )
    tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Erwarteter Steuersatz (zur Validierung, z.B. 19.00)",
    )
    vat_classification = models.CharField(
        max_length=10,
        choices=[
            ("domestic", "Inland"),
            ("eu", "EU (Reverse Charge)"),
            ("non_eu", "Drittland"),
            ("any", "Alle"),
        ],
        default="any",
        help_text="USt-Klassifizierung für automatische Zuordnung",
    )
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "account_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "account_number"],
                name="unique_revenue_account_per_tenant",
            ),
        ]

    def __str__(self):
        return f"{self.account_number} {self.name}"


class TaxAccount(TenantModel):
    """Tax account for VAT bookings (Steuerkonto / Gegenkonto)."""

    account_number = models.CharField(max_length=10)
    name = models.CharField(max_length=255)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["account_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "account_number"],
                name="unique_tax_account_per_tenant",
            ),
        ]

    def __str__(self):
        return f"{self.account_number} {self.name}"


class RevenueAccountMapping(TenantModel):
    """Mapping rule: tax rate / product → revenue account.

    Two mapping levels:
    A) Automatic by tax rate + VAT classification (standard):
       - domestic + 19% → 4400
       - domestic + 7%  → 4300
       - eu             → 4336
       - non_eu         → 4338

    B) Manual per product (exception, takes precedence):
       - Product X → always account 4400

    Priority (highest first):
    1. Product-specific + VAT classification
    2. Product-specific + any
    3. Tax rate + VAT classification (automatic)
    4. Tax rate + any
    5. Global fallback (no product, no tax rate, any)
    """

    product = models.ForeignKey(
        "products.Product",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="revenue_account_mappings",
        help_text="Specific product (for exceptions, takes precedence)",
    )
    tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Tax rate for automatic mapping (e.g. 19.00, 7.00, 0.00)",
    )
    vat_classification = models.CharField(
        max_length=10,
        choices=[
            ("domestic", "Inland"),
            ("eu", "EU (Reverse Charge)"),
            ("non_eu", "Drittland"),
            ("any", "Alle (Fallback)"),
        ],
        default="any",
    )
    revenue_account = models.ForeignKey(
        RevenueAccount,
        on_delete=models.PROTECT,
        related_name="mappings",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "product", "tax_rate", "vat_classification"],
                name="unique_revenue_mapping",
            ),
        ]

    def __str__(self):
        parts = []
        if self.product:
            parts.append(f"Product: {self.product.name}")
        if self.tax_rate is not None:
            parts.append(f"Tax: {self.tax_rate}%")
        parts.append(f"VAT: {self.vat_classification}")
        parts.append(f"→ {self.revenue_account.account_number}")
        return " | ".join(parts)


class DebitorAccount(TenantModel):
    """Debtor account: link between customer and accounting.

    The account number can remain empty and is assigned before export —
    manually or automatically. This allows importing existing DATEV numbers.
    """

    customer = models.OneToOneField(
        "customers.Customer",
        on_delete=models.CASCADE,
        related_name="debitor_account",
    )
    account_number = models.CharField(
        max_length=10,
        blank=True,
        default="",
        help_text="DATEV account number (e.g. '10001'). Empty = not yet assigned.",
    )
    notes = models.TextField(
        blank=True,
        help_text="Notes (e.g. 'Legacy system: D-4711')",
    )

    class Meta:
        ordering = ["account_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "account_number"],
                condition=models.Q(account_number__gt=""),
                name="unique_debitor_number_per_tenant",
            ),
        ]

    def __str__(self):
        num = self.account_number or "(no number)"
        return f"Debitor {num} – {self.customer}"


class DebitorAccountScheme(TimestampedModel):
    """Configuration for automatic debtor account number assignment."""

    tenant = models.OneToOneField(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        related_name="debitor_account_scheme",
    )
    prefix = models.CharField(
        max_length=5,
        default="",
        blank=True,
        help_text="Optional prefix (e.g. 'D' → D10001)",
    )
    start_number = models.PositiveIntegerField(
        default=10000,
        help_text="Start number for debtor accounts (SKR04 default: 10000)",
    )
    next_number = models.PositiveIntegerField(
        default=10001,
        help_text="Next number to be assigned",
    )
    end_number = models.PositiveIntegerField(
        default=69999,
        help_text="Maximum allowed number (SKR04 default: 69999)",
    )

    def __str__(self):
        return f"Debitor scheme for {self.tenant.name}: {self.prefix}{self.next_number}"


class BookingEntry(TenantModel):
    """A single booking entry generated from an invoice."""

    invoice_record = models.ForeignKey(
        "invoices.InvoiceRecord",
        on_delete=models.CASCADE,
        related_name="booking_entries",
    )
    booking_date = models.DateField(
        help_text="Booking date (= invoice date)",
    )
    debit_account = models.CharField(
        max_length=10,
        help_text="Debit account (Soll — debtor or revenue account)",
    )
    credit_account = models.CharField(
        max_length=10,
        help_text="Credit account (Haben — revenue or tax account)",
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )
    tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
    )
    tax_key = models.CharField(
        max_length=5,
        blank=True,
        help_text="DATEV tax key / BU-Schlüssel (e.g. '9' for 19% USt)",
    )
    description = models.CharField(
        max_length=255,
        help_text="Booking text (e.g. 'RE 2026-0042 / Customer XY / Product Z')",
    )
    cost_center = models.CharField(
        max_length=20,
        blank=True,
        help_text="Optional cost center (KOST1)",
    )
    line_item_snapshot = models.JSONField(
        null=True,
        blank=True,
        help_text="Snapshot of the line item at booking time",
    )

    class Meta:
        ordering = ["booking_date", "invoice_record", "id"]
        indexes = [
            models.Index(fields=["tenant", "booking_date"]),
            models.Index(fields=["tenant", "debit_account"]),
            models.Index(fields=["tenant", "credit_account"]),
        ]

    def __str__(self):
        return f"{self.debit_account} → {self.credit_account}: {self.amount}"


def accounting_export_upload_path(instance, filename):
    """Upload path for accounting exports."""
    import uuid as _uuid

    unique = _uuid.uuid4().hex
    return f"uploads/{instance.tenant_id}/accounting/exports/{unique}.csv"


class AccountingExport(TenantModel):
    """Tracking of DATEV exports."""

    class ExportFormat(models.TextChoices):
        DATEV_CSV = "datev_csv", "DATEV Buchungsstapel (CSV)"

    period_start = models.DateField()
    period_end = models.DateField()
    export_format = models.CharField(
        max_length=20,
        choices=ExportFormat.choices,
        default=ExportFormat.DATEV_CSV,
    )
    file = models.FileField(
        upload_to=accounting_export_upload_path,
        blank=True,
    )
    entry_count = models.PositiveIntegerField(default=0)
    total_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
    )
    exported_by = models.ForeignKey(
        "tenants.User",
        on_delete=models.SET_NULL,
        null=True,
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Export {self.period_start} – {self.period_end} ({self.entry_count} entries)"
