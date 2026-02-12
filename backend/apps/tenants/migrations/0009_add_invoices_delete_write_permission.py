"""Add invoices.delete and invoices.write permissions to roles with invoice management capabilities."""
from django.db import migrations


def add_invoices_permissions(apps, schema_editor):
    """Add invoices.delete and invoices.write to roles that have invoices.export or invoices.generate."""
    Role = apps.get_model("tenants", "Role")

    for role in Role.objects.all():
        if not role.permissions:
            continue

        permissions = dict(role.permissions)
        changed = False

        # If role has export or generate, they should also be able to delete and write
        if permissions.get("invoices.export") or permissions.get("invoices.generate"):
            if not permissions.get("invoices.delete"):
                permissions["invoices.delete"] = True
                changed = True
            if not permissions.get("invoices.write"):
                permissions["invoices.write"] = True
                changed = True

        if changed:
            role.permissions = permissions
            role.save(update_fields=["permissions"])


def reverse_migration(apps, schema_editor):
    """Remove invoices.delete and invoices.write permissions."""
    Role = apps.get_model("tenants", "Role")

    for role in Role.objects.all():
        if not role.permissions:
            continue

        permissions = dict(role.permissions)
        changed = False

        if "invoices.delete" in permissions:
            del permissions["invoices.delete"]
            changed = True
        if "invoices.write" in permissions:
            del permissions["invoices.write"]
            changed = True

        if changed:
            role.permissions = permissions
            role.save(update_fields=["permissions"])


class Migration(migrations.Migration):
    dependencies = [
        ("tenants", "0008_add_banking_permissions"),
    ]

    operations = [
        migrations.RunPython(add_invoices_permissions, reverse_migration),
    ]
