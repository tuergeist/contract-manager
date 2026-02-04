"""Seed default roles and migrate users from is_admin to role-based system."""

from django.db import migrations


def seed_default_roles(apps, schema_editor):
    from apps.core.permissions import DEFAULT_ROLES

    Tenant = apps.get_model("tenants", "Tenant")
    Role = apps.get_model("tenants", "Role")
    User = apps.get_model("tenants", "User")

    for tenant in Tenant.objects.all():
        roles_by_name = {}
        for role_name, permissions in DEFAULT_ROLES.items():
            role, created = Role.objects.get_or_create(
                tenant=tenant,
                name=role_name,
                defaults={
                    "permissions": permissions,
                    "is_system": True,
                    "is_default": role_name == "Manager",
                },
            )
            if not created:
                # Update existing role to be system role
                role.is_system = True
                role.permissions = permissions
                role.save()
            roles_by_name[role_name] = role

        # Assign roles to users
        for user in User.objects.filter(tenant=tenant):
            if user.is_admin:
                user.roles.add(roles_by_name["Admin"])
            else:
                user.roles.add(roles_by_name["Manager"])


def reverse_migration(apps, schema_editor):
    # No-op: we don't remove role assignments on reverse
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("tenants", "0004_add_rbac"),
    ]

    operations = [
        migrations.RunPython(seed_default_roles, reverse_migration),
    ]
