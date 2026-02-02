"""Audit log models."""

from django.db import models

from apps.core.models import TenantModel


class AuditLog(TenantModel):
    """Audit log entry for tracking entity changes."""

    class Action(models.TextChoices):
        """Action types for audit log entries."""

        CREATE = "create", "Create"
        UPDATE = "update", "Update"
        DELETE = "delete", "Delete"

    action = models.CharField(
        max_length=10,
        choices=Action.choices,
        help_text="The type of action performed",
    )
    entity_type = models.CharField(
        max_length=100,
        help_text="The type of entity that was changed (e.g., 'contract', 'customer')",
    )
    entity_id = models.IntegerField(
        help_text="The ID of the entity that was changed",
    )
    entity_repr = models.CharField(
        max_length=255,
        help_text="Human-readable representation of the entity at the time of change",
    )
    user = models.ForeignKey(
        "tenants.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
        help_text="The user who made the change (null for system changes)",
    )
    changes = models.JSONField(
        default=dict,
        help_text="JSON object containing field changes with old/new values",
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        help_text="When the change occurred",
    )
    # For tracking related entities (e.g., contract_id for contract items)
    parent_entity_type = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Parent entity type for related entities",
    )
    parent_entity_id = models.IntegerField(
        null=True,
        blank=True,
        help_text="Parent entity ID for related entities",
    )

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["entity_type", "entity_id"]),
            models.Index(fields=["entity_type"]),
            models.Index(fields=["user"]),
            models.Index(fields=["timestamp"]),
            models.Index(fields=["tenant", "timestamp"]),
            models.Index(fields=["parent_entity_type", "parent_entity_id"]),
        ]

    def __str__(self):
        return f"{self.action} {self.entity_type}:{self.entity_id} by {self.user or 'system'}"
