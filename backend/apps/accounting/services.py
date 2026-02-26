"""Accounting services for booking generation and revenue account resolution."""
from datetime import date
from decimal import Decimal
from typing import Optional

from django.db import transaction
from django.db.models import Q, Sum

from apps.accounting.models import (
    BookingEntry,
    DebitorAccount,
    DebitorAccountScheme,
    RevenueAccount,
    RevenueAccountMapping,
)
from apps.invoices.models import InvoiceRecord
from apps.invoices.services import _classify_customer, _get_country_iso
from apps.products.models import Product
from apps.tenants.models import Tenant


# DATEV tax keys (BU-Schlüssel)
DATEV_TAX_KEYS = {
    Decimal("19.00"): "9",   # USt 19% (Automatikkonto)
    Decimal("7.00"): "8",    # USt 7% (Automatikkonto)
    Decimal("0.00"): "",     # Tax-free
}


class BookingService:
    """Generates booking entries from finalized invoices."""

    def resolve_revenue_account(
        self,
        tenant: Tenant,
        product: Optional[Product],
        effective_tax_rate: Decimal,
        vat_classification: str,
    ) -> Optional[RevenueAccount]:
        """Resolve the revenue account using the priority chain.

        Priority (highest first):
        1. Product-specific + VAT classification
        2. Product-specific + any
        3. Tax rate + VAT classification
        4. Tax rate + any
        5. Global fallback (no product, no tax rate) + VAT classification
        6. Global fallback + any
        """
        mappings = RevenueAccountMapping.objects.filter(
            tenant=tenant,
        ).select_related("revenue_account")

        # 1. Product-specific + VAT classification
        if product:
            m = mappings.filter(product=product, vat_classification=vat_classification).first()
            if m:
                return m.revenue_account

            # 2. Product-specific + any
            m = mappings.filter(product=product, vat_classification="any").first()
            if m:
                return m.revenue_account

        # 3. Tax rate + VAT classification
        m = mappings.filter(
            product__isnull=True,
            tax_rate=effective_tax_rate,
            vat_classification=vat_classification,
        ).first()
        if m:
            return m.revenue_account

        # 4. Tax rate + any
        m = mappings.filter(
            product__isnull=True,
            tax_rate=effective_tax_rate,
            vat_classification="any",
        ).first()
        if m:
            return m.revenue_account

        # 5. Global fallback + VAT classification
        m = mappings.filter(
            product__isnull=True,
            tax_rate__isnull=True,
            vat_classification=vat_classification,
        ).first()
        if m:
            return m.revenue_account

        # 6. Global fallback + any
        m = mappings.filter(
            product__isnull=True,
            tax_rate__isnull=True,
            vat_classification="any",
        ).first()
        if m:
            return m.revenue_account

        return None

    def _get_datev_tax_key(self, tax_rate: Decimal, vat_classification: str) -> str:
        """Get the DATEV BU-Schlüssel for a tax rate and classification."""
        if vat_classification != "domestic":
            return ""
        return DATEV_TAX_KEYS.get(tax_rate, "")

    def _get_debitor_number(self, tenant: Tenant, customer_id: int) -> Optional[str]:
        """Get the debitor account number for a customer."""
        try:
            debitor = DebitorAccount.objects.get(
                tenant=tenant, customer_id=customer_id,
            )
            return debitor.account_number or None
        except DebitorAccount.DoesNotExist:
            return None

    @transaction.atomic
    def generate_bookings(self, invoice_record: InvoiceRecord) -> list[BookingEntry]:
        """Generate booking entries for a single invoice.

        Creates one BookingEntry per line item:
        - Debit: debitor account (customer)
        - Credit: revenue account (resolved via mapping)

        Returns empty list with error info if debitor account is missing.
        """
        tenant = invoice_record.tenant

        # Get debitor account number
        debitor_number = self._get_debitor_number(tenant, invoice_record.customer_id)
        if not debitor_number:
            return []

        # Get company legal data for default tax rate and classification
        from apps.invoices.models import CompanyLegalData
        try:
            legal_data = CompanyLegalData.objects.get(tenant=tenant)
        except CompanyLegalData.DoesNotExist:
            return []

        default_tax_rate = legal_data.default_tax_rate
        company_country = legal_data.country

        # Get customer address for VAT classification
        customer_address = {}
        if invoice_record.customer:
            customer_address = invoice_record.customer.address or {}

        vat_classification = _classify_customer(company_country, customer_address)

        # Determine booking date
        booking_date = invoice_record.invoice_date or invoice_record.billing_date

        # Delete existing bookings for this invoice (regeneration)
        BookingEntry.objects.filter(
            tenant=tenant, invoice_record=invoice_record,
        ).delete()

        entries = []
        is_storno = invoice_record.document_type == InvoiceRecord.DocumentType.STORNO

        # Process line items from snapshot
        line_items = invoice_record.line_items_snapshot or []
        for item in line_items:
            product_name = item.get("product_name", item.get("description", ""))
            amount = Decimal(str(item.get("amount", 0)))
            product_id = item.get("product_id") or item.get("item_id")

            if is_storno:
                amount = -abs(amount)

            # Resolve product for tax rate and mapping
            product = None
            if product_id:
                product = Product.objects.filter(
                    tenant=tenant, id=product_id,
                ).first()

            # Effective tax rate
            if product:
                effective_tax_rate = product.get_effective_tax_rate(default_tax_rate)
            else:
                effective_tax_rate = default_tax_rate

            # For EU/non-EU: actual tax is 0%, but we use the effective rate for mapping
            actual_tax_rate = effective_tax_rate if vat_classification == "domestic" else Decimal("0.00")
            tax_key = self._get_datev_tax_key(effective_tax_rate, vat_classification)

            # Resolve revenue account
            revenue_account = self.resolve_revenue_account(
                tenant, product, effective_tax_rate, vat_classification,
            )

            credit_account = revenue_account.account_number if revenue_account else "????"

            description = f"{invoice_record.invoice_number} / {invoice_record.customer_name}"
            if product_name:
                description = f"{invoice_record.invoice_number} / {product_name}"

            # Truncate description to max length
            if len(description) > 255:
                description = description[:252] + "..."

            entry = BookingEntry(
                tenant=tenant,
                invoice_record=invoice_record,
                booking_date=booking_date,
                debit_account=debitor_number,
                credit_account=credit_account,
                amount=amount,
                tax_rate=actual_tax_rate,
                tax_key=tax_key,
                description=description,
                line_item_snapshot=item,
            )
            entries.append(entry)

        # Bulk create
        if entries:
            BookingEntry.objects.bulk_create(entries)

        return entries

    def generate_bookings_for_period(
        self,
        tenant: Tenant,
        start: date,
        end: date,
        regenerate: bool = False,
    ) -> dict:
        """Generate bookings for all finalized invoices in a period.

        Returns dict with counts: created, skipped, errors.
        """
        invoices = InvoiceRecord.objects.filter(
            tenant=tenant,
            billing_date__gte=start,
            billing_date__lte=end,
            status__in=[
                InvoiceRecord.Status.FINALIZED,
                InvoiceRecord.Status.SENT,
                InvoiceRecord.Status.PAID,
            ],
        )

        created = 0
        skipped = 0
        errors = []

        for invoice in invoices:
            # Skip if already has bookings and not regenerating
            if not regenerate and invoice.booking_entries.exists():
                skipped += 1
                continue

            entries = self.generate_bookings(invoice)
            if entries:
                created += len(entries)
            else:
                errors.append(
                    f"Invoice {invoice.invoice_number}: no bookings generated "
                    f"(missing debitor or mapping)"
                )

        return {"created": created, "skipped": skipped, "errors": errors}

    def validate_period(self, tenant: Tenant, start: date, end: date) -> dict:
        """Validate accounting readiness for a period.

        Returns validation results with counts and details.
        """
        invoices = InvoiceRecord.objects.filter(
            tenant=tenant,
            billing_date__gte=start,
            billing_date__lte=end,
            status__in=[
                InvoiceRecord.Status.FINALIZED,
                InvoiceRecord.Status.SENT,
                InvoiceRecord.Status.PAID,
            ],
        )

        total_invoices = invoices.count()
        with_bookings = invoices.filter(booking_entries__isnull=False).distinct().count()
        without_bookings = total_invoices - with_bookings

        # Customers without debitor account in this period
        customer_ids = invoices.values_list("customer_id", flat=True).distinct()
        customers_with_debitor = DebitorAccount.objects.filter(
            tenant=tenant,
            customer_id__in=customer_ids,
        ).exclude(account_number="").values_list("customer_id", flat=True)

        customers_without_debitor_ids = set(customer_ids) - set(customers_with_debitor)

        # Unmapped line items check
        unmapped_items = []
        from apps.invoices.models import CompanyLegalData
        try:
            legal_data = CompanyLegalData.objects.get(tenant=tenant)
            default_tax_rate = legal_data.default_tax_rate
            company_country = legal_data.country
        except CompanyLegalData.DoesNotExist:
            default_tax_rate = Decimal("19.00")
            company_country = "DE"

        for invoice in invoices[:50]:  # Limit check to 50 invoices
            customer_address = {}
            if invoice.customer:
                customer_address = invoice.customer.address or {}
            vat_classification = _classify_customer(company_country, customer_address)

            for item in (invoice.line_items_snapshot or []):
                product_id = item.get("product_id") or item.get("item_id")
                product = None
                if product_id:
                    product = Product.objects.filter(tenant=tenant, id=product_id).first()

                effective_tax_rate = default_tax_rate
                if product:
                    effective_tax_rate = product.get_effective_tax_rate(default_tax_rate)

                revenue_account = self.resolve_revenue_account(
                    tenant, product, effective_tax_rate, vat_classification,
                )
                if not revenue_account:
                    unmapped_items.append({
                        "invoice_number": invoice.invoice_number,
                        "product_name": item.get("product_name", item.get("description", "?")),
                        "amount": str(item.get("amount", 0)),
                        "reason": f"No mapping for tax_rate={effective_tax_rate}, vat={vat_classification}",
                    })

        return {
            "total_invoices": total_invoices,
            "invoices_with_bookings": with_bookings,
            "invoices_without_bookings": without_bookings,
            "customers_without_debitor": list(customers_without_debitor_ids),
            "unmapped_line_items": unmapped_items,
        }


