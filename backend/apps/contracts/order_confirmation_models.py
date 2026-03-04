"""Order confirmation (Auftragsbestätigung) models."""
import os
import uuid

from django.db import models

from apps.core.models import TenantModel, TimestampedModel


def ab_pdf_upload_path(instance, filename):
    """Generate upload path for AB PDFs."""
    ext = os.path.splitext(filename)[1] or ".pdf"
    return f"uploads/{instance.tenant_id}/order_confirmations/{uuid.uuid4().hex}{ext}"


class OrderConfirmationNumberScheme(TimestampedModel):
    """Configurable order confirmation number pattern per tenant."""

    class ResetPeriod(models.TextChoices):
        YEARLY = "yearly", "Yearly"
        MONTHLY = "monthly", "Monthly"
        NEVER = "never", "Never"

    tenant = models.OneToOneField(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        related_name="order_confirmation_number_scheme",
    )
    pattern = models.CharField(
        max_length=100,
        default="AB-{YYYY}-{NNNN}",
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
        verbose_name = "Order Confirmation Number Scheme"

    def __str__(self):
        return f"AB number scheme for {self.tenant.name}: {self.pattern}"


class OrderConfirmation(TenantModel):
    """An order confirmation (Auftragsbestätigung) linked to a contract."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SENT = "sent", "Sent"

    contract = models.ForeignKey(
        "contracts.Contract",
        on_delete=models.CASCADE,
        related_name="order_confirmations",
    )
    created_by = models.ForeignKey(
        "tenants.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_order_confirmations",
    )
    order_confirmation_number = models.CharField(
        max_length=100,
        blank=True,
    )
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    personal_message = models.TextField(
        blank=True,
        help_text="Optional personal message from the sender",
    )
    include_message_in_pdf = models.BooleanField(
        default=True,
        help_text="Include personal message in the PDF document",
    )
    include_message_in_email = models.BooleanField(
        default=True,
        help_text="Include personal message in the email body",
    )
    additional_emails = models.JSONField(
        default=list,
        blank=True,
        help_text="Additional email addresses beyond billing contacts",
    )
    language = models.CharField(
        max_length=5,
        default="de",
        help_text="Language for the AB document (de/en)",
    )
    pdf_file = models.FileField(
        upload_to=ab_pdf_upload_path,
        blank=True,
        null=True,
    )
    sent_at = models.DateTimeField(null=True, blank=True)
    sent_to = models.JSONField(
        default=list,
        blank=True,
        help_text="List of email addresses the AB was sent to",
    )
    email_message_id = models.CharField(
        max_length=255,
        blank=True,
        help_text="Microsoft Graph API message ID",
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant", "order_confirmation_number"]),
        ]

    def __str__(self):
        return f"AB {self.order_confirmation_number} for {self.contract}"
