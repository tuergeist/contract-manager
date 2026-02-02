"""Invoice service for generating and exporting invoices."""
import io
import zipfile
from calendar import monthrange
from datetime import date
from decimal import Decimal
from typing import Literal

from django.template.loader import render_to_string

try:
    from weasyprint import HTML
except ImportError:
    HTML = None  # PDF generation will be unavailable

from apps.contracts.models import Contract
from apps.invoices.types import InvoiceData, InvoiceLineItem
from apps.tenants.models import Tenant


# Localization labels for invoice PDF
LABELS = {
    "de": {
        "invoice": "Rechnung",
        "bill_to": "Rechnungsadresse",
        "invoice_date": "Rechnungsdatum",
        "billing_period": "Abrechnungszeitraum",
        "contract": "Vertrag",
        "description": "Beschreibung",
        "quantity": "Menge",
        "unit_price": "Einzelpreis",
        "amount": "Betrag",
        "total": "Gesamtbetrag",
        "prorated": "Anteilig",
        "one_off": "Einmalig",
        "customer_id": "Kunden-Nr.",
    },
    "en": {
        "invoice": "Invoice",
        "bill_to": "Bill To",
        "invoice_date": "Invoice Date",
        "billing_period": "Billing Period",
        "contract": "Contract",
        "description": "Description",
        "quantity": "Qty",
        "unit_price": "Unit Price",
        "amount": "Amount",
        "total": "Total",
        "prorated": "Prorated",
        "one_off": "One-time",
        "customer_id": "Customer ID",
    },
}


