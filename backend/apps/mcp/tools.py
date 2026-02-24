"""MCP tool definitions for contract-manager."""

from datetime import date, datetime
from decimal import Decimal

from mcp_server import MCPToolset

from apps.contracts.models import Contract, ContractItem
from apps.customers.models import Customer
from apps.invoices.models import ImportedInvoice, InvoiceRecord
from apps.products.models import Product


class _BaseTool(MCPToolset):
    """Base class with tenant resolution and permission checking."""

    def _get_user(self):
        user = getattr(self.request, "user", None)
        if not user or not user.is_authenticated:
            return None
        return user

    def _get_tenant(self):
        user = self._get_user()
        if not user:
            return None
        return getattr(user, "tenant", None)

    def _check_perm(self, resource: str, action: str) -> str | None:
        """Check permission, return error message or None if allowed."""
        user = self._get_user()
        if not user:
            return "Authentication required."
        tenant = self._get_tenant()
        if not tenant or not tenant.is_active:
            return "No active tenant."
        if not user.has_perm_check(resource, action):
            return f"Permission denied: {resource}.{action}"
        return None

    def _check_scope(self, required_scope: str) -> str | None:
        """Check OAuth token scope, return error or None."""
        token = getattr(self.request, "auth", None)
        if token and hasattr(token, "scope"):
            if required_scope not in token.scope.split():
                return f"Scope '{required_scope}' required. Your token only has: {token.scope}"
        return None

    def _fmt_currency(self, value, currency="EUR") -> str:
        if value is None:
            return "-"
        if isinstance(value, str):
            value = Decimal(value)
        return f"{value:,.2f} {currency}"

    def _fmt_date(self, d) -> str:
        if d is None:
            return "-"
        if isinstance(d, datetime):
            d = d.date()
        return d.strftime("%d.%m.%Y")


class CustomerTools(_BaseTool):
    def list_customers(self, search: str = "", offset: int = 0, limit: int = 20) -> str:
        """List customers with optional search. Returns name, company, email, and contract count."""
        if err := self._check_perm("customers", "read"):
            return err
        tenant = self._get_tenant()
        qs = Customer.objects.filter(tenant=tenant).order_by("name")
        if search:
            qs = qs.filter(name__icontains=search)
        total = qs.count()
        customers = qs[offset:offset + limit]
        if not customers:
            return f"No customers found. (Total: {total})"
        lines = [f"Customers (showing {offset + 1}-{offset + len(customers)} of {total})", ""]
        for c in customers:
            contract_count = Contract.objects.filter(customer=c).count()
            lines.append(f"- **{c.name}** (ID: {c.id})")
            if c.vat_id:
                lines.append(f"  VAT ID: {c.vat_id}")
            if c.billing_emails:
                lines.append(f"  Billing: {', '.join(c.billing_emails)}")
            lines.append(f"  Contracts: {contract_count}")
        return "\n".join(lines)

    def get_customer(self, customer_id: int) -> str:
        """Get detailed customer information including contacts and contracts."""
        if err := self._check_perm("customers", "read"):
            return err
        tenant = self._get_tenant()
        try:
            c = Customer.objects.get(id=customer_id, tenant=tenant)
        except Customer.DoesNotExist:
            return f"Customer {customer_id} not found."

        lines = [f"# {c.name}", f"ID: {c.id}"]
        if c.address:
            lines.append(f"Address: {c.address}")
        if c.vat_id:
            lines.append(f"VAT ID: {c.vat_id}")

        billing_emails = c.billing_emails or []
        if billing_emails:
            lines.append(f"Billing Emails: {', '.join(billing_emails)}")

        contacts = list(c.contacts.all()) if hasattr(c, "contacts") else []
        if contacts:
            lines.append("\n## Contacts")
            for contact in contacts:
                name = f"{contact.first_name} {contact.last_name}".strip()
                lines.append(f"- {name}")
                if contact.email:
                    lines.append(f"  Email: {contact.email}")

        contracts = Contract.objects.filter(customer=c).order_by("-start_date")
        if contracts.exists():
            lines.append("\n## Contracts")
            for contract in contracts[:10]:
                lines.append(
                    f"- {contract.name} (ID: {contract.id}) — "
                    f"{contract.status}, started {self._fmt_date(contract.start_date)}"
                )

        return "\n".join(lines)


