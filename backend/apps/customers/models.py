"""Customer models."""
from django.db import models

from apps.core.models import TenantModel


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
