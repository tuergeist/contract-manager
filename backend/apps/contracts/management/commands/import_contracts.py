"""Management command to import contracts from NetSuite Excel exports."""

from django.core.management.base import BaseCommand, CommandError

from apps.contracts.services import ExcelParser, ImportService, MatchStatus
from apps.tenants.models import Tenant


class Command(BaseCommand):
    help = "Import contracts from a NetSuite Excel export file"

    def add_arguments(self, parser):
        parser.add_argument(
            "file",
            type=str,
            help="Path to the Excel file to import",
        )
        parser.add_argument(
            "--tenant",
            type=str,
            required=True,
            help="Tenant name to import contracts into",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Parse and show proposals without creating contracts",
        )
        parser.add_argument(
            "--auto-approve",
            action="store_true",
            help="Automatically approve all high-confidence matches (>= 0.9)",
        )
        parser.add_argument(
            "--approve-all",
            action="store_true",
            help="Approve all proposals (including low-confidence matches)",
        )
        parser.add_argument(
            "--threshold",
            type=float,
            default=0.9,
            help="Confidence threshold for auto-approval (default: 0.9)",
        )
        parser.add_argument(
            "--auto-create-products",
            action="store_true",
            default=True,
            help="Automatically create missing products (default: True)",
        )
        parser.add_argument(
            "--interactive",
            "-i",
            action="store_true",
            help="Interactive mode: prompt for each proposal that needs review",
        )

    def handle(self, *args, **options):
        file_path = options["file"]
        tenant_name = options["tenant"]
        dry_run = options["dry_run"]
        auto_approve = options["auto_approve"]
        approve_all = options["approve_all"]
        threshold = options["threshold"]
        auto_create_products = options["auto_create_products"]
        interactive = options["interactive"]

        # Get tenant
        try:
            tenant = Tenant.objects.get(name=tenant_name)
        except Tenant.DoesNotExist as err:
            raise CommandError(f"Tenant '{tenant_name}' not found") from err

        self.stdout.write(f"Importing contracts for tenant: {tenant.name}")
        self.stdout.write(f"File: {file_path}")
        self.stdout.write("")

        # Parse Excel file
        parser = ExcelParser()
        rows = parser.parse(file_path)

        if parser.errors:
            self.stdout.write(self.style.ERROR("Parsing errors:"))
            for error in parser.errors:
                self.stdout.write(f"  - {error}")
            if not rows:
                raise CommandError("Failed to parse Excel file")
            self.stdout.write("")

        self.stdout.write(f"Parsed {len(rows)} rows from Excel")
        self.stdout.write("")

        # Generate proposals
        service = ImportService(tenant)
        service.AUTO_APPROVE_THRESHOLD = threshold
        proposals = service.generate_proposals(rows)

        # Show summary
        summary = service.get_summary()
        self.stdout.write(self.style.SUCCESS("Import Summary:"))
        self.stdout.write(f"  Total proposals: {summary['total_proposals']}")
        self.stdout.write(f"  Auto-matched (>= {threshold}): {summary['auto_matched']}")
        self.stdout.write(f"  Needs review: {summary['needs_review']}")
        self.stdout.write(f"  Not found: {summary['not_found']}")
        self.stdout.write(f"  Total line items: {summary['total_items']}")
        self.stdout.write("")

        # Process proposals
        if interactive:
            self._process_interactive(proposals)
        elif approve_all:
            for p in proposals:
                if p.match_result and p.match_result.status != MatchStatus.NOT_FOUND:
                    p.approved = True
                    if not p.selected_customer and p.match_result.customer:
                        p.selected_customer = p.match_result.customer
        elif auto_approve:
            for p in proposals:
                if p.match_result and p.match_result.status == MatchStatus.MATCHED:
                    p.approved = True

        # Show proposals
        self._show_proposals(proposals)

        if dry_run:
            self.stdout.write(self.style.WARNING("\n[DRY RUN] No contracts created."))
            return

        # Apply proposals
        approved_count = sum(1 for p in proposals if p.approved)
        if approved_count == 0:
            self.stdout.write(
                self.style.WARNING("\nNo proposals approved. Use --auto-approve or --interactive.")
            )
            return

        self.stdout.write(f"\nCreating {approved_count} contracts...")
        created = service.apply_proposals(
            proposals,
            auto_create_products=auto_create_products,
        )

        self.stdout.write(self.style.SUCCESS(f"\nCreated {len(created)} contracts:"))
        for contract in created:
            self.stdout.write(f"  - {contract.name} ({contract.customer.name})")

        # Show errors
        errors = [p for p in proposals if p.error]
        if errors:
            self.stdout.write(self.style.ERROR("\nErrors:"))
            for p in errors:
                self.stdout.write(f"  - {p.sales_order_number}: {p.error}")

    def _show_proposals(self, proposals):
        """Display proposals in a formatted table."""
        self.stdout.write(self.style.SUCCESS("\nProposals:"))
        self.stdout.write("-" * 100)

        for p in proposals:
            status_str = "✓ MATCHED" if p.match_result.status == MatchStatus.MATCHED else \
                        "? REVIEW" if p.match_result.status == MatchStatus.REVIEW else \
                        "✗ NOT FOUND"

            confidence = f"{p.match_result.confidence:.0%}" if p.match_result.confidence else "N/A"

            approved_str = "APPROVED" if p.approved else "REJECTED" if p.rejected else "PENDING"

            self.stdout.write(
                f"{p.sales_order_number:15} | "
                f"{p.customer_name[:30]:30} | "
                f"{status_str:12} | "
                f"{confidence:5} | "
                f"{approved_str:8} | "
                f"Items: {len(p.items)}"
            )

            if p.match_result.customer:
                self.stdout.write(f"                 -> Matched to: {p.match_result.customer.name}")

            if p.match_result.alternatives:
                self.stdout.write("                 -> Alternatives:")
                for alt in p.match_result.alternatives[:3]:
                    self.stdout.write(
                        f"                      {alt.customer.name} ({alt.confidence:.0%})"
                    )

            if p.discount_amount:
                self.stdout.write(f"                 -> Discount: €{p.discount_amount}")

        self.stdout.write("-" * 100)

    def _process_interactive(self, proposals):
        """Process proposals interactively."""
        for proposal in proposals:
            if proposal.match_result.status == MatchStatus.MATCHED:
                # Auto-approve high-confidence matches
                proposal.approved = True
                continue

            if proposal.match_result.status == MatchStatus.NOT_FOUND:
                # Skip proposals with no matches
                self.stdout.write(
                    self.style.WARNING(
                        f"\nNo matches found for: {proposal.customer_name} ({proposal.sales_order_number})"
                    )
                )
                continue

            # Show proposal details
            self.stdout.write(f"\n{'='*60}")
            self.stdout.write(f"Customer: {proposal.customer_name}")
            self.stdout.write(f"NetSuite #: {proposal.customer_number}")
            self.stdout.write(f"Order: {proposal.sales_order_number}")
            self.stdout.write(f"Items: {len(proposal.items)}")
            self.stdout.write(f"Monthly Rate: €{proposal.total_monthly_rate:.2f}")

            # Show match options
            self.stdout.write("\nMatch options:")
            options = []
            if proposal.match_result.customer:
                options.append(proposal.match_result)
            options.extend(proposal.match_result.alternatives)

            for i, opt in enumerate(options, 1):
                self.stdout.write(
                    f"  {i}. {opt.customer.name} ({opt.confidence:.0%})"
                )

            self.stdout.write("  s. Skip this proposal")
            self.stdout.write("  q. Quit interactive mode")

            # Get user input
            while True:
                choice = input("\nSelect option: ").strip().lower()

                if choice == "q":
                    self.stdout.write("Exiting interactive mode...")
                    return

                if choice == "s":
                    proposal.rejected = True
                    break

                try:
                    idx = int(choice) - 1
                    if 0 <= idx < len(options):
                        proposal.approved = True
                        proposal.selected_customer = options[idx].customer
                        self.stdout.write(
                            self.style.SUCCESS(f"Selected: {options[idx].customer.name}")
                        )
                        break
                except ValueError:
                    pass

                self.stdout.write("Invalid option, try again.")
