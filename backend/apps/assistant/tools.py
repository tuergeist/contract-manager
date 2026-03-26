"""Claude API tool definitions for the AI assistant.

Each tool is a plain function: (tenant, **params) -> str
Tool schemas follow the Anthropic tool_use format.
"""

import json as json_module
from datetime import date
from decimal import Decimal

from apps.contracts.models import Contract, ContractItem
from apps.customers.models import Customer
from apps.invoices.models import ImportedInvoice, InvoiceRecord
from apps.products.models import Product


def _fmt_currency(value, currency="EUR"):
    if value is None:
        return "-"
    if isinstance(value, str):
        value = Decimal(value)
    return f"{value:,.2f} {currency}"


def _fmt_date(d):
    if d is None:
        return "-"
    if hasattr(d, "date"):
        d = d.date()
    return d.strftime("%d.%m.%Y")


# --- Tool implementations ---


def search_customers(tenant, search: str = "", limit: int = 20) -> str:
    qs = Customer.objects.filter(tenant=tenant).order_by("name")
    if search:
        qs = qs.filter(name__icontains=search)
    total = qs.count()
    customers = list(qs[:limit])
    if not customers:
        return f"No customers found matching '{search}'. (Total customers: {total})"
    lines = [f"Found {total} customer(s):", ""]
    for c in customers:
        contract_count = Contract.objects.filter(customer=c).count()
        lines.append(f"- **{c.name}** (ID: {c.id}) — {contract_count} contract(s)")
        if c.billing_emails:
            lines.append(f"  Billing: {', '.join(c.billing_emails)}")
    if total > limit:
        lines.append(f"\n(Showing first {limit} of {total})")
    return "\n".join(lines)


def get_customer_details(tenant, customer_id: int) -> str:
    try:
        c = Customer.objects.get(id=customer_id, tenant=tenant)
    except Customer.DoesNotExist:
        return f"Customer {customer_id} not found."

    lines = [f"# {c.name}", f"ID: {c.id}"]
    if c.vat_id:
        lines.append(f"VAT ID: {c.vat_id}")
    if c.address:
        lines.append(f"Address: {c.address}")
    if c.billing_emails:
        lines.append(f"Billing Emails: {', '.join(c.billing_emails)}")

    contacts = list(c.contacts.all()) if hasattr(c, "contacts") else []
    if contacts:
        lines.append("\n## Contacts")
        for contact in contacts:
            name = f"{contact.first_name} {contact.last_name}".strip()
            email = f" ({contact.email})" if contact.email else ""
            lines.append(f"- {name}{email}")

    contracts = Contract.objects.filter(customer=c).order_by("-start_date")[:10]
    if contracts:
        lines.append("\n## Contracts")
        for contract in contracts:
            lines.append(
                f"- {contract.name} (ID: {contract.id}) — "
                f"{contract.status}, started {_fmt_date(contract.start_date)}"
            )
    return "\n".join(lines)


def search_contracts(
    tenant, status: str = "", customer_id: int = 0, search: str = "", limit: int = 20
) -> str:
    qs = Contract.objects.filter(tenant=tenant).select_related("customer").order_by("-start_date")
    if status:
        qs = qs.filter(status=status)
    if customer_id:
        qs = qs.filter(customer_id=customer_id)
    if search:
        qs = qs.filter(name__icontains=search)
    total = qs.count()
    contracts = list(qs[:limit])
    if not contracts:
        return f"No contracts found. (Total: {total})"
    lines = [f"Found {total} contract(s):", ""]
    for c in contracts:
        customer_name = c.customer.name if c.customer else "No customer"
        lines.append(f"- **{c.name}** (ID: {c.id})")
        lines.append(f"  Customer: {customer_name} | Status: {c.status} | Cycle: {c.billing_interval}")
        lines.append(f"  Start: {_fmt_date(c.start_date)}")
    if total > limit:
        lines.append(f"\n(Showing first {limit} of {total})")
    return "\n".join(lines)


def get_contract_details(tenant, contract_id: int) -> str:
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
        f"Start Date: {_fmt_date(c.start_date)}",
    ]
    if c.end_date:
        lines.append(f"End Date: {_fmt_date(c.end_date)}")
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
            lines.append(f"- {name}: {_fmt_currency(total)}")
            if item.quantity and item.unit_price:
                lines.append(f"  {item.quantity} x {_fmt_currency(item.unit_price)}")
        lines.append(f"\n**Total Recurring: {_fmt_currency(total_recurring)}**")

    if one_off:
        lines.append("\n## One-Off Items")
        total_one_off = Decimal("0")
        for item in one_off:
            name = item.product.name if item.product else item.description or "Item"
            total = item.total_price or Decimal("0")
            total_one_off += total
            lines.append(f"- {name}: {_fmt_currency(total)}")
        lines.append(f"\n**Total One-Off: {_fmt_currency(total_one_off)}**")

    return "\n".join(lines)