class ProductTools(_BaseTool):
    def list_products(self, search: str = "", offset: int = 0, limit: int = 20) -> str:
        """List products with optional search. Shows name, SKU, price, and billing cycle."""
        if err := self._check_perm("products", "read"):
            return err
        tenant = self._get_tenant()
        qs = Product.objects.filter(tenant=tenant).order_by("name")
        if search:
            qs = qs.filter(name__icontains=search)
        total = qs.count()
        products = qs[offset:offset + limit]
        if not products:
            return f"No products found. (Total: {total})"
        lines = [f"Products (showing {offset + 1}-{offset + len(products)} of {total})", ""]
        for p in products:
            lines.append(f"- **{p.name}** (ID: {p.id})")
            if p.sku:
                lines.append(f"  SKU: {p.sku}")
            if p.billing_frequency:
                lines.append(f"  Billing: {p.billing_frequency}")
        return "\n".join(lines)

    def get_product(self, product_id: int) -> str:
        """Get detailed product information."""
        if err := self._check_perm("products", "read"):
            return err
        tenant = self._get_tenant()
        try:
            p = Product.objects.get(id=product_id, tenant=tenant)
        except Product.DoesNotExist:
            return f"Product {product_id} not found."

        lines = [f"# {p.name}", f"ID: {p.id}"]
        if p.sku:
            lines.append(f"SKU: {p.sku}")
        if p.billing_frequency:
            lines.append(f"Billing: {p.billing_frequency}")
        if p.description:
            lines.append(f"\n{p.description}")
        return "\n".join(lines)


class ContractTools(_BaseTool):
    def list_contracts(
        self,
        status: str = "",
        customer_id: int = 0,
        search: str = "",
        offset: int = 0,
        limit: int = 20,
    ) -> str:
        """List contracts with optional filters. Shows name, customer, status, and MRR."""
        if err := self._check_perm("contracts", "read"):
            return err
        tenant = self._get_tenant()
        qs = Contract.objects.filter(tenant=tenant).select_related("customer").order_by("-start_date")
        if status:
            qs = qs.filter(status=status)
        if customer_id:
            qs = qs.filter(customer_id=customer_id)
        if search:
            qs = qs.filter(name__icontains=search)
        total = qs.count()
        contracts = qs[offset:offset + limit]
        if not contracts:
            return f"No contracts found. (Total: {total})"
        lines = [f"Contracts (showing {offset + 1}-{offset + len(contracts)} of {total})", ""]
        for c in contracts:
            customer_name = c.customer.name if c.customer else "No customer"
            lines.append(f"- **{c.name}** (ID: {c.id})")
            lines.append(f"  Customer: {customer_name} | Status: {c.status}")
            lines.append(f"  Start: {self._fmt_date(c.start_date)} | Cycle: {c.billing_interval}")
        return "\n".join(lines)

    def get_contract(self, contract_id: int) -> str:
        """Get contract details including items and financial summary."""
        if err := self._check_perm("contracts", "read"):
            return err
        tenant = self._get_tenant()
        try:
            c = Contract.objects.select_related("customer").get(id=contract_id, tenant=tenant)
        except Contract.DoesNotExist:
            return f"Contract {contract_id} not found."

        lines = [
            f"# {c.name}",
            f"ID: {c.id}",
            f"Status: {c.status}",
            f"Customer: {c.customer.name if c.customer else 'None'}",
            f"Billing Cycle: {c.billing_interval}",
            f"Start Date: {self._fmt_date(c.start_date)}",
        ]
        if c.end_date:
            lines.append(f"End Date: {self._fmt_date(c.end_date)}")
        if c.notes:
            lines.append(f"Notes: {c.notes}")

        items = ContractItem.objects.filter(contract=c).select_related("product").order_by("sort_order")
        recurring = [i for i in items if not i.is_one_off]
        one_off = [i for i in items if i.is_one_off]

        if recurring:
            lines.append("\n## Recurring Items")
            total_recurring = Decimal("0")
            for item in recurring:
                name = item.product.name if item.product else item.description or "Item"
                total = item.total_price or Decimal("0")
                total_recurring += total
                lines.append(f"- {name}: {self._fmt_currency(total)}")
                if item.quantity and item.unit_price:
                    lines.append(f"  {item.quantity} x {self._fmt_currency(item.unit_price)}")
            lines.append(f"\n**Total Recurring: {self._fmt_currency(total_recurring)}**")

        if one_off:
            lines.append("\n## One-Off Items")
            total_one_off = Decimal("0")
            for item in one_off:
                name = item.product.name if item.product else item.description or "Item"
                total = item.total_price or Decimal("0")
                total_one_off += total
                lines.append(f"- {name}: {self._fmt_currency(total)}")
            lines.append(f"\n**Total One-Off: {self._fmt_currency(total_one_off)}**")

        return "\n".join(lines)


