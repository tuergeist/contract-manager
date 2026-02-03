"""Customer models."""
import os
import uuid

from django.db import models

from apps.core.models import TenantModel


def customer_attachment_upload_path(instance, filename):
    """
    Generate upload path: uploads/{tenant_id}/customers/{customer_id}/{uuid}_{ext}

    This structure enables:
    - Per-tenant backup/restore
    - Per-customer file organization
    - Unique filenames to prevent collisions
    - Easy S3 migration (sync with same path structure)
    """
    ext = os.path.splitext(filename)[1]
    unique_filename = f"{uuid.uuid4().hex}{ext}"
    return f"uploads/{instance.tenant_id}/customers/{instance.customer_id}/{unique_filename}"


class Customer(TenantModel):
    """A customer synced from Hubspot or created manually."""

    hubspot_id = models.CharField(max_length=100, blank=True, null=True)
    netsuite_customer_number = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Customer number from NetSuite (e.g., 'CUS174')",
    )
    name = models.CharField(max_length=255)
    address = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    synced_at = models.DateTimeField(null=True, blank=True)
    hubspot_deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["name"]
        unique_together = ["tenant", "hubspot_id"]

    def __str__(self):
        return self.name


class CustomerNote(TenantModel):
    """Notes attached to a customer."""

    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="notes",
    )
    user = models.ForeignKey(
        "tenants.User",
        on_delete=models.SET_NULL,
        null=True,
    )
    content = models.TextField()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Note for {self.customer.name}"


class CustomerAttachment(TenantModel):
    """A file attachment for a customer."""

    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="attachments",
    )
    file = models.FileField(upload_to=customer_attachment_upload_path)
    original_filename = models.CharField(
        max_length=255,
        help_text="Original filename as uploaded by user",
    )
    file_size = models.PositiveIntegerField(
        help_text="File size in bytes",
    )
    content_type = models.CharField(
        max_length=100,
        help_text="MIME type of the file",
    )
    uploaded_by = models.ForeignKey(
        "tenants.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="uploaded_customer_attachments",
    )
    description = models.TextField(
        blank=True,
        help_text="Optional description of the attachment",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.original_filename} ({self.customer.name})"

    def delete(self, *args, **kwargs):
        """Delete the file from storage when the model is deleted."""
        if self.file:
            self.file.delete(save=False)
        super().delete(*args, **kwargs)


class CustomerLink(TenantModel):
    """A named link attached to a customer."""

    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="links",
    )
    name = models.CharField(
        max_length=255,
        help_text="Display name for the link",
    )
    url = models.URLField(
        max_length=2000,
        help_text="URL of the link",
    )
    created_by = models.ForeignKey(
        "tenants.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_customer_links",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.customer.name})"