def search_invoices(
    tenant, customer_id: int = 0, status: str = "", date_from: str = "", date_to: str = "", limit: int = 20
) -> str:
    results = []

    # Generated invoices
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
            "gross": r.total_gross,
            "status": r.status,
        })

    # Imported invoices
    imported = ImportedInvoice.objects.filter(tenant=tenant).select_related("customer")
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
            "customer": inv.customer.name if inv.customer else inv.customer_name or "-",
            "gross": inv.total_amount,
            "status": "imported",
        })

    results.sort(key=lambda x: x["date"] or date.min, reverse=True)
    total = len(results)
    page = results[:limit]
    if not page:
        return "No invoices found."

    lines = [f"Found {total} invoice(s):", ""]
    for inv in page:
        lines.append(
            f"- **{inv['number']}** ({inv['type']}, ID: {inv['id']}) — "
            f"{_fmt_date(inv['date'])} | {inv['customer']} | {_fmt_currency(inv['gross'])} | {inv['status']}"
        )
    if total > limit:
        lines.append(f"\n(Showing first {limit} of {total})")
    return "\n".join(lines)


def get_invoice_details(tenant, invoice_id: int, invoice_type: str = "generated") -> str:
    if invoice_type == "imported":
        try:
            inv = ImportedInvoice.objects.select_related("customer").get(id=invoice_id, tenant=tenant)
        except ImportedInvoice.DoesNotExist:
            return f"Imported invoice {invoice_id} not found."
        return "\n".join([
            f"# {inv.invoice_number or f'IMP-{inv.id}'}",
            f"Type: Imported",
            f"Date: {_fmt_date(inv.invoice_date)}",
            f"Customer: {inv.customer.name if inv.customer else inv.customer_name or '-'}",
            f"Amount: {_fmt_currency(inv.total_amount)}",
        ])

    try:
        r = InvoiceRecord.objects.select_related("customer", "contract").get(id=invoice_id, tenant=tenant)
    except InvoiceRecord.DoesNotExist:
        return f"Invoice {invoice_id} not found."

    lines = [
        f"# {r.invoice_number}",
        f"Status: {r.status}",
        f"Date: {_fmt_date(r.invoice_date)}",
        f"Customer: {r.customer.name if r.customer else '-'}",
        f"Contract: {r.contract.name if r.contract else '-'}",
        f"Period: {_fmt_date(r.period_start)} – {_fmt_date(r.period_end)}",
        f"Net: {_fmt_currency(r.total_net)}",
        f"Gross: {_fmt_currency(r.total_gross)}",
    ]
    if r.email_sent_at:
        recipients = ", ".join(r.email_sent_to or [])
        lines.append(f"Email Sent: {_fmt_date(r.email_sent_at)} to {recipients}")

    items = r.items_snapshot or []
    if items:
        lines.append("\n## Line Items")
        for item in items:
            name = item.get("description") or item.get("product_name", "Item")
            total = item.get("total_price")
            lines.append(f"- {name}: {_fmt_currency(total)}")

    return "\n".join(lines)


def search_products(tenant, search: str = "", limit: int = 20) -> str:
    qs = Product.objects.filter(tenant=tenant).order_by("name")
    if search:
        qs = qs.filter(name__icontains=search)
    total = qs.count()
    products = list(qs[:limit])
    if not products:
        return f"No products found. (Total: {total})"
    lines = [f"Found {total} product(s):", ""]
    for p in products:
        lines.append(f"- **{p.name}** (ID: {p.id})")
        if p.sku:
            lines.append(f"  SKU: {p.sku}")
        if p.billing_frequency:
            lines.append(f"  Billing: {p.billing_frequency}")
    return "\n".join(lines)


