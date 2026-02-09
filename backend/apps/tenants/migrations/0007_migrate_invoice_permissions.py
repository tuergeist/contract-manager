"""Migrate invoices.write permission to granular invoice permissions."""

from django.db import migrations


def migrate_invoice_permissions(apps, schema_editor):
    """Convert invoices.write to invoices.export + invoices.generate for existing roles.

    Also grant invoices.settings to roles that have settings.write since
    invoice settings mutations now check invoices.settings instead of settings.write.
    """
    Role = apps.get_model("tenants", "Role")

    for role in Role.objects.all():
        if not role.permissions:
            continue

        permissions = dict(role.permissions)
        changed = False

        # If role had invoices.write, give them export and generate
        if permissions.get("invoices.write"):
            permissions["invoices.export"] = True
            permissions["invoices.generate"] = True
            del permissions["invoices.write"]
            changed = True

        # Remove any stale invoices.write that was False
        if "invoices.write" in permissions:
            del permissions["invoices.write"]
            changed = True

        # If role has settings.write, also grant invoices.settings
        # since invoice settings now require invoices.settings instead of settings.write
        if permissions.get("settings.write") and not permissions.get("invoices.settings"):
            permissions["invoices.settings"] = True
            changed = True

        if changed:
            role.permissions = permissions
            role.save(update_fields=["permissions"])


def reverse_migration(apps, schema_editor):
    """Convert granular permissions back to invoices.write."""
    Role = apps.get_model("tenants", "Role")

    for role in Role.objects.all():
        if not role.permissions:
            continue

        permissions = dict(role.permissions)
        changed = False

        # If role has export or generate, give them write
        if permissions.get("invoices.export") or permissions.get("invoices.generate"):
            permissions["invoices.write"] = True
            changed = True

        # Remove granular permissions
        for perm in ["invoices.export", "invoices.generate", "invoices.settings"]:
            if perm in permissions:
                del permissions[perm]
                changed = True

        if changed:
            role.permissions = permissions
            role.save(update_fields=["permissions"])


class Migration(migrations.Migration):

    dependencies = [
        ("tenants", "0006_add_role_ids_to_invitation"),
    ]

    operations = [
        migrations.RunPython(migrate_invoice_permissions, reverse_migration),
    ]