class InvoiceService:
    """Service for generating invoices from contract billing schedules."""

    def __init__(self, tenant: Tenant):
        self.tenant = tenant

    def get_invoices_for_month(self, year: int, month: int) -> list[InvoiceData]:
        """
        Get all invoices due for a specific month.

        Aggregates billing events from all active contracts within the tenant
        for the specified month.

        Args:
            year: The year (e.g., 2026)
            month: The month (1-12)

        Returns:
            List of InvoiceData objects, one per contract with billing events
            in the specified month.
        """
        # Calculate date range for the month
        first_day = date(year, month, 1)
        last_day = date(year, month, monthrange(year, month)[1])

        # Get all active contracts for this tenant
        contracts = Contract.objects.filter(
            tenant=self.tenant,
            status=Contract.Status.ACTIVE,
        ).select_related("customer").prefetch_related("items__product")

        invoices = []

        for contract in contracts:
            # Get billing schedule for this contract within the month
            billing_events = contract.get_billing_schedule(
                from_date=first_day,
                to_date=last_day,
            )

            # Create an invoice for each billing event in this month
            for event in billing_events:
                billing_date = event["date"]

                # Skip if billing date is outside our target month
                if billing_date.year != year or billing_date.month != month:
                    continue

                # Skip if no items (shouldn't happen, but defensive)
                if not event["items"]:
                    continue

                # Calculate billing period (depends on contract interval)
                period_start, period_end = self._calculate_billing_period(
                    contract, billing_date
                )

                # Convert billing items to invoice line items
                line_items = []
                for item in event["items"]:
                    line_item = InvoiceLineItem(
                        item_id=item["item_id"],
                        product_name=item["product_name"],
                        description=item.get("description", ""),
                        quantity=item["quantity"],
                        unit_price=item["unit_price"],
                        amount=item["amount"],
                        is_prorated=item.get("is_prorated", False),
                        prorate_factor=item.get("prorate_factor"),
                        is_one_off=item.get("is_one_off", False),
                    )
                    line_items.append(line_item)

                invoice = InvoiceData(
                    contract_id=contract.id,
                    contract_name=contract.name or f"Contract {contract.id}",
                    customer_id=contract.customer.id,
                    customer_name=contract.customer.name,
                    customer_address=contract.customer.address or {},
                    billing_date=billing_date,
                    billing_period_start=period_start,
                    billing_period_end=period_end,
                    line_items=line_items,
                    invoice_text=contract.invoice_text or "",
                )
                invoices.append(invoice)

        # Sort by customer name for consistent ordering
        invoices.sort(key=lambda x: x.customer_name.lower())

        return invoices

    def _calculate_billing_period(
        self, contract: Contract, billing_date: date
    ) -> tuple[date, date]:
        """Calculate the billing period for a given billing date."""
        from dateutil.relativedelta import relativedelta

        interval_months = contract.get_interval_months()

        # Period starts at billing_date
        period_start = billing_date

        # Period ends before next billing date
        period_end = billing_date + relativedelta(months=interval_months, days=-1)

        # Don't extend beyond contract end date
        if contract.end_date and period_end > contract.end_date:
            period_end = contract.end_date

        return period_start, period_end

    def generate_pdf(
        self,
        invoices: list[InvoiceData],
        language: Literal["de", "en"] = "de",
    ) -> bytes:
        """
        Generate a combined PDF containing all invoices.

        Each invoice starts on a new page.

        Args:
            invoices: List of InvoiceData to include in PDF
            language: Language for labels ("de" or "en")

        Returns:
            PDF file as bytes.
        """
        if not invoices:
            return b""

        labels = LABELS.get(language, LABELS["en"])
        currency_symbol = self.tenant.currency_symbol

        # Render each invoice as HTML
        html_parts = []
        for i, invoice in enumerate(invoices):
            # Convert dataclass to dict for template
            invoice_dict = {
                "contract_id": invoice.contract_id,
                "contract_name": invoice.contract_name,
                "customer_id": invoice.customer_id,
                "customer_name": invoice.customer_name,
                "customer_address": invoice.customer_address,
                "billing_date": invoice.billing_date,
                "billing_period_start": invoice.billing_period_start,
                "billing_period_end": invoice.billing_period_end,
                "line_items": [
                    {
                        "item_id": item.item_id,
                        "product_name": item.product_name,
                        "description": item.description,
                        "quantity": item.quantity,
                        "unit_price": item.unit_price,
                        "amount": item.amount,
                        "is_prorated": item.is_prorated,
                        "prorate_factor": item.prorate_factor,
                        "is_one_off": item.is_one_off,
                    }
                    for item in invoice.line_items
                ],
                "total_amount": invoice.total_amount,
            }

            html = render_to_string(
                "invoices/invoice.html",
                {
                    "invoice": invoice_dict,
                    "labels": labels,
                    "language": language,
                    "currency_symbol": currency_symbol,
                    "company_name": self.tenant.name,
                },
            )
            html_parts.append(html)

        # Combine all HTML parts with page breaks
        combined_html = '<div class="page-break"></div>'.join(html_parts)

        # Generate PDF
        pdf_document = HTML(string=combined_html).render()
        return pdf_document.write_pdf()

    def generate_individual_pdfs(
        self,
        invoices: list[InvoiceData],
        year: int,
        month: int,
        language: Literal["de", "en"] = "de",
    ) -> bytes:
        """
        Generate individual PDFs for each invoice, packaged as a ZIP.

        Args:
            invoices: List of InvoiceData to generate PDFs for
            year: Year for filename
            month: Month for filename
            language: Language for labels ("de" or "en")

        Returns:
            ZIP file containing individual PDFs as bytes.
        """
        if not invoices:
            return b""

        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for invoice in invoices:
                # Generate PDF for single invoice
                pdf_bytes = self.generate_pdf([invoice], language)

                # Create safe filename
                customer_safe = self._safe_filename(invoice.customer_name)
                contract_safe = self._safe_filename(invoice.contract_name)
                filename = f"invoice-{customer_safe}-{contract_safe}-{year:04d}-{month:02d}.pdf"

                zip_file.writestr(filename, pdf_bytes)

        return zip_buffer.getvalue()

    def _safe_filename(self, name: str) -> str:
        """Convert a name to a safe filename component."""
        import re
        # Replace spaces with hyphens, remove special characters
        safe = re.sub(r"[^\w\s-]", "", name)
        safe = re.sub(r"[-\s]+", "-", safe).strip("-")
        return safe[:50]  # Limit length

    def generate_excel(
        self,
        invoices: list[InvoiceData],
        year: int,
        month: int,
        language: Literal["de", "en"] = "de",
    ) -> bytes:
        """
        Generate an Excel file with all invoices.

        Creates three sheets:
        - Summary: Overview with totals and breakdown by customer
        - Invoices: One row per invoice
        - Line Items: One row per line item

        Args:
            invoices: List of InvoiceData to include
            year: Year for context
            month: Month for context
            language: Language for headers ("de" or "en")

        Returns:
            Excel file as bytes.
        """
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment

        if not invoices:
            # Return empty workbook
            wb = Workbook()
            buffer = io.BytesIO()
            wb.save(buffer)
            return buffer.getvalue()

        labels = LABELS.get(language, LABELS["en"])

        wb = Workbook()

        # Header style
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="2563EB", end_color="2563EB", fill_type="solid")

        # --- Summary Sheet ---
        ws_summary = wb.active
        ws_summary.title = "Summary"

        # Summary header
        ws_summary["A1"] = f"{labels['invoice']} - {year:04d}-{month:02d}"
        ws_summary["A1"].font = Font(bold=True, size=14)

        ws_summary["A3"] = "Total Invoices"
        ws_summary["B3"] = len(invoices)

        total_amount = sum(inv.total_amount for inv in invoices)
        ws_summary["A4"] = labels["total"]
        ws_summary["B4"] = float(total_amount)
        ws_summary["B4"].number_format = '#,##0.00 "' + self.tenant.currency + '"'

        # Breakdown by customer
        ws_summary["A6"] = "Breakdown by Customer"
        ws_summary["A6"].font = Font(bold=True)

        customer_totals: dict[str, Decimal] = {}
        for inv in invoices:
            customer_totals[inv.customer_name] = (
                customer_totals.get(inv.customer_name, Decimal("0")) + inv.total_amount
            )

        row = 7
        for customer_name, amount in sorted(customer_totals.items()):
            ws_summary[f"A{row}"] = customer_name
            ws_summary[f"B{row}"] = float(amount)
            ws_summary[f"B{row}"].number_format = '#,##0.00 "' + self.tenant.currency + '"'
            row += 1

        # Adjust column widths
        ws_summary.column_dimensions["A"].width = 30
        ws_summary.column_dimensions["B"].width = 15

        # --- Invoices Sheet ---
        ws_invoices = wb.create_sheet("Invoices")

        headers = ["Customer", labels["contract"], labels["invoice_date"], labels["total"]]
        for col, header in enumerate(headers, 1):
            cell = ws_invoices.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill

        for row_num, inv in enumerate(invoices, 2):
            ws_invoices.cell(row=row_num, column=1, value=inv.customer_name)
            ws_invoices.cell(row=row_num, column=2, value=inv.contract_name)
            ws_invoices.cell(row=row_num, column=3, value=inv.billing_date)
            total_cell = ws_invoices.cell(row=row_num, column=4, value=float(inv.total_amount))
            total_cell.number_format = '#,##0.00 "' + self.tenant.currency + '"'

        # Adjust column widths
        ws_invoices.column_dimensions["A"].width = 25
        ws_invoices.column_dimensions["B"].width = 25
        ws_invoices.column_dimensions["C"].width = 12
        ws_invoices.column_dimensions["D"].width = 15

        # --- Line Items Sheet ---
        ws_items = wb.create_sheet("Line Items")

        item_headers = [
            "Customer",
            labels["contract"],
            labels["description"],
            labels["quantity"],
            labels["unit_price"],
            labels["amount"],
        ]
        for col, header in enumerate(item_headers, 1):
            cell = ws_items.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill

        row_num = 2
        for inv in invoices:
            for item in inv.line_items:
                ws_items.cell(row=row_num, column=1, value=inv.customer_name)
                ws_items.cell(row=row_num, column=2, value=inv.contract_name)
                ws_items.cell(row=row_num, column=3, value=item.product_name)
                ws_items.cell(row=row_num, column=4, value=item.quantity)
                price_cell = ws_items.cell(row=row_num, column=5, value=float(item.unit_price))
                price_cell.number_format = '#,##0.00 "' + self.tenant.currency + '"'
                amount_cell = ws_items.cell(row=row_num, column=6, value=float(item.amount))
                amount_cell.number_format = '#,##0.00 "' + self.tenant.currency + '"'
                row_num += 1

        # Adjust column widths
        ws_items.column_dimensions["A"].width = 25
        ws_items.column_dimensions["B"].width = 25
        ws_items.column_dimensions["C"].width = 30
        ws_items.column_dimensions["D"].width = 10
        ws_items.column_dimensions["E"].width = 15
        ws_items.column_dimensions["F"].width = 15

        # Save to bytes
        buffer = io.BytesIO()
        wb.save(buffer)
        return buffer.getvalue()
