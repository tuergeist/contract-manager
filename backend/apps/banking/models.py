"""Banking models for bank account and transaction management."""
import hashlib
from decimal import Decimal

from django.db import models

from apps.core.models import TenantModel


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
    counterparty_name = models.CharField(max_length=255, blank=True)
    counterparty_iban = models.CharField(max_length=50, blank=True)
    counterparty_bic = models.CharField(max_length=20, blank=True)
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
            models.Index(fields=["counterparty_name"], name="idx_txn_counterparty"),
        ]
        ordering = ["-entry_date", "-id"]

    def __str__(self):
        return f"{self.entry_date} {self.counterparty_name} {self.amount}"

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


class RecurringPattern(TenantModel):
    """A detected recurring payment pattern from bank transactions."""

    class Frequency(models.TextChoices):
        MONTHLY = "monthly", "Monthly"
        QUARTERLY = "quarterly", "Quarterly"
        SEMI_ANNUAL = "semi_annual", "Semi-Annual"
        ANNUAL = "annual", "Annual"
        IRREGULAR = "irregular", "Irregular"

    counterparty_name = models.CharField(max_length=255)
    counterparty_iban = models.CharField(max_length=50, blank=True)
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
        return f"{self.counterparty_name} ({self.frequency}) {self.average_amount}"