def get_revenue_summary(tenant) -> str:
    active_contracts = Contract.objects.filter(tenant=tenant, status="active")
    active_count = active_contracts.count()

    total_mrr = Decimal("0")
    for contract in active_contracts.prefetch_related("items"):
        for item in contract.items.filter(is_one_off=False):
            price = item.total_price or Decimal("0")
            interval = contract.billing_interval
            if interval == "yearly":
                total_mrr += price / 12
            elif interval == "quarterly":
                total_mrr += price / 3
            elif interval == "half_yearly":
                total_mrr += price / 6
            else:
                total_mrr += price

    total_customers = Customer.objects.filter(tenant=tenant).count()
    customers_with_contracts = (
        Customer.objects.filter(tenant=tenant, contracts__status="active").distinct().count()
    )

    # Top customers by recurring revenue
    customer_revenue = {}
    for contract in active_contracts.select_related("customer").prefetch_related("items"):
        if not contract.customer:
            continue
        rev = Decimal("0")
        for item in contract.items.filter(is_one_off=False):
            rev += item.total_price or Decimal("0")
        customer_revenue[contract.customer.name] = customer_revenue.get(contract.customer.name, Decimal("0")) + rev

    top_customers = sorted(customer_revenue.items(), key=lambda x: x[1], reverse=True)[:10]

    lines = [
        "# Revenue Summary",
        f"**MRR (Monthly Recurring Revenue): {_fmt_currency(total_mrr)}**",
        f"**ARR (Annual Recurring Revenue): {_fmt_currency(total_mrr * 12)}**",
        f"Active Contracts: {active_count}",
        f"Total Customers: {total_customers}",
        f"Customers with Active Contracts: {customers_with_contracts}",
    ]

    if top_customers:
        lines.append("\n## Top Customers by Recurring Revenue")
        for name, rev in top_customers:
            lines.append(f"- {name}: {_fmt_currency(rev)}")

    return "\n".join(lines)


def run_graphql(tenant, user, query: str, variables: dict | None = None) -> str:
    """Execute a GraphQL query against the schema with the user's auth context."""
    import asyncio

    from django.test import RequestFactory

    from apps.core.context import Context
    from config.schema import schema

    # Build a fake request with the user attached
    factory = RequestFactory()
    request = factory.post("/graphql")
    request.user = user

    context = Context(request=request, user=user)

    # Execute synchronously
    try:
        loop = asyncio.new_event_loop()
        result = loop.run_until_complete(
            schema.execute(query, variable_values=variables or {}, context_value=context)
        )
        loop.close()
    except Exception as e:
        return f"GraphQL execution error: {e}"

    if result.errors:
        error_msgs = [str(e) for e in result.errors]
        return f"GraphQL errors:\n" + "\n".join(f"- {e}" for e in error_msgs)

    # Convert result to readable string
    def _serialize(obj):
        if isinstance(obj, Decimal):
            return str(obj)
        if isinstance(obj, date):
            return obj.isoformat()
        raise TypeError(f"Not serializable: {type(obj)}")

    return json_module.dumps(result.data, indent=2, default=_serialize, ensure_ascii=False)


# --- Tool registry ---

