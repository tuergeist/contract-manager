"""Data migration: grant the new `offers.finalize` permission to all
existing Admin roles across all tenants.

The Admin role is "all permissions" by convention. The new permission
key needs to be added to existing role rows so admins keep that
convention without requiring a manual settings update.

Non-Admin roles are left untouched — `offers.finalize` is a deliberate
gate that admins distribute on a per-role basis.
"""

from django.db import migrations


def grant_offers_finalize_to_admin(apps, schema_editor):
    Role = apps.get_model("tenants", "Role")
    for role in Role.objects.filter(name="Admin"):
        perms = role.permissions or {}
        if not perms.get("offers.finalize"):
            perms["offers.finalize"] = True
            role.permissions = perms
            role.save(update_fields=["permissions"])


def revoke_offers_finalize(apps, schema_editor):
    Role = apps.get_model("tenants", "Role")
    for role in Role.objects.filter(name="Admin"):
        perms = role.permissions or {}
        if "offers.finalize" in perms:
            perms.pop("offers.finalize", None)
            role.permissions = perms
            role.save(update_fields=["permissions"])


class Migration(migrations.Migration):

    dependencies = [
        # Depend on the last tracked migration (0018). The local-only
        # 0019_tenant_slack_config / 0020_remove_tenant_slack_config
        # migrations are untracked in git and would break CI if depended on
        # — same trap as fixed in 2.32.1 for invoices.0028.
        ("tenants", "0018_reportschedule"),
    ]

    operations = [
        migrations.RunPython(
            grant_offers_finalize_to_admin,
            reverse_code=revoke_offers_finalize,
        ),
    ]
