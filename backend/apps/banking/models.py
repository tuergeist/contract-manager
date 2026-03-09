"""Banking models for bank account and transaction management."""
import hashlib
import uuid
from decimal import Decimal

from django.db import models

from apps.core.models import TenantModel


class CostCenter(TenantModel):
    """A cost center (Kostenstelle) for categorizing transactions."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=20, help_text="Short code, e.g. 100, IT, MKTG")
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "code"],
                name="unique_cost_center_code_per_tenant",
            ),
        ]
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} – {self.name}"


class Counterparty(TenantModel):
    """A counterparty (business partner) that appears in bank transactions."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    iban = models.CharField(max_length=50, blank=True)
    bic = models.CharField(max_length=20, blank=True)
    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="counterparties",
        help_text="Linked customer for payment matching",
    )
    default_cost_center = models.ForeignKey(
        CostCenter,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="counterparties",
        help_text="Default cost center for new transactions with this counterparty",
    )

    class Meta:
        verbose_name_plural = "counterparties"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "name"],
                name="unique_counterparty_name_per_tenant",
            ),
        ]
        ordering = ["name"]
        indexes = [
            models.Index(fields=["tenant", "name"], name="idx_counterparty_tenant_name"),
        ]

    def __str__(self):
        return self.name


class BankAccount(TenantModel):
    """A bank account that MT940 statements can be imported into."""

    name = models.CharField(max_length=255, help_text="User-given label")
    bank_code = models.CharField(
        max_length=20, help_text="BLZ / routing number from MT940 :25: field"
    )
    account_number = models.CharField(
        max_length=30, help_text="Account number from MT940 :25: field"
    )
    iban = models.CharField(max_length=50, blank=True)
    bic = models.CharField(max_length=20, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "bank_code", "account_number"],
                name="unique_bank_account_per_tenant",
            ),
        ]
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.bank_code}/{self.account_number})"


class BankTransaction(TenantModel):
    """A single bank transaction parsed from an MT940 statement."""

    account = models.ForeignKey(
        BankAccount,
        on_delete=models.CASCADE,
        related_name="transactions",
    )
    entry_date = models.DateField(help_text="Booking date from :61: field")
    value_date = models.DateField(
        null=True, blank=True, help_text="Value/settlement date from :61: field"
    )
    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        help_text="Positive for credit, negative for debit",
    )
    currency = models.CharField(max_length=3, default="EUR")
    transaction_type = models.CharField(
        max_length=10, blank=True, help_text="SWIFT type code (e.g. NTRF, NDDT)"
    )
    counterparty = models.ForeignKey(
        Counterparty,
        on_delete=models.PROTECT,
        related_name="transactions",
        help_text="Reference to counterparty entity",
    )
    cost_center = models.ForeignKey(
        CostCenter,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transactions",
        help_text="Cost center assignment",
    )
    booking_text = models.TextField(
        blank=True, help_text="Verwendungszweck from :86: ?20-?29 subfields"
    )
    reference = models.CharField(
        max_length=500, blank=True, help_text="EREF/KREF/MREF combined"
    )
    raw_data = models.TextField(
        blank=True, help_text="Full :86: field content for debugging"
    )
    opening_balance = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    closing_balance = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    import_hash = models.CharField(
        max_length=64, help_text="SHA256 hash for deduplication"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "import_hash"],
                name="unique_transaction_hash_per_tenant",
            ),
        ]
        indexes = [
            models.Index(
                fields=["tenant", "account", "entry_date"],
                name="idx_txn_tenant_account_date",
            ),
            models.Index(fields=["amount"], name="idx_txn_amount"),
            models.Index(fields=["counterparty"], name="idx_txn_counterparty"),
        ]
        ordering = ["-entry_date", "-id"]

    def __str__(self):
        return f"{self.entry_date} {self.counterparty.name} {self.amount}"

    @staticmethod
    def compute_hash(
        account_id: int,
        entry_date,
        amount: Decimal,
        currency: str,
        reference: str,
        counterparty_name: str,
    ) -> str:
        """Compute deterministic SHA256 hash for deduplication."""
        raw = f"{account_id}|{entry_date}|{amount}|{currency}|{reference}|{counterparty_name}"
        return hashlib.sha256(raw.encode()).hexdigest()


class CostCenterSplitRule(TenantModel):
    """A rule for automatically splitting transactions across cost centers."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    counterparty = models.ForeignKey(
        Counterparty,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="split_rules",
        help_text="Match transactions with this counterparty",
    )
    booking_text_pattern = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Regex or substring pattern to match booking text",
    )
    priority = models.IntegerField(
        default=0,
        help_text="Higher priority rules are evaluated first",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-priority", "id"]
        constraints = [
            models.CheckConstraint(
                check=~models.Q(counterparty__isnull=True, booking_text_pattern__isnull=True)
                & ~models.Q(counterparty__isnull=True, booking_text_pattern=""),
                name="split_rule_must_have_matcher",
            ),
        ]

    def __str__(self):
        if self.counterparty:
            return f"Split rule: {self.counterparty.name} (priority {self.priority})"
        return f"Split rule: pattern '{self.booking_text_pattern}' (priority {self.priority})"


class CostCenterSplitAllocation(models.Model):
    """An allocation line within a split rule."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rule = models.ForeignKey(
        CostCenterSplitRule,
        on_delete=models.CASCADE,
        related_name="allocations",
    )
    cost_center = models.ForeignKey(
        CostCenter,
        on_delete=models.CASCADE,
        related_name="split_allocations",
    )
    percentage = models.DecimalField(
        max_digits=7,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Percentage of transaction amount (0-100)",
    )
    fixed_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Fixed amount to allocate",
    )

    class Meta:
        ordering = ["id"]

    def __str__(self):
        if self.percentage is not None:
            return f"{self.cost_center.code}: {self.percentage}%"
        return f"{self.cost_center.code}: {self.fixed_amount} fixed"


