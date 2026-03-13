"""Add cost_centers permissions to existing system roles."""
from django.db import migrations


def add_cost_center_permissions(apps, schema_editor):
    """Sync cost_centers permissions to system roles based on DEFAULT_ROLES."""
    from apps.core.permissions import DEFAULT_ROLES

    Role = apps.get_model("tenants", "Role")

    for role in Role.objects.filter(is_system=True):
        if role.name not in DEFAULT_ROLES:
            continue

        default_perms = DEFAULT_ROLES[role.name]
        permissions = dict(role.permissions or {})
        changed = False

        for perm_key, perm_val in default_perms.items():
            if perm_key.startswith("cost_centers.") and permissions.get(perm_key) != perm_val:
                permissions[perm_key] = perm_val
                changed = True

        if changed:
            role.permissions = permissions
            role.save(update_fields=["permissions"])


def reverse_migration(apps, schema_editor):
    """Remove cost_centers permissions."""
    Role = apps.get_model("tenants", "Role")

    for role in Role.objects.all():
        if not role.permissions:
            continue

        permissions = dict(role.permissions)
        keys_to_remove = [k for k in permissions if k.startswith("cost_centers.")]
        if keys_to_remove:
            for k in keys_to_remove:
                del permissions[k]
            role.permissions = permissions
            role.save(update_fields=["permissions"])


class Migration(migrations.Migration):
    dependencies = [
        ("tenants", "0015_signupverification"),
    ]

    operations = [
        migrations.RunPython(add_cost_center_permissions, reverse_migration),
    ]