class InvoiceTools(_BaseTool):
    def list_invoices(
        self,
        customer_id: int = 0,
        status: str = "",
        date_from: str = "",
        date_to: str = "",
        offset: int = 0,
        limit: int = 20,
    ) -> str:
        """List invoices (both generated and imported). Filters: customer_id, status, date_from, date_to."""
        if err := self._check_perm("invoices", "read"):
            return err
        tenant = self._get_tenant()
        results = []

        # Generated invoices (InvoiceRecord)
        records = InvoiceRecord.objects.filter(tenant=tenant).select_related("customer")
        if customer_id:
            records = records.filter(customer_id=customer_id)
        if status:
            records = records.filter(status=status)
        if date_from:
            records = records.filter(invoice_date__gte=date_from)
        if date_to:
            records = records.filter(invoice_date__lte=date_to)
        for r in records.order_by("-invoice_date"):
            results.append({
                "type": "generated",
                "id": r.id,
                "number": r.invoice_number,
                "date": r.invoice_date,
                "customer": r.customer.name if r.customer else "-",
                "net": r.total_net,
                "gross": r.total_gross,
                "status": r.status,
                "email_sent": bool(r.email_sent_at),
            })

        # Imported invoices
        imported = ImportedInvoice.objects.filter(tenant=tenant)
        if customer_id:
            imported = imported.filter(customer_id=customer_id)
        if date_from:
            imported = imported.filter(invoice_date__gte=date_from)
        if date_to:
            imported = imported.filter(invoice_date__lte=date_to)
        for inv in imported.order_by("-invoice_date"):
            results.append({
                "type": "imported",
                "id": inv.id,
                "number": inv.invoice_number or f"IMP-{inv.id}",
                "date": inv.invoice_date,
                "customer": inv.customer.name if inv.customer else inv.vendor_name or "-",
                "net": inv.net_amount,
                "gross": inv.gross_amount,
                "status": "imported",
                "email_sent": False,
            })

        # Sort by date descending
        results.sort(key=lambda x: x["date"] or date.min, reverse=True)
        total = len(results)
        page = results[offset:offset + limit]
        if not page:
            return f"No invoices found. (Total: {total})"

        lines = [f"Invoices (showing {offset + 1}-{offset + len(page)} of {total})", ""]
        for inv in page:
            sent = " [email sent]" if inv["email_sent"] else ""
            lines.append(
                f"- **{inv['number']}** ({inv['type']}, ID: {inv['id']})"
            )
            lines.append(
                f"  {self._fmt_date(inv['date'])} | {inv['customer']} | "
                f"Net: {self._fmt_currency(inv['net'])} | "
                f"Gross: {self._fmt_currency(inv['gross'])} | "
                f"{inv['status']}{sent}"
            )
        return "\n".join(lines)

    def get_invoice(self, invoice_id: int, invoice_type: str = "generated") -> str:
        """Get invoice details. invoice_type: 'generated' or 'imported'."""
        if err := self._check_perm("invoices", "read"):
            return err
        tenant = self._get_tenant()

        if invoice_type == "imported":
            try:
                inv = ImportedInvoice.objects.select_related("customer").get(
                    id=invoice_id, tenant=tenant
                )
            except ImportedInvoice.DoesNotExist:
                return f"Imported invoice {invoice_id} not found."
            lines = [
                f"# {inv.invoice_number or f'IMP-{inv.id}'}",
                f"Type: Imported",
                f"Date: {self._fmt_date(inv.invoice_date)}",
                f"Customer: {inv.customer.name if inv.customer else inv.vendor_name or '-'}",
                f"Net: {self._fmt_currency(inv.net_amount)}",
                f"Gross: {self._fmt_currency(inv.gross_amount)}",
            ]
            return "\n".join(lines)

        try:
            r = InvoiceRecord.objects.select_related("customer", "contract").get(
                id=invoice_id, tenant=tenant
            )
        except InvoiceRecord.DoesNotExist:
            return f"Invoice record {invoice_id} not found."

        lines = [
            f"# {r.invoice_number}",
            f"Type: Generated",
            f"Status: {r.status}",
            f"Date: {self._fmt_date(r.invoice_date)}",
            f"Customer: {r.customer.name if r.customer else '-'}",
            f"Contract: {r.contract.name if r.contract else '-'}",
            f"Period: {self._fmt_date(r.period_start)} – {self._fmt_date(r.period_end)}",
            f"Net: {self._fmt_currency(r.total_net)}",
            f"Gross: {self._fmt_currency(r.total_gross)}",
            f"PDF: {'Yes' if r.pdf_file else 'No'}",
        ]
        if r.email_sent_at:
            recipients = ", ".join(r.email_sent_to or [])
            lines.append(f"Email Sent: {self._fmt_date(r.email_sent_at)} to {recipients}")
        else:
            lines.append("Email: Not sent")

        # Line items from snapshot
        items = r.items_snapshot or []
        if items:
            lines.append("\n## Line Items")
            for item in items:
                name = item.get("description") or item.get("product_name", "Item")
                total = item.get("total_price")
                lines.append(f"- {name}: {self._fmt_currency(total)}")

        return "\n".join(lines)


