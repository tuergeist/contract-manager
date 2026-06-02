"""Grant the new dunning permissions to existing default roles.

Admin roles receive ``reminders.send`` and ``reminders.settings``.
Manager roles receive ``reminders.send`` only. Viewer and custom roles
are left untouched.
"""
from django.db import migrations

ROLE_GRANTS = {
    "Admin": ["reminders.send", "reminders.settings"],
    "Manager": ["reminders.send"],
}


def grant_permissions(apps, schema_editor):
    Role = apps.get_model("tenants", "Role")
    for role in Role.objects.filter(name__in=ROLE_GRANTS.keys()):
        perms = dict(role.permissions or {})
        changed = False
        for perm in ROLE_GRANTS[role.name]:
            if not perms.get(perm):
                perms[perm] = True
                changed = True
        if changed:
            role.permissions = perms
            role.save(update_fields=["permissions"])


def revoke_permissions(apps, schema_editor):
    Role = apps.get_model("tenants", "Role")
    for role in Role.objects.filter(name__in=ROLE_GRANTS.keys()):
        perms = dict(role.permissions or {})
        changed = False
        for perm in ROLE_GRANTS[role.name]:
            if perm in perms:
                del perms[perm]
                changed = True
        if changed:
            role.permissions = perms
            role.save(update_fields=["permissions"])


class Migration(migrations.Migration):

    dependencies = [
        ("invoices", "0026_backfill_invoice_due_date"),
        ("tenants", "0018_reportschedule"),
    ]

    operations = [
        migrations.RunPython(grant_permissions, revoke_permissions),
    ]
