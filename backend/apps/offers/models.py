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
        ACCEPTED = "accepted", "Accepted"
        REJECTED = "rejected", "Rejected"
        CANCELLED = "cancelled", "Cancelled"

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
