"""Management command to create test tenant and admin user."""
from django.core.management.base import BaseCommand

from apps.tenants.models import Role, Tenant, User


class Command(BaseCommand):
    help = "Create a test tenant with admin user for development"

    def add_arguments(self, parser):
        parser.add_argument(
            "--tenant-name",
            default="Test Company",
            help="Name of the test tenant",
        )
        parser.add_argument(
            "--admin-email",
            default="admin@test.local",
            help="Email for the admin user",
        )
        parser.add_argument(
            "--admin-password",
            default="admin123",
            help="Password for the admin user",
        )

    def handle(self, *args, **options):
        tenant_name = options["tenant_name"]
        admin_email = options["admin_email"]
        admin_password = options["admin_password"]

        # Create or get tenant
        tenant, created = Tenant.objects.get_or_create(
            name=tenant_name,
            defaults={
                "currency": "EUR",
                "is_active": True,
            },
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"Created tenant: {tenant.name}"))
        else:
            self.stdout.write(f"Tenant already exists: {tenant.name}")

        # Create admin role
        admin_role, created = Role.objects.get_or_create(
            tenant=tenant,
            name="Admin",
            defaults={
                "permissions": {
                    "customers": ["read", "write", "delete"],
                    "products": ["read", "write", "delete"],
                    "contracts": ["read", "write", "delete"],
                    "users": ["read", "write", "delete"],
                    "settings": ["read", "write"],
                },
                "is_default": False,
            },
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"Created role: {admin_role.name}"))

        # Create user role
        user_role, created = Role.objects.get_or_create(
            tenant=tenant,
            name="User",
            defaults={
                "permissions": {
                    "customers": ["read"],
                    "products": ["read"],
                    "contracts": ["read", "write"],
                },
                "is_default": True,
            },
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"Created role: {user_role.name}"))

        # Create or update admin user
        user, created = User.objects.get_or_create(
            email=admin_email,
            defaults={
                "tenant": tenant,
                "role": admin_role,
                "first_name": "Admin",
                "last_name": "User",
                "is_active": True,
                "is_staff": True,
            },
        )

        if created:
            user.set_password(admin_password)
            user.save()
            self.stdout.write(self.style.SUCCESS(f"Created admin user: {admin_email}"))
        else:
            self.stdout.write(f"Admin user already exists: {admin_email}")

        # Summary
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=" * 50))
        self.stdout.write(self.style.SUCCESS("Test data setup complete!"))
        self.stdout.write(self.style.SUCCESS("=" * 50))
        self.stdout.write(f"Tenant: {tenant.name}")
        self.stdout.write(f"Admin Email: {admin_email}")
        self.stdout.write(f"Admin Password: {admin_password}")
        self.stdout.write("")
        self.stdout.write("Login with:")
        self.stdout.write(f'  mutation {{ login(email: "{admin_email}", password: "{admin_password}") {{ ... on AuthPayload {{ accessToken }} }} }}')
