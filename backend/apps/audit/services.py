"""Audit logging service."""

import threading
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from django.db import models

from apps.audit.models import AuditLog


# Thread-local storage for current user
_thread_locals = threading.local()


def set_current_user(user):
    """Set the current user for audit logging in this thread."""
    _thread_locals.user = user


def get_current_user():
    """Get the current user for audit logging from this thread."""
    return getattr(_thread_locals, "user", None)


def clear_current_user():
    """Clear the current user from thread-local storage."""
    if hasattr(_thread_locals, "user"):
        del _thread_locals.user


class AuditLogService:
    """Service for creating audit log entries."""

    # Models to audit and their entity type names
    AUDITED_MODELS = {}

    # Fields to exclude from change tracking
    EXCLUDED_FIELDS = {"created_at", "updated_at", "id", "tenant", "tenant_id"}

    # Parent relationship mappings (child_type -> (parent_type, parent_field))
    PARENT_RELATIONSHIPS = {}

    # Multi-parent relationship mappings for entities that can have different parent types
    # Maps entity_type -> [(parent_type, parent_field), ...]
    MULTI_PARENT_RELATIONSHIPS = {}

    @classmethod
    def register_model(cls, model_class, entity_type: str, parent_field: str = None, parent_type: str = None):
        """Register a model for audit logging.

        Args:
            model_class: The Django model class to audit
            entity_type: The entity type name for audit logs
            parent_field: Optional field name that references the parent entity
            parent_type: Optional parent entity type name
        """
        cls.AUDITED_MODELS[model_class] = entity_type
        if parent_field and parent_type:
            cls.PARENT_RELATIONSHIPS[entity_type] = (parent_type, parent_field)

    @classmethod
    def register_model_multi_parent(
        cls, model_class, entity_type: str, parent_fields: list[tuple[str, str]]
    ):
        """Register a model that can have different parent types.

        Args:
            model_class: The Django model class to audit
            entity_type: The entity type name for audit logs
            parent_fields: List of (parent_type, parent_field) tuples to check in order
        """
        cls.AUDITED_MODELS[model_class] = entity_type
        cls.MULTI_PARENT_RELATIONSHIPS[entity_type] = parent_fields

    @classmethod
    def is_audited(cls, model_class) -> bool:
        """Check if a model class is registered for auditing."""
        return model_class in cls.AUDITED_MODELS

    @classmethod
    def get_entity_type(cls, model_class) -> str | None:
        """Get the entity type name for a model class."""
        return cls.AUDITED_MODELS.get(model_class)

    @classmethod
    def serialize_value(cls, value: Any) -> Any:
        """Serialize a field value for JSON storage."""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, date):
            return value.isoformat()
        if isinstance(value, Decimal):
            return str(value)
        if isinstance(value, models.Model):
            return value.pk
        if hasattr(value, "__iter__") and not isinstance(value, (str, bytes, dict)):
            return [cls.serialize_value(v) for v in value]
        return value

    @classmethod
    def get_model_fields(cls, instance: models.Model) -> dict[str, Any]:
        """Get all field values from a model instance."""
        fields = {}
        for field in instance._meta.get_fields():
            # Skip excluded and non-concrete fields
            if field.name in cls.EXCLUDED_FIELDS:
                continue
            if not field.concrete or field.many_to_many:
                continue
            if hasattr(field, "related_model") and field.related_model:
                # Foreign key - store the ID
                value = getattr(instance, f"{field.name}_id", None)
            else:
                value = getattr(instance, field.name, None)
            fields[field.name] = cls.serialize_value(value)
        return fields

    @classmethod
    def compute_diff(cls, old_values: dict, new_values: dict) -> dict[str, dict]:
        """Compute the difference between old and new field values.

        Returns:
            Dict mapping field names to {"old": value, "new": value}
        """
        changes = {}
        all_fields = set(old_values.keys()) | set(new_values.keys())

        for field in all_fields:
            old_val = old_values.get(field)
            new_val = new_values.get(field)
            if old_val != new_val:
                changes[field] = {"old": old_val, "new": new_val}

        return changes

    @classmethod
    def get_entity_repr(cls, instance: models.Model) -> str:
        """Get a human-readable representation of an entity."""
        if hasattr(instance, "name") and instance.name:
            return str(instance.name)
        return str(instance)

    @classmethod
    def get_parent_info(cls, instance: models.Model, entity_type: str) -> tuple[str | None, int | None]:
        """Get parent entity information for related entities."""
        # Check single parent relationship first
        if entity_type in cls.PARENT_RELATIONSHIPS:
            parent_type, parent_field = cls.PARENT_RELATIONSHIPS[entity_type]
            parent_id = getattr(instance, f"{parent_field}_id", None)
            return parent_type, parent_id

        # Check multi-parent relationships (first non-null parent wins)
        if entity_type in cls.MULTI_PARENT_RELATIONSHIPS:
            for parent_type, parent_field in cls.MULTI_PARENT_RELATIONSHIPS[entity_type]:
                parent_id = getattr(instance, f"{parent_field}_id", None)
                if parent_id is not None:
                    return parent_type, parent_id

        return None, None

    @classmethod
    def log_create(cls, instance: models.Model) -> AuditLog | None:
        """Log a create action for an entity."""
        entity_type = cls.get_entity_type(type(instance))
        if not entity_type:
            return None

        fields = cls.get_model_fields(instance)
        changes = {field: {"old": None, "new": value} for field, value in fields.items()}

        parent_type, parent_id = cls.get_parent_info(instance, entity_type)

        return AuditLog.objects.create(
            tenant=instance.tenant,
            action=AuditLog.Action.CREATE,
            entity_type=entity_type,
            entity_id=instance.pk,
            entity_repr=cls.get_entity_repr(instance),
            user=get_current_user(),
            changes=changes,
            parent_entity_type=parent_type,
            parent_entity_id=parent_id,
        )

    @classmethod
    def log_update(cls, instance: models.Model, old_values: dict) -> AuditLog | None:
        """Log an update action for an entity."""
        entity_type = cls.get_entity_type(type(instance))
        if not entity_type:
            return None

        new_values = cls.get_model_fields(instance)
        changes = cls.compute_diff(old_values, new_values)

        # Don't create a log entry if nothing changed
        if not changes:
            return None

        parent_type, parent_id = cls.get_parent_info(instance, entity_type)

        return AuditLog.objects.create(
            tenant=instance.tenant,
            action=AuditLog.Action.UPDATE,
            entity_type=entity_type,
            entity_id=instance.pk,
            entity_repr=cls.get_entity_repr(instance),
            user=get_current_user(),
            changes=changes,
            parent_entity_type=parent_type,
            parent_entity_id=parent_id,
        )

    @classmethod
    def log_delete(cls, instance: models.Model) -> AuditLog | None:
        """Log a delete action for an entity."""
        entity_type = cls.get_entity_type(type(instance))
        if not entity_type:
            return None

        fields = cls.get_model_fields(instance)
        changes = {field: {"old": value, "new": None} for field, value in fields.items()}

        parent_type, parent_id = cls.get_parent_info(instance, entity_type)

        return AuditLog.objects.create(
            tenant=instance.tenant,
            action=AuditLog.Action.DELETE,
            entity_type=entity_type,
            entity_id=instance.pk,
            entity_repr=cls.get_entity_repr(instance),
            user=get_current_user(),
            changes=changes,
            parent_entity_type=parent_type,
            parent_entity_id=parent_id,
        )
