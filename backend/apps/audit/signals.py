"""Signal handlers for audit logging."""

from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from apps.audit.services import AuditLogService

# Storage for pre-save snapshots keyed by (model_class, pk)
_pre_save_snapshots = {}


def _get_snapshot_key(instance):
    """Get a unique key for storing pre-save snapshots."""
    return (type(instance), instance.pk)


@receiver(pre_save)
def audit_pre_save(sender, instance, **kwargs):
    """Capture the current state before saving for diff computation."""
    if not AuditLogService.is_audited(sender):
        return

    # Only capture existing instances (updates, not creates)
    if instance.pk is None:
        return

    try:
        # Fetch the current state from the database
        current = sender.objects.get(pk=instance.pk)
        _pre_save_snapshots[_get_snapshot_key(instance)] = AuditLogService.get_model_fields(current)
    except sender.DoesNotExist:
        # Instance doesn't exist yet (shouldn't happen if pk is set, but defensive)
        pass


@receiver(post_save)
def audit_post_save(sender, instance, created, **kwargs):
    """Create audit log entry after save."""
    if not AuditLogService.is_audited(sender):
        return

    if created:
        AuditLogService.log_create(instance)
    else:
        # Get the pre-save snapshot
        key = _get_snapshot_key(instance)
        old_values = _pre_save_snapshots.pop(key, {})
        AuditLogService.log_update(instance, old_values)


@receiver(post_delete)
def audit_post_delete(sender, instance, **kwargs):
    """Create audit log entry after delete."""
    if not AuditLogService.is_audited(sender):
        return

    AuditLogService.log_delete(instance)


def register_audit_models():
    """Register all models that should be audited."""
    from apps.contracts.models import Contract, ContractItem
    from apps.customers.models import Customer
    from apps.products.models import Product
    from apps.todos.models import TodoItem

    # Register models with their entity type names
    AuditLogService.register_model(Contract, "contract")
    AuditLogService.register_model(
        ContractItem,
        "contract_item",
        parent_field="contract",
        parent_type="contract",
    )
    AuditLogService.register_model(Customer, "customer")
    AuditLogService.register_model(Product, "product")

    # Register TodoItem with multiple possible parents
    AuditLogService.register_model_multi_parent(
        TodoItem,
        "todo",
        parent_fields=[
            ("contract", "contract"),
            ("contract_item", "contract_item"),
            ("customer", "customer"),
        ],
    )


# Register models when this module is imported
register_audit_models()
