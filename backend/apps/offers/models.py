"""Offer models for persistent offers, numbering, and lifecycle management."""
import os
import uuid

from django.db import models

from apps.core.models import TenantModel, TimestampedModel


def offer_record_upload_path(instance, filename):
    """Upload path: uploads/{tenant_id}/offers/generated/{uuid}.pdf"""
    unique_filename = f"{uuid.uuid4().hex}.pdf"
    return f"uploads/{instance.tenant_id}/offers/generated/{unique_filename}"


class OfferNumberScheme(TimestampedModel):
    """Configurable offer number pattern per tenant."""

    class ResetPeriod(models.TextChoices):
        YEARLY = "yearly", "Yearly"
        MONTHLY = "monthly", "Monthly"
        NEVER = "never", "Never"

    tenant = models.OneToOneField(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        related_name="offer_number_scheme",
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
        verbose_name = "Offer Number Scheme"

    def __str__(self):
        return f"Offer number scheme for {self.tenant.name}: {self.pattern}"


class OfferRecord(TenantModel):
    """A persisted offer with assigned number and frozen data."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SENT = "sent", "Sent"
        FINALIZED = "finalized", "Finalized"
        # Legacy values kept for backwards compatibility with existing rows
        # and for read-only display in the offer list. They MUST NOT be used
        # as the target of a new transition. The supported lifecycle is:
        #   draft -> sent       (system: on successful email_sent_at)
        #   draft -> finalized  (user: explicit Finalize action)
        ACCEPTED = "accepted", "Accepted (legacy)"
        REJECTED = "rejected", "Rejected (legacy)"
        CANCELLED = "cancelled", "Cancelled (legacy)"

    contract = models.ForeignKey(
        "contracts.Contract",
        on_delete=models.SET_NULL,
        null=True,
        related_name="offer_records",
    )
    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.SET_NULL,
        null=True,
        related_name="offer_records",
    )

    # Offer identification
    offer_number = models.CharField(
        max_length=100,
        help_text="Assigned sequential offer number",
    )

    # Dates
    offer_date = models.DateField(
        help_text="The date shown on the offer",
    )
    valid_until = models.DateField(
        null=True,
        blank=True,
        help_text="Offer validity expiration date",
    )
    billing_date = models.DateField(
        help_text="The billing date from the forecast event",
    )
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

    # Display fields
    customer_name = models.CharField(max_length=255)
    contract_name = models.CharField(max_length=255)
    notes = models.TextField(blank=True, help_text="Offer conditions/notes (rendered in PDF)")
    pdf_file = models.FileField(upload_to=offer_record_upload_path, blank=True)

    # Frozen VAT sentence
    vat_sentence = models.TextField(blank=True, help_text="Frozen VAT sentence at generation time")

    # Scoped item IDs (for offers covering a subset of contract items)
    scoped_item_ids = models.JSONField(
        null=True,
        blank=True,
        help_text="List of contract item IDs this offer covers. Null = all items.",
    )

    # User-editable free-form Markdown blocks rendered in the PDF.
    free_text_after_items = models.TextField(
        blank=True,
        default="",
        help_text="Markdown rendered directly below the line-item table.",
    )
    free_text_before_terms = models.TextField(
        blank=True,
        default="",
        help_text="Markdown rendered directly above the VAT block and any T&C section.",
    )

    # Snapshotted from contract.min_duration_months / notice_period_months at
    # create time; user-overridable on drafts. Rendered into the PDF only when
    # set and greater than zero.
    minimum_term_months = models.PositiveIntegerField(null=True, blank=True)
    notice_period_months = models.PositiveIntegerField(null=True, blank=True)

    # Set when this offer was produced by "Copy to edit" on a locked source.
    # SET_NULL so deleting the source does not cascade-destroy the clone audit
    # trail.
    cloned_from = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="clones",
    )

    # Email sending tracking
    email_sent_at = models.DateTimeField(null=True, blank=True)
    email_sent_to = models.JSONField(default=list, blank=True)
    email_message_id = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-offer_date", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "offer_number"],
                name="unique_offer_number_per_tenant",
            ),
        ]

    def __str__(self):
        return f"Offer {self.offer_number} - {self.customer_name}"

    # ------------------------------------------------------------------ #
    # Field-group contract — single source of truth for what re-create
    # overwrites vs what update_offer mutates. See
    # openspec/specs/offer-edit/spec.md and design.md::Decision 1.
    # ------------------------------------------------------------------ #
    @classmethod
    def _contract_derived_fields(cls) -> frozenset[str]:
        """Fields rewritten by recreate_offer_from_contract."""
        return frozenset({
            "line_items_snapshot",
            "company_data_snapshot",
            "customer_name",
            "contract_name",
            "period_start",
            "period_end",
            "billing_date",
            "total_net",
            "tax_rate",
            "tax_amount",
            "total_gross",
            "vat_sentence",
        })

    @classmethod
    def _user_editable_fields(cls) -> frozenset[str]:
        """Fields accepted by update_offer; preserved by re-create."""
        return frozenset({
            "free_text_after_items",
            "free_text_before_terms",
            "valid_until",
            "minimum_term_months",
            "notice_period_months",
            "scoped_item_ids",
        })

    @property
    def is_locked(self) -> bool:
        """True when the offer is in a terminal locked status."""
        return self.status in (
            self.Status.SENT,
            self.Status.FINALIZED,
        )
