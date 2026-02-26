"""Management command to seed default SKR04 accounts and mappings."""
from decimal import Decimal

from django.core.management.base import BaseCommand

from apps.accounting.models import (
    DebitorAccountScheme,
    RevenueAccount,
    RevenueAccountMapping,
    TaxAccount,
)
from apps.tenants.models import Tenant


# Standard SKR04 revenue accounts
DEFAULT_REVENUE_ACCOUNTS = [
    {
        "account_number": "4400",
        "name": "Erlöse aus Lieferungen und Leistungen 19% USt",
        "tax_rate": Decimal("19.00"),
        "vat_classification": "domestic",
        "sort_order": 10,
    },
    {
        "account_number": "4300",
        "name": "Erlöse 7% USt",
        "tax_rate": Decimal("7.00"),
        "vat_classification": "domestic",
        "sort_order": 20,
    },
    {
        "account_number": "4336",
        "name": "Erlöse aus im anderen EU-Land stpfl. sonstigen Leistungen",
        "tax_rate": Decimal("0.00"),
        "vat_classification": "eu",
        "sort_order": 30,
    },
    {
        "account_number": "4125",
        "name": "Steuerfreie innergemeinschaftliche Lieferungen §4 Nr.1b UStG",
        "tax_rate": Decimal("0.00"),
        "vat_classification": "eu",
        "sort_order": 31,
    },
    {
        "account_number": "4338",
        "name": "Erlöse aus im Drittland stpfl. sonstigen Leistungen",
        "tax_rate": Decimal("0.00"),
        "vat_classification": "non_eu",
        "sort_order": 40,
    },
]

# Standard SKR04 tax accounts
DEFAULT_TAX_ACCOUNTS = [
    {
        "account_number": "3806",
        "name": "Umsatzsteuer 19%",
        "tax_rate": Decimal("19.00"),
    },
    {
        "account_number": "3801",
        "name": "Umsatzsteuer 7%",
        "tax_rate": Decimal("7.00"),
    },
]

# Default revenue account mappings (tax-rate based)
DEFAULT_MAPPINGS = [
    # Domestic: by tax rate
    {"tax_rate": Decimal("19.00"), "vat_classification": "domestic", "account_number": "4400"},
    {"tax_rate": Decimal("7.00"), "vat_classification": "domestic", "account_number": "4300"},
    # EU: regardless of tax rate
    {"tax_rate": None, "vat_classification": "eu", "account_number": "4336"},
    # Non-EU: regardless of tax rate
    {"tax_rate": None, "vat_classification": "non_eu", "account_number": "4338"},
]


class Command(BaseCommand):
    help = "Seed default SKR04 revenue accounts, tax accounts, and mappings for a tenant."

    def add_arguments(self, parser):
        parser.add_argument(
            "--tenant-id",
            type=int,
            help="Tenant ID to seed accounts for. If not provided, seeds for all tenants.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Overwrite existing accounts (by account number).",
        )

    def handle(self, *args, **options):
        tenant_id = options.get("tenant_id")
        force = options.get("force", False)

        if tenant_id:
            tenants = Tenant.objects.filter(id=tenant_id)
            if not tenants.exists():
                self.stderr.write(f"Tenant {tenant_id} not found.")
                return
        else:
            tenants = Tenant.objects.filter(is_active=True)

        for tenant in tenants:
            self.stdout.write(f"\nSeeding SKR04 accounts for tenant: {tenant.name}")
            self._seed_revenue_accounts(tenant, force)
            self._seed_tax_accounts(tenant, force)
            self._seed_mappings(tenant, force)
            self._ensure_debitor_scheme(tenant)
            self.stdout.write(self.style.SUCCESS(f"  Done for {tenant.name}"))

    def _seed_revenue_accounts(self, tenant, force):
        for data in DEFAULT_REVENUE_ACCOUNTS:
            obj, created = RevenueAccount.objects.update_or_create(
                tenant=tenant,
                account_number=data["account_number"],
                defaults=data if force else {},
            ) if force else (
                RevenueAccount.objects.get_or_create(
                    tenant=tenant,
                    account_number=data["account_number"],
                    defaults=data,
                )
            )
            status = "created" if created else ("updated" if force else "exists")
            self.stdout.write(f"  Revenue {data['account_number']}: {status}")

    def _seed_tax_accounts(self, tenant, force):
        for data in DEFAULT_TAX_ACCOUNTS:
            obj, created = TaxAccount.objects.update_or_create(
                tenant=tenant,
                account_number=data["account_number"],
                defaults=data if force else {},
            ) if force else (
                TaxAccount.objects.get_or_create(
                    tenant=tenant,
                    account_number=data["account_number"],
                    defaults=data,
                )
            )
            status = "created" if created else ("updated" if force else "exists")
            self.stdout.write(f"  Tax {data['account_number']}: {status}")

    def _seed_mappings(self, tenant, force):
        account_map = {
            a.account_number: a
            for a in RevenueAccount.objects.filter(tenant=tenant)
        }

        for mapping_data in DEFAULT_MAPPINGS:
            account_number = mapping_data["account_number"]
            revenue_account = account_map.get(account_number)
            if not revenue_account:
                self.stderr.write(
                    f"  WARNING: Revenue account {account_number} not found, skipping mapping."
                )
                continue

            lookup = {
                "tenant": tenant,
                "product": None,
                "tax_rate": mapping_data["tax_rate"],
                "vat_classification": mapping_data["vat_classification"],
            }
            defaults = {"revenue_account": revenue_account}

            if force:
                obj, created = RevenueAccountMapping.objects.update_or_create(
                    **lookup, defaults=defaults,
                )
            else:
                obj, created = RevenueAccountMapping.objects.get_or_create(
                    **lookup, defaults=defaults,
                )

            label = f"{mapping_data['tax_rate'] or '—'}% / {mapping_data['vat_classification']}"
            status = "created" if created else ("updated" if force else "exists")
            self.stdout.write(f"  Mapping {label} → {account_number}: {status}")

    def _ensure_debitor_scheme(self, tenant):
        _, created = DebitorAccountScheme.objects.get_or_create(tenant=tenant)
        status = "created" if created else "exists"
        self.stdout.write(f"  Debitor scheme: {status}")
