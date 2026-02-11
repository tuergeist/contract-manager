"""Core models and mixins used across the application."""
from django.db import models


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


class StorageMigration(models.Model):
    """Tracks files migrated from local storage to object storage."""

    file_path = models.CharField(max_length=500, unique=True)
    migrated_at = models.DateTimeField(auto_now_add=True)
    source = models.CharField(max_length=20, default="local")
    destination = models.CharField(max_length=20, default="s3")

    class Meta:
        verbose_name = "Storage Migration"
        verbose_name_plural = "Storage Migrations"

    def __str__(self):
        return f"{self.file_path} ({self.source} -> {self.destination})"