class BankingTools(_BaseTool):
    def list_transactions(
        self,
        counterparty: str = "",
        date_from: str = "",
        date_to: str = "",
        offset: int = 0,
        limit: int = 20,
    ) -> str:
        """List bank transactions with optional filters."""
        if err := self._check_perm("banking", "read"):
            return err
        tenant = self._get_tenant()
        from apps.banking.models import BankTransaction
        qs = BankTransaction.objects.filter(account__tenant=tenant).order_by("-date")
        if counterparty:
            qs = qs.filter(counterparty_name__icontains=counterparty)
        if date_from:
            qs = qs.filter(date__gte=date_from)
        if date_to:
            qs = qs.filter(date__lte=date_to)
        total = qs.count()
        txns = qs[offset:offset + limit]
        if not txns:
            return f"No transactions found. (Total: {total})"
        lines = [f"Transactions (showing {offset + 1}-{offset + len(txns)} of {total})", ""]
        for t in txns:
            color = "+" if t.amount >= 0 else ""
            lines.append(f"- {self._fmt_date(t.date)} | {color}{self._fmt_currency(t.amount)}")
            lines.append(f"  {t.counterparty_name or 'Unknown'}")
            if t.purpose:
                lines.append(f"  Purpose: {t.purpose[:80]}")
        return "\n".join(lines)

    def get_transaction(self, transaction_id: int) -> str:
        """Get detailed bank transaction information."""
        if err := self._check_perm("banking", "read"):
            return err
        tenant = self._get_tenant()
        from apps.banking.models import BankTransaction
        try:
            t = BankTransaction.objects.select_related("account").get(
                id=transaction_id, account__tenant=tenant
            )
        except BankTransaction.DoesNotExist:
            return f"Transaction {transaction_id} not found."
        lines = [
            f"# Transaction {t.id}",
            f"Date: {self._fmt_date(t.date)}",
            f"Amount: {self._fmt_currency(t.amount)}",
            f"Counterparty: {t.counterparty_name or '-'}",
            f"Account: {t.account.name if t.account else '-'}",
        ]
        if t.purpose:
            lines.append(f"Purpose: {t.purpose}")
        if t.counterparty_iban:
            lines.append(f"IBAN: {t.counterparty_iban}")
        return "\n".join(lines)


