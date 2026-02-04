"""Signals for the tenants app."""
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.core.permissions import DEFAULT_ROLES


@receiver(post_save, sender="tenants.Tenant")
def create_default_roles(sender, instance, created, **kwargs):
    """Seed default roles for newly created tenants."""
    if not created:
        return

    from apps.tenants.models import Role

    for role_name, permissions in DEFAULT_ROLES.items():
        Role.objects.get_or_create(
            tenant=instance,
            name=role_name,
            defaults={
                "permissions": permissions,
                "is_system": True,
                "is_default": role_name == "Manager",
            },
        )
