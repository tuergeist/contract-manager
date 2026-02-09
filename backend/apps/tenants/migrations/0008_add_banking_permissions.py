"""Add banking permissions to existing Admin and Manager roles."""

from django.db import migrations


def add_banking_permissions(apps, schema_editor):
    Role = apps.get_model("tenants", "Role")

    for role in Role.objects.all():
        if not role.permissions:
            continue

        permissions = dict(role.permissions)

        # Admin and Manager roles should get banking permissions.
        # Admin has all permissions, Manager has most.
        # We detect these by checking for broad permission coverage.
        has_contracts_write = permissions.get("contracts.write")
        has_customers_read = permissions.get("customers.read")

        if has_contracts_write and has_customers_read:
            changed = False
            if not permissions.get("banking.read"):
                permissions["banking.read"] = True
                changed = True
            if not permissions.get("banking.write"):
                permissions["banking.write"] = True
                changed = True
            if changed:
                role.permissions = permissions
                role.save(update_fields=["permissions"])


def reverse_migration(apps, schema_editor):
    Role = apps.get_model("tenants", "Role")

    for role in Role.objects.all():
        if not role.permissions:
            continue

        permissions = dict(role.permissions)
        changed = False

        for perm in ["banking.read", "banking.write"]:
            if perm in permissions:
                del permissions[perm]
                changed = True

        if changed:
            role.permissions = permissions
            role.save(update_fields=["permissions"])


class Migration(migrations.Migration):

    dependencies = [
        ("tenants", "0007_migrate_invoice_permissions"),
    ]

    operations = [
        migrations.RunPython(add_banking_permissions, reverse_migration),
    ]