class WriteTools(_BaseTool):
    def generate_invoices(self, contract_id: int, billing_date: str) -> str:
        """Generate invoices for a contract and billing date (YYYY-MM-DD format)."""
        if err := self._check_scope("write"):
            return err
        if err := self._check_perm("invoices", "generate"):
            return err
        tenant = self._get_tenant()
        try:
            contract = Contract.objects.get(id=contract_id, tenant=tenant)
        except Contract.DoesNotExist:
            return f"Contract {contract_id} not found."

        try:
            billing_dt = date.fromisoformat(billing_date)
        except ValueError:
            return f"Invalid date format: {billing_date}. Use YYYY-MM-DD."

        from apps.invoices.services import InvoiceService
        service = InvoiceService(tenant)
        try:
            records = service.generate_for_contract(contract, billing_dt)
        except Exception as e:
            return f"Invoice generation failed: {e}"

        if not records:
            return f"No invoices generated for contract '{contract.name}' on {billing_date}."

        lines = [f"Generated {len(records)} invoice(s) for '{contract.name}':", ""]
        for r in records:
            lines.append(
                f"- {r.invoice_number}: Net {self._fmt_currency(r.total_net)}, "
                f"Gross {self._fmt_currency(r.total_gross)}"
            )
        return "\n".join(lines)

    def void_invoice(self, invoice_id: int, reason: str = "") -> str:
        """Void a generated invoice record."""
        if err := self._check_scope("write"):
            return err
        if err := self._check_perm("invoices", "write"):
            return err
        tenant = self._get_tenant()
        try:
            record = InvoiceRecord.objects.get(id=invoice_id, tenant=tenant)
        except InvoiceRecord.DoesNotExist:
            return f"Invoice record {invoice_id} not found."

        if record.status == "voided":
            return f"Invoice {record.invoice_number} is already voided."

        from apps.invoices.services import InvoiceService
        service = InvoiceService(tenant)
        try:
            service.void_invoice(record, reason=reason)
        except Exception as e:
            return f"Failed to void invoice: {e}"

        return f"Invoice {record.invoice_number} has been voided."

    def send_invoice_email(self, invoice_id: int) -> str:
        """Send an invoice email to the customer's billing addresses."""
        if err := self._check_scope("write"):
            return err
        if err := self._check_perm("invoices", "write"):
            return err
        tenant = self._get_tenant()
        try:
            record = InvoiceRecord.objects.select_related("customer").get(
                id=invoice_id, tenant=tenant
            )
        except InvoiceRecord.DoesNotExist:
            return f"Invoice record {invoice_id} not found."

        if not record.customer:
            return "Invoice has no customer assigned."

        recipients = record.customer.billing_emails or []
        if not recipients:
            return f"Customer '{record.customer.name}' has no billing email addresses configured."

        if not record.pdf_file:
            return f"Invoice {record.invoice_number} has no PDF generated yet."

        from apps.invoices.tasks import send_invoice_email_task
        user = self._get_user()
        send_invoice_email_task.delay(record.id, user_id=user.id if user else None)

        return (
            f"Invoice email for {record.invoice_number} queued for sending to: "
            f"{', '.join(recipients)}"
        )

    def create_contract(
        self,
        customer_id: int,
        name: str,
        billing_cycle: str = "monthly",
        start_date: str = "",
    ) -> str:
        """Create a new draft contract. billing_cycle: monthly, quarterly, yearly."""
        if err := self._check_scope("write"):
            return err
        if err := self._check_perm("contracts", "write"):
            return err
        tenant = self._get_tenant()
        try:
            customer = Customer.objects.get(id=customer_id, tenant=tenant)
        except Customer.DoesNotExist:
            return f"Customer {customer_id} not found."

        start_dt = None
        if start_date:
            try:
                start_dt = date.fromisoformat(start_date)
            except ValueError:
                return f"Invalid date format: {start_date}. Use YYYY-MM-DD."

        start = start_dt or date.today()
        contract = Contract.objects.create(
            tenant=tenant,
            customer=customer,
            name=name,
            billing_interval=billing_cycle,
            start_date=start,
            billing_start_date=start,
            status="draft",
        )

        return (
            f"Contract created: '{contract.name}' (ID: {contract.id})\n"
            f"Customer: {customer.name}\n"
            f"Status: draft\n"
            f"Billing Cycle: {billing_cycle}\n"
            f"Start Date: {self._fmt_date(contract.start_date)}"
        )

    def update_contract(
        self,
        contract_id: int,
        name: str = "",
        status: str = "",
        billing_cycle: str = "",
        notes: str = "",
    ) -> str:
        """Update contract fields. Leave empty to skip. Status transitions are validated."""
        if err := self._check_scope("write"):
            return err
        if err := self._check_perm("contracts", "write"):
            return err
        tenant = self._get_tenant()
        try:
            contract = Contract.objects.get(id=contract_id, tenant=tenant)
        except Contract.DoesNotExist:
            return f"Contract {contract_id} not found."

        changes = []
        if name:
            contract.name = name
            changes.append(f"Name → {name}")
        if billing_cycle:
            contract.billing_interval = billing_cycle
            changes.append(f"Billing Cycle → {billing_cycle}")
        if notes:
            contract.notes = notes
            changes.append("Notes updated")

        if status and status != contract.status:
            valid_transitions = {
                "draft": ["active"],
                "active": ["paused", "cancelled"],
                "paused": ["active", "cancelled"],
                "cancelled": ["ended"],
            }
            allowed = valid_transitions.get(contract.status, [])
            if status not in allowed:
                return (
                    f"Invalid status transition: {contract.status} → {status}. "
                    f"Allowed: {', '.join(allowed) if allowed else 'none'}"
                )
            contract.status = status
            changes.append(f"Status → {status}")

        if not changes:
            return "No changes specified."

        contract.save()
        return f"Contract '{contract.name}' (ID: {contract.id}) updated:\n" + "\n".join(
            f"- {c}" for c in changes
        )