class DebitorService:
    """Manages debtor account number assignment."""

    @transaction.atomic
    def assign_number(
        self,
        tenant: Tenant,
        customer_id: int,
        account_number: Optional[str] = None,
    ) -> DebitorAccount:
        """Assign a debitor account number to a customer.

        If account_number is None, auto-assigns the next available number.
        """
        debitor, _ = DebitorAccount.objects.get_or_create(
            tenant=tenant,
            customer_id=customer_id,
        )

        if account_number is None:
            account_number = self._next_number(tenant)

        debitor.account_number = account_number
        debitor.save(update_fields=["account_number", "updated_at"])
        return debitor

    @transaction.atomic
    def bulk_assign(
        self,
        tenant: Tenant,
        customer_ids: Optional[list[int]] = None,
    ) -> dict:
        """Auto-assign debitor numbers to customers without one.

        If customer_ids is None, assigns to all customers without a number.
        Returns dict with assigned count, skipped, errors.
        """
        from apps.customers.models import Customer

        if customer_ids:
            customers = Customer.objects.filter(tenant=tenant, id__in=customer_ids)
        else:
            # All customers that don't have a debitor account with a number
            existing_with_number = DebitorAccount.objects.filter(
                tenant=tenant,
            ).exclude(account_number="").values_list("customer_id", flat=True)

            customers = Customer.objects.filter(
                tenant=tenant,
            ).exclude(id__in=existing_with_number)

        assigned = 0
        skipped = 0
        errors = []

        for customer in customers:
            try:
                debitor, _ = DebitorAccount.objects.get_or_create(
                    tenant=tenant, customer=customer,
                )
                if debitor.account_number:
                    skipped += 1
                    continue

                debitor.account_number = self._next_number(tenant)
                debitor.save(update_fields=["account_number", "updated_at"])
                assigned += 1
            except Exception as e:
                errors.append(f"Customer {customer.name}: {e}")

        return {"assigned": assigned, "skipped": skipped, "errors": errors}

    def import_from_mappings(
        self,
        tenant: Tenant,
        mappings: list[dict],
    ) -> dict:
        """Import debitor account numbers from a list of mappings.

        Each mapping: {"customer_number": "CUS174", "customer_name": "...", "account_number": "10001"}
        Matches by customer_number first, then customer_name.

        Returns dict with matched, created, conflicts.
        """
        from apps.customers.models import Customer

        matched = 0
        created = 0
        conflicts = []

        for mapping in mappings:
            customer_number = mapping.get("customer_number", "").strip()
            customer_name = mapping.get("customer_name", "").strip()
            account_number = mapping.get("account_number", "").strip()

            if not account_number:
                continue

            # Find customer
            customer = None
            if customer_number:
                customer = Customer.objects.filter(
                    tenant=tenant,
                    netsuite_customer_number=customer_number,
                ).first()

            if not customer and customer_name:
                customer = Customer.objects.filter(
                    tenant=tenant,
                    name__iexact=customer_name,
                ).first()

            if not customer:
                conflicts.append({
                    "customer_name": customer_name or customer_number,
                    "imported_number": account_number,
                    "existing_number": "",
                    "reason": "Customer not found",
                })
                continue

            # Check for conflicts
            existing = DebitorAccount.objects.filter(
                tenant=tenant,
                account_number=account_number,
            ).exclude(customer=customer).first()

            if existing:
                conflicts.append({
                    "customer_name": customer.name,
                    "imported_number": account_number,
                    "existing_number": account_number,
                    "reason": f"Number already assigned to {existing.customer.name}",
                })
                continue

            debitor, was_created = DebitorAccount.objects.get_or_create(
                tenant=tenant,
                customer=customer,
            )

            if debitor.account_number and debitor.account_number != account_number:
                conflicts.append({
                    "customer_name": customer.name,
                    "imported_number": account_number,
                    "existing_number": debitor.account_number,
                    "reason": "Customer already has a different number",
                })
                continue

            debitor.account_number = account_number
            debitor.save(update_fields=["account_number", "updated_at"])

            if was_created:
                created += 1
            else:
                matched += 1

        return {"matched": matched, "created": created, "conflicts": conflicts}

    def _next_number(self, tenant: Tenant) -> str:
        """Get and increment the next available debitor account number."""
        scheme, _ = DebitorAccountScheme.objects.get_or_create(tenant=tenant)

        if scheme.next_number > scheme.end_number:
            raise ValueError(
                f"Debitor number range exhausted ({scheme.start_number}–{scheme.end_number})"
            )

        number = f"{scheme.prefix}{scheme.next_number}"
        scheme.next_number += 1
        scheme.save(update_fields=["next_number", "updated_at"])
        return number
