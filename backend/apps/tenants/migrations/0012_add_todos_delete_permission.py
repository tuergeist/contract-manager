"""Add todos.delete permission to roles that have todos.write."""
from django.db import migrations


def add_todos_delete(apps, schema_editor):
    """Grant todos.delete to roles that already have todos.write."""
    Role = apps.get_model("tenants", "Role")

    for role in Role.objects.all():
        if not role.permissions:
            continue

        permissions = dict(role.permissions)

        if permissions.get("todos.write"):
            if not permissions.get("todos.delete"):
                permissions["todos.delete"] = True
                role.permissions = permissions
                role.save(update_fields=["permissions"])


def reverse_migration(apps, schema_editor):
    """Remove todos.delete permission."""
    Role = apps.get_model("tenants", "Role")

    for role in Role.objects.all():
        if not role.permissions:
            continue

        permissions = dict(role.permissions)
        if "todos.delete" in permissions:
            del permissions["todos.delete"]
            role.permissions = permissions
            role.save(update_fields=["permissions"])


class Migration(migrations.Migration):
    dependencies = [
        ("tenants", "0011_add_user_notification_preferences"),
    ]

    operations = [
        migrations.RunPython(add_todos_delete, reverse_migration),
    ]
