"""Management command to create test tenant and admin user."""
from datetime import date, timedelta
from decimal import Decimal

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
                "is_admin": True,
            },
        )

        if created:
            user.set_password(admin_password)
            user.save()
            self.stdout.write(self.style.SUCCESS(f"Created admin user: {admin_email}"))
        else:
            # Ensure existing user has is_admin set
            if not user.is_admin:
                user.is_admin = True
                user.save()
                self.stdout.write(f"Updated admin user with is_admin=True: {admin_email}")
            else:
                self.stdout.write(f"Admin user already exists: {admin_email}")

        # Optional: dunning fixture (overdue invoice for the E2E reminders flow)
        self._setup_dunning_fixture(tenant)

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

    # ----------------------------------------------------------------
    # Dunning fixture (for E2E payment-reminders.spec.ts)
    # ----------------------------------------------------------------

    E2E_CUSTOMER_NAME = "E2E Overdue Customer"
    E2E_CONTRACT_NAME = "E2E Overdue Contract"
    E2E_INVOICE_NUMBER = "E2E-OVERDUE-0001"

    def _setup_dunning_fixture(self, tenant):
        """Create a fixed, mahnfähige InvoiceRecord for the dunning E2E flow.

        Idempotent: existing rows are reused. Re-running the command refreshes
        the invoice's due_date so it stays overdue regardless of wall clock.
        """
        try:
            from apps.contracts.models import Contract
            from apps.customers.models import Customer
            from apps.invoices.models import InvoiceRecord
        except Exception as exc:  # pragma: no cover - apps always available in dev
            self.stdout.write(
                self.style.WARNING(f"Skipping dunning fixture: {exc}")
            )
            return

        customer, _ = Customer.objects.get_or_create(
            tenant=tenant,
            name=self.E2E_CUSTOMER_NAME,
            defaults={
                "billing_emails": ["billing@e2e.test"],
                "is_active": True,
                "invoice_language": "de",
            },
        )
        # Always keep a billing email set so the send mutation does not bail out.
        if not customer.billing_emails:
            customer.billing_emails = ["billing@e2e.test"]
            customer.save(update_fields=["billing_emails"])

        contract_start = date.today() - timedelta(days=120)
        contract, _ = Contract.objects.get_or_create(
            tenant=tenant,
            customer=customer,
            name=self.E2E_CONTRACT_NAME,
            defaults={
                "status": Contract.Status.ACTIVE,
                "start_date": contract_start,
                "billing_start_date": contract_start,
                "billing_interval": Contract.BillingInterval.MONTHLY,
                "billing_anchor_day": 1,
            },
        )

        # Overdue invoice: invoiced ~45 days ago, due 30 days ago.
        invoice_date = date.today() - timedelta(days=45)
        due_date = date.today() - timedelta(days=30)
        period_start = date.today().replace(day=1) - timedelta(days=60)
        period_end = period_start + timedelta(days=29)

        invoice, created = InvoiceRecord.objects.get_or_create(
            tenant=tenant,
            invoice_number=self.E2E_INVOICE_NUMBER,
            defaults={
                "contract": contract,
                "customer": customer,
                "billing_date": invoice_date,
                "invoice_date": invoice_date,
                "due_date": due_date,
                "period_start": period_start,
                "period_end": period_end,
                "total_net": Decimal("100.00"),
                "tax_rate": Decimal("19.00"),
                "tax_amount": Decimal("19.00"),
                "total_gross": Decimal("119.00"),
                "line_items_snapshot": [
                    {
                        "product_name": "E2E Test Item",
                        "description": "Fixture line for dunning E2E",
                        "quantity": 1,
                        "unit_price": "100.00",
                        "amount": "100.00",
                    }
                ],
                "company_data_snapshot": {"company_name": tenant.name},
                "status": InvoiceRecord.Status.FINALIZED,
                "customer_name": customer.name,
                "contract_name": contract.name,
                "invoice_text": "",
            },
        )

        # Keep the invoice perpetually overdue across re-runs and ensure it has
        # not silently transitioned to DUNNING/PAID from a previous E2E run.
        invoice.due_date = due_date
        invoice.invoice_date = invoice_date
        invoice.status = InvoiceRecord.Status.FINALIZED
        invoice.save(update_fields=["due_date", "invoice_date", "status"])

        # Remove any reminders left over from prior E2E runs so the test starts
        # from a clean slate (no prior reminders for this invoice).
        invoice.payment_reminders.all().delete()

        if created:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Created overdue invoice fixture: {invoice.invoice_number}"
                )
            )
        else:
            self.stdout.write(
                f"Refreshed overdue invoice fixture: {invoice.invoice_number}"
            )
