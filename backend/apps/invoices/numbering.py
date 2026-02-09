"""Invoice numbering service for sequential, pattern-based number generation."""
import re
from datetime import date

from django.db import transaction
from django.db.models import F

from apps.invoices.models import InvoiceNumberScheme
from apps.tenants.models import Tenant


class InvoiceNumberService:
    """Generates unique sequential invoice numbers using configurable patterns."""

    def __init__(self, tenant: Tenant):
        self.tenant = tenant

    def get_next_number(self, billing_date: date) -> str:
        """
        Atomically increment the counter and return the formatted invoice number.

        Uses select_for_update() to prevent race conditions.
        Counter reset is handled based on the scheme's reset_period.
        """
        with transaction.atomic():
            scheme = self._get_or_create_scheme()

            # Lock the row for update
            scheme = (
                InvoiceNumberScheme.objects
                .select_for_update()
                .get(pk=scheme.pk)
            )

            # Check if counter needs reset
            self._maybe_reset_counter(scheme, billing_date)

            # Capture current counter value
            current_counter = scheme.next_counter

            # Atomically increment
            scheme.next_counter = F("next_counter") + 1
            scheme.save(update_fields=["next_counter", "updated_at"])

            # Format the number
            return self._format_number(scheme.pattern, billing_date, current_counter)

    def preview_next_number(self, billing_date: date | None = None) -> str:
        """Preview what the next invoice number would look like without incrementing."""
        if billing_date is None:
            billing_date = date.today()

        scheme = self._get_or_create_scheme()
        counter = scheme.next_counter

        # Simulate reset check
        if self._should_reset(scheme, billing_date):
            counter = 1

        return self._format_number(scheme.pattern, billing_date, counter)

    def _get_or_create_scheme(self) -> InvoiceNumberScheme:
        """Get existing scheme or create default."""
        scheme, _ = InvoiceNumberScheme.objects.get_or_create(
            tenant=self.tenant,
            defaults={
                "pattern": "{YYYY}-{NNNN}",
                "next_counter": 1,
                "reset_period": InvoiceNumberScheme.ResetPeriod.YEARLY,
            },
        )
        return scheme

    def _should_reset(self, scheme: InvoiceNumberScheme, billing_date: date) -> bool:
        """Check if the counter should be reset based on the reset period."""
        if scheme.reset_period == InvoiceNumberScheme.ResetPeriod.NEVER:
            return False

        if scheme.reset_period == InvoiceNumberScheme.ResetPeriod.YEARLY:
            return (
                scheme.last_reset_year is not None
                and billing_date.year != scheme.last_reset_year
            )

        if scheme.reset_period == InvoiceNumberScheme.ResetPeriod.MONTHLY:
            return (
                scheme.last_reset_year is not None
                and scheme.last_reset_month is not None
                and (
                    billing_date.year != scheme.last_reset_year
                    or billing_date.month != scheme.last_reset_month
                )
            )

        return False

    def _maybe_reset_counter(self, scheme: InvoiceNumberScheme, billing_date: date):
        """Reset counter if period boundary crossed. Updates scheme in place."""
        if self._should_reset(scheme, billing_date):
            scheme.next_counter = 1

        # Always update the last_reset tracking
        scheme.last_reset_year = billing_date.year
        scheme.last_reset_month = billing_date.month
        scheme.save(update_fields=[
            "next_counter", "last_reset_year", "last_reset_month", "updated_at",
        ])
        # Refresh to get the actual value after save
        scheme.refresh_from_db()

    @staticmethod
    def _format_number(pattern: str, billing_date: date, counter: int) -> str:
        """
        Replace placeholders in the pattern with actual values.

        Supported placeholders:
        - {YYYY}: 4-digit year
        - {YY}: 2-digit year
        - {MM}: 2-digit month
        - {NNN}: 3-digit zero-padded counter
        - {NNNN}: 4-digit zero-padded counter
        - {NNNNN}: 5-digit zero-padded counter
        """
        result = pattern
        result = result.replace("{YYYY}", f"{billing_date.year:04d}")
        result = result.replace("{YY}", f"{billing_date.year % 100:02d}")
        result = result.replace("{MM}", f"{billing_date.month:02d}")

        # Handle counter placeholders (longest first to avoid partial replacement)
        result = result.replace("{NNNNN}", f"{counter:05d}")
        result = result.replace("{NNNN}", f"{counter:04d}")
        result = result.replace("{NNN}", f"{counter:03d}")

        return result

    @staticmethod
    def validate_pattern(pattern: str) -> list[str]:
        """Validate a number pattern and return a list of errors (empty = valid)."""
        errors = []
        if not pattern:
            errors.append("Pattern cannot be empty.")
            return errors

        # Must contain at least one counter placeholder
        counter_placeholders = ["{NNN}", "{NNNN}", "{NNNNN}"]
        if not any(p in pattern for p in counter_placeholders):
            errors.append(
                "Pattern must contain at least one counter placeholder "
                "({NNN}, {NNNN}, or {NNNNN})."
            )

        # Check for invalid placeholders
        valid_placeholders = {"{YYYY}", "{YY}", "{MM}", "{NNN}", "{NNNN}", "{NNNNN}"}
        found = re.findall(r"\{[^}]+\}", pattern)
        for placeholder in found:
            if placeholder not in valid_placeholders:
                errors.append(f"Unknown placeholder: {placeholder}")

        return errors
