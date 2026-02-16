"""Add contracts.export permission to roles that have contracts.read and contracts.write."""
from django.db import migrations


def add_contracts_export(apps, schema_editor):
    """Grant contracts.export to roles that already have contracts.read + contracts.write."""
    Role = apps.get_model("tenants", "Role")

    for role in Role.objects.all():
        if not role.permissions:
            continue

        permissions = dict(role.permissions)

        if permissions.get("contracts.read") and permissions.get("contracts.write"):
            if not permissions.get("contracts.export"):
                permissions["contracts.export"] = True
                role.permissions = permissions
                role.save(update_fields=["permissions"])


def reverse_migration(apps, schema_editor):
    """Remove contracts.export permission."""
    Role = apps.get_model("tenants", "Role")

    for role in Role.objects.all():
        if not role.permissions:
            continue

        permissions = dict(role.permissions)
        if "contracts.export" in permissions:
            del permissions["contracts.export"]
            role.permissions = permissions
            role.save(update_fields=["permissions"])


class Migration(migrations.Migration):
    dependencies = [
        ("tenants", "0009_add_invoices_delete_write_permission"),
    ]

    operations = [
        migrations.RunPython(add_contracts_export, reverse_migration),
    ]