class TransactionCostCenterSplit(models.Model):
    """An actual cost center split applied to a transaction."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    transaction = models.ForeignKey(
        "BankTransaction",
        on_delete=models.CASCADE,
        related_name="cost_center_splits",
    )
    cost_center = models.ForeignKey(
        CostCenter,
        on_delete=models.CASCADE,
        related_name="transaction_splits",
    )
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    is_manual = models.BooleanField(default=False)
    rule = models.ForeignKey(
        CostCenterSplitRule,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="applied_splits",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.transaction} → {self.cost_center.code}: {self.amount}"


class RecurringPattern(TenantModel):
    """A detected recurring payment pattern from bank transactions."""

    class Frequency(models.TextChoices):
        MONTHLY = "monthly", "Monthly"
        QUARTERLY = "quarterly", "Quarterly"
        SEMI_ANNUAL = "semi_annual", "Semi-Annual"
        ANNUAL = "annual", "Annual"
        IRREGULAR = "irregular", "Irregular"

    counterparty = models.ForeignKey(
        Counterparty,
        on_delete=models.PROTECT,
        related_name="recurring_patterns",
        help_text="Reference to counterparty entity",
    )
    average_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        help_text="Average transaction amount (negative for costs)",
    )
    frequency = models.CharField(
        max_length=20,
        choices=Frequency.choices,
        default=Frequency.MONTHLY,
    )
    day_of_month = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="Typical day of month for payment (1-31)",
    )
    confidence_score = models.FloatField(
        default=0.0,
        help_text="Detection confidence (0.0-1.0)",
    )
    is_confirmed = models.BooleanField(
        default=False,
        help_text="User has confirmed this pattern",
    )
    is_ignored = models.BooleanField(
        default=False,
        help_text="User has dismissed this pattern",
    )
    is_paused = models.BooleanField(
        default=False,
        help_text="Temporarily excluded from projections",
    )
    last_occurrence = models.DateField(
        null=True,
        blank=True,
        help_text="Date of most recent matching transaction",
    )
    source_transactions = models.ManyToManyField(
        BankTransaction,
        related_name="recurring_patterns",
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-confidence_score", "-last_occurrence"]
        indexes = [
            models.Index(
                fields=["tenant", "is_confirmed", "is_ignored"],
                name="idx_pattern_tenant_status",
            ),
        ]

    def __str__(self):
        return f"{self.counterparty.name} ({self.frequency}) {self.average_amount}"


def incoming_invoice_upload_path(instance, filename):
    unique_filename = f"{uuid.uuid4().hex}.pdf"
    return f"uploads/{instance.tenant_id}/incoming_invoices/{unique_filename}"


class InvoiceInbox(TenantModel):
    class InboxType(models.TextChoices):
        IMAP = "imap", "IMAP"
        M365 = "m365", "Microsoft 365"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    inbox_type = models.CharField(max_length=10, choices=InboxType.choices, default=InboxType.IMAP)
    host = models.CharField(max_length=255, blank=True)
    port = models.PositiveIntegerField(default=993)
    username = models.CharField(max_length=255, blank=True)
    password = models.CharField(max_length=500, blank=True)
    folder = models.CharField(max_length=255, default="INBOX")
    use_ssl = models.BooleanField(default=True)
    m365_mailbox = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    poll_interval_minutes = models.PositiveIntegerField(default=15)
    last_polled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.get_inbox_type_display()})"


class IncomingInvoice(TenantModel):
    class ExtractionStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        EXTRACTING = "extracting", "Extracting"
        EXTRACTED = "extracted", "Extracted"
        EXTRACTION_FAILED = "extraction_failed", "Extraction Failed"
        CONFIRMED = "confirmed", "Confirmed"
        MATCHED = "matched", "Matched"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    inbox = models.ForeignKey(InvoiceInbox, on_delete=models.SET_NULL, null=True, blank=True, related_name="incoming_invoices")
    counterparty = models.ForeignKey(Counterparty, on_delete=models.SET_NULL, null=True, blank=True, related_name="incoming_invoices")
    supplier_name = models.CharField(max_length=255, blank=True)
    invoice_number = models.CharField(max_length=100, blank=True)
    invoice_date = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    net_amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    vat_amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    gross_amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, default="EUR")
    pdf_file = models.FileField(upload_to=incoming_invoice_upload_path)
    original_filename = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField(default=0)
    extraction_status = models.CharField(max_length=20, choices=ExtractionStatus.choices, default=ExtractionStatus.PENDING)
    extraction_error = models.TextField(blank=True)
    email_message_id = models.CharField(max_length=500, blank=True)
    source_email_subject = models.CharField(max_length=500, blank=True)
    source_email_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "email_message_id", "original_filename"],
                name="unique_incoming_invoice_per_tenant_email",
                condition=models.Q(email_message_id__gt=""),
            ),
        ]
        indexes = [
            models.Index(fields=["tenant", "extraction_status"], name="idx_incoming_inv_tenant_status"),
        ]

    def __str__(self):
        return f"{self.supplier_name or 'Unknown'} - {self.invoice_number or self.original_filename}"
