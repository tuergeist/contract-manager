"""Core models and mixins used across the application."""
from django.db import models


class RevenueType(models.TextChoices):
    ADVANCED_DEVELOPMENT = "advanced_development", "Advanced Development"
    TRAINING_IMPLEMENTATION = "training_implementation", "Training + Implementation"
    RECURRING = "recurring", "Recurring Revenue"


class TimestampedModel(models.Model):
    """Abstract base model with created and modified timestamps."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class TenantModel(TimestampedModel):
    """Abstract base model for multi-tenant models."""

    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        related_name="%(class)s_set",
    )

    class Meta:
        abstract = True