TOOL_DEFINITIONS = [
    {
        "name": "search_customers",
        "description": "Search for customers by name. Returns a list with name, ID, and contract count.",
        "input_schema": {
            "type": "object",
            "properties": {
                "search": {"type": "string", "description": "Customer name to search for (partial match)"},
                "limit": {"type": "integer", "description": "Max results to return", "default": 20},
            },
        },
    },
    {
        "name": "get_customer_details",
        "description": "Get detailed information about a specific customer including contacts, billing emails, and linked contracts.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "integer", "description": "The customer ID"},
            },
            "required": ["customer_id"],
        },
    },
    {
        "name": "search_contracts",
        "description": "Search and filter contracts. Can filter by status (draft/active/paused/cancelled/ended), customer_id, or text search.",
        "input_schema": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "description": "Filter by status: draft, active, paused, cancelled, ended"},
                "customer_id": {"type": "integer", "description": "Filter by customer ID"},
                "search": {"type": "string", "description": "Search in contract name"},
                "limit": {"type": "integer", "description": "Max results", "default": 20},
            },
        },
    },
    {
        "name": "get_contract_details",
        "description": "Get full contract details including line items (recurring and one-off), financial totals, and billing info.",
        "input_schema": {
            "type": "object",
            "properties": {
                "contract_id": {"type": "integer", "description": "The contract ID"},
            },
            "required": ["contract_id"],
        },
    },
    {
        "name": "search_invoices",
        "description": "Search invoices (both generated and imported). Filter by customer_id, status, date range.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "integer", "description": "Filter by customer ID"},
                "status": {"type": "string", "description": "Filter by status (for generated invoices)"},
                "date_from": {"type": "string", "description": "Start date (YYYY-MM-DD)"},
                "date_to": {"type": "string", "description": "End date (YYYY-MM-DD)"},
                "limit": {"type": "integer", "description": "Max results", "default": 20},
            },
        },
    },
    {
        "name": "get_invoice_details",
        "description": "Get detailed invoice information including line items, amounts, and email status.",
        "input_schema": {
            "type": "object",
            "properties": {
                "invoice_id": {"type": "integer", "description": "The invoice ID"},
                "invoice_type": {
                    "type": "string",
                    "enum": ["generated", "imported"],
                    "description": "Type of invoice",
                    "default": "generated",
                },
            },
            "required": ["invoice_id"],
        },
    },
    {
        "name": "search_products",
        "description": "Search the product catalog by name.",
        "input_schema": {
            "type": "object",
            "properties": {
                "search": {"type": "string", "description": "Product name to search for"},
                "limit": {"type": "integer", "description": "Max results", "default": 20},
            },
        },
    },
    {
        "name": "get_revenue_summary",
        "description": "Get an overview of revenue metrics: MRR, ARR, active contract count, customer count, and top customers by recurring revenue.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "run_graphql",
        "description": """Execute a GraphQL query against the contract management system. Use this for complex or analytical queries that the other tools can't answer.

IMPORTANT QUERIES:
- customers(search, isActive, page, pageSize, sortBy, sortOrder): CustomerConnection!
  Returns: { items { id, name, address, vatId, billingEmails, contractCount, activeContractCount }, totalCount }
  address is JSON with keys: street, city, zip, state, country (2-letter code like "DE", "FR", "US")

- contracts(search, status, isNewBusiness, dealWonYear, page, pageSize, sortBy, sortOrder): ContractConnection!
  Returns: { items { id, name, status, customer { id, name, address }, billingInterval, startDate, endDate, monthlyRecurringValue, arr, totalValue, items { description, product { name }, unitPrice, quantity, totalPrice, isOneOff, revenueType } }, totalCount }
  Status values: draft, active, paused, cancelled, ended

- products(search, isActive, revenueType, page, pageSize): ProductConnection!
  Returns: { items { id, name, sku, billingFrequency, revenueType, isActive }, totalCount }

- dashboardKpis: DashboardKPIsType!
  Returns: { totalActiveContracts, totalContractValue, annualRecurringRevenue, yearToDateRevenue, currentYearForecast, nextYearForecast }

- revenueForecast(months, quarters, view, proRata, excludeOneOff): RevenueForecastResult!
  Returns: { monthColumns, monthlyTotals { total }, contracts { contractName, customerName, months { amount } }, grandTotal }

- invoiceRecords(search, contractId, customerId, offset, limit): InvoiceRecordConnection!
  Returns: { items { id, invoiceNumber, customerName, totalNet, totalGross, status, invoiceDate, isPaid }, totalCount }

- bankTransactions(search, dateFrom, dateTo, direction, page, pageSize): BankTransactionPage!
  Returns: { items { id, entryDate, amount, counterparty { name }, bookingText }, totalCount }

TIPS:
- For country-based queries, filter in the query or return address data and I'll count
- Use pageSize up to 200 for aggregation queries
- All data is automatically scoped to the user's tenant""",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The GraphQL query string",
                },
                "variables": {
                    "type": "object",
                    "description": "Optional GraphQL variables",
                },
            },
            "required": ["query"],
        },
    },
]

TOOL_EXECUTORS = {
    "search_customers": search_customers,
    "get_customer_details": get_customer_details,
    "search_contracts": search_contracts,
    "get_contract_details": get_contract_details,
    "search_invoices": search_invoices,
    "get_invoice_details": get_invoice_details,
    "search_products": search_products,
    "get_revenue_summary": get_revenue_summary,
    "run_graphql": run_graphql,
}

# Tools that need the user object (not just tenant)
_USER_TOOLS = {"run_graphql"}
# Tools that take no data args (just tenant)
_NO_ARGS_TOOLS = {"get_revenue_summary"}


def execute_tool(tenant, tool_name: str, tool_input: dict, user=None) -> str:
    """Execute a tool by name with the given input, scoped to tenant."""
    executor = TOOL_EXECUTORS.get(tool_name)
    if not executor:
        return f"Unknown tool: {tool_name}"
    try:
        if tool_name in _NO_ARGS_TOOLS:
            return executor(tenant)
        if tool_name in _USER_TOOLS:
            return executor(tenant, user, **tool_input)
        return executor(tenant, **tool_input)
    except Exception as e:
        return f"Tool error: {e}"
