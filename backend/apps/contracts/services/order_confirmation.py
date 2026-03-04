"""Order confirmation service — rendering, PDF generation, and email sending."""
import logging
from datetime import date
from decimal import Decimal
from typing import Literal

from django.template.loader import render_to_string
from django.utils import timezone

logger = logging.getLogger(__name__)

AB_LABELS = {
    "de": {
        "title": "Auftragsbestätigung",
        "ab_number": "AB-Nr.",
        "date_label": "Datum",
        "contract": "Vertrag",
        "contract_start": "Vertragsbeginn",
        "contract_end": "Vertragsende",
        "description": "Beschreibung",
        "quantity": "Menge",
        "unit_price": "Einzelpreis",
        "per_month": "/Monat",
        "amount": "Betrag",
        "net_total": "Nettobetrag",
        "tax": "MwSt.",
        "total": "Gesamtbetrag",
        "pos": "Pos.",
        "po_number": "Bestellnummer",
        "order_confirmation": "Auftragsbestätigung",
        "customer_vat_id": "USt-IdNr.",
        "vat_id": "USt-IdNr.",
        "tax_number": "Steuernummer",
        "register": "Handelsregister",
        "managing_directors": "Geschäftsführer",
        "share_capital": "Stammkapital",
        "bank_details": "Bankverbindung",
        "phone": "Telefon",
    },
    "en": {
        "title": "Order Confirmation",
        "ab_number": "Conf. No.",
        "date_label": "Date",
        "contract": "Contract",
        "contract_start": "Contract Start",
        "contract_end": "Contract End",
        "description": "Description",
        "quantity": "Qty",
        "unit_price": "Unit Price",
        "per_month": "/mo.",
        "amount": "Amount",
        "net_total": "Net Total",
        "tax": "VAT",
        "total": "Total",
        "pos": "Pos.",
        "po_number": "PO Number",
        "order_confirmation": "Order Confirmation",
        "customer_vat_id": "VAT ID",
        "vat_id": "VAT ID",
        "tax_number": "Tax Number",
        "register": "Commercial Register",
        "managing_directors": "Managing Directors",
        "share_capital": "Share Capital",
        "bank_details": "Bank Details",
        "phone": "Phone",
    },
}

AB_EMAIL_TEMPLATES = {
    "de": {
        "subject": "Auftragsbestätigung {order_confirmation_number}",
        "body": """\
<p>Sehr geehrte Damen und Herren,</p>
<p>anbei erhalten Sie unsere Auftragsbestätigung <strong>{order_confirmation_number}</strong> \
zum Vertrag {contract_reference}.</p>
{personal_message_html}\
<p>Die Auftragsbestätigung finden Sie als PDF im Anhang.</p>
<p>Mit freundlichen Grüßen<br>{company_name}</p>""",
    },
    "en": {
        "subject": "Order Confirmation {order_confirmation_number}",
        "body": """\
<p>Dear Sir or Madam,</p>
<p>Please find attached our order confirmation <strong>{order_confirmation_number}</strong> \
for contract {contract_reference}.</p>
{personal_message_html}\
<p>The order confirmation is attached as a PDF.</p>
<p>Best regards,<br>{company_name}</p>""",
    },
}


class OrderConfirmationService:
    """Service for rendering, generating PDFs, and sending order confirmations."""

    def __init__(self, tenant):
        self.tenant = tenant

    def _get_template_context(self) -> dict:
        """Load template settings and legal data (reuses invoice template settings)."""
        from apps.invoices.models import CompanyLegalData, InvoiceTemplate

        try:
            legal_data_obj = self.tenant.legal_data
            company = legal_data_obj.to_snapshot()
        except CompanyLegalData.DoesNotExist:
            company = {
                "company_name": self.tenant.name,
                "street": "", "zip_code": "", "city": "", "country": "",
                "tax_number": "", "vat_id": "",
                "commercial_register_court": "", "commercial_register_number": "",
                "managing_directors": [], "bank_name": "", "iban": "", "bic": "",
                "phone": "", "email": "", "website": "", "share_capital": "",
                "default_tax_rate": "19.00",
            }

        accent_color = "#2563eb"
        header_text = ""
        footer_text = ""
        logo_url = ""
        try:
            template = InvoiceTemplate.objects.get(tenant=self.tenant)
            accent_color = template.accent_color or "#2563eb"
            header_text = template.header_text or ""
            footer_text = template.footer_text or ""
            if template.logo and template.logo.name:
                import base64
                import mimetypes
                try:
                    mime_type = mimetypes.guess_type(template.logo.name)[0] or "image/png"
                    logo_data = template.logo.read()
                    logo_url = f"data:{mime_type};base64,{base64.b64encode(logo_data).decode()}"
                except Exception:
                    logo_url = ""
        except InvoiceTemplate.DoesNotExist:
            pass

        tax_rate = Decimal(company.get("default_tax_rate", "19.00"))

        return {
            "company": company,
            "accent_color": accent_color,
            "header_text": header_text,
            "footer_text": footer_text,
            "logo_url": logo_url,
            "tax_rate": tax_rate,
        }

    def _build_line_items(self, contract) -> list[dict]:
        """Build line item dicts from contract items."""
        items = []
        for item in contract.items.select_related("product").order_by("id"):
            product_name = ""
            if item.product:
                product_name = item.product.name
            amount = item.quantity * item.unit_price
            items.append({
                "product_name": product_name,
                "description": item.description or "",
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "amount": amount,
                "billing_interval": item.price_period if item.price_period != "monthly" else "",
            })
        return items

    def _build_totals(self, line_items: list[dict], tax_rate: Decimal) -> dict:
        """Calculate net, tax, gross totals."""
        net = sum(item["amount"] for item in line_items)
        tax_amount = (net * tax_rate / Decimal("100")).quantize(Decimal("0.01"))
        gross = net + tax_amount
        return {
            "net": net,
            "tax_rate": tax_rate,
            "tax_amount": tax_amount if tax_amount > 0 else None,
            "gross": gross,
        }

    def build_template_context(
        self,
        contract,
        ab_number: str = "",
        personal_message: str = "",
        include_message_in_pdf: bool = True,
        language: str = "de",
    ) -> dict:
        """Build the full template context for rendering the AB HTML."""
        labels = AB_LABELS.get(language, AB_LABELS["de"])
        template_ctx = self._get_template_context()
        line_items = self._build_line_items(contract)
        totals = self._build_totals(line_items, template_ctx["tax_rate"])
        currency_symbol = self.tenant.currency_symbol

        customer = contract.customer
        customer_address = customer.address if customer else {}
        customer_vat_id = customer.vat_id if customer else ""

        return {
            "labels": labels,
            "language": language,
            "currency_symbol": currency_symbol,
            "ab_number": ab_number,
            "confirmation_date": date.today(),
            "contract": contract,
            "customer_address": customer_address,
            "customer_vat_id": customer_vat_id,
            "line_items": line_items,
            "totals": totals,
            "personal_message": personal_message,
            "include_message_in_pdf": include_message_in_pdf,
            **template_ctx,
        }

    def render_html(
        self,
        contract,
        ab_number: str = "",
        personal_message: str = "",
        include_message_in_pdf: bool = True,
        language: str = "de",
    ) -> str:
        """Render the order confirmation as HTML string."""
        ctx = self.build_template_context(
            contract, ab_number, personal_message, include_message_in_pdf, language
        )
        return render_to_string("contracts/order_confirmation.html", ctx)

    def generate_pdf(
        self,
        contract,
        ab_number: str = "",
        personal_message: str = "",
        include_message_in_pdf: bool = True,
        language: str = "de",
    ) -> bytes:
        """Generate the order confirmation PDF."""
        from weasyprint import HTML

        html = self.render_html(
            contract, ab_number, personal_message, include_message_in_pdf, language
        )
        pdf_document = HTML(string=html).render()
        return pdf_document.write_pdf()

    def create_order_confirmation(
        self,
        contract,
        user,
        personal_message: str = "",
        include_message_in_pdf: bool = True,
        include_message_in_email: bool = True,
        additional_emails: list[str] | None = None,
    ):
        """Create an OrderConfirmation record with generated number and PDF."""
        from django.core.files.base import ContentFile

        from apps.contracts.order_confirmation_models import OrderConfirmation
        from apps.contracts.order_confirmation_numbering import OrderConfirmationNumberService

        customer = contract.customer
        language = getattr(customer, "invoice_language", "") or "de"
        if language not in AB_LABELS:
            language = "de"

        # Generate number
        numbering = OrderConfirmationNumberService(self.tenant)
        ab_number = numbering.get_next_number(date.today())

        # Create record
        ab = OrderConfirmation.objects.create(
            tenant=self.tenant,
            contract=contract,
            created_by=user,
            order_confirmation_number=ab_number,
            personal_message=personal_message,
            include_message_in_pdf=include_message_in_pdf,
            include_message_in_email=include_message_in_email,
            additional_emails=additional_emails or [],
            language=language,
            status=OrderConfirmation.Status.DRAFT,
        )

        # Generate and store PDF
        pdf_bytes = self.generate_pdf(
            contract, ab_number, personal_message, include_message_in_pdf, language
        )
        ab.pdf_file.save(f"{ab_number}.pdf", ContentFile(pdf_bytes), save=True)

        return ab

    def get_email_template(self, language: str) -> dict:
        """Get AB email template, preferring tenant custom templates."""
        if language not in AB_EMAIL_TEMPLATES:
            language = "de"

        custom = (self.tenant.settings or {}).get("ab_email_templates", {}).get(language, {})
        if custom.get("subject") and custom.get("body"):
            return {"subject": custom["subject"], "body": custom["body"]}

        return AB_EMAIL_TEMPLATES[language]

    def send_order_confirmation(self, ab) -> bool:
        """Send the order confirmation email via M365 Graph API."""
        from apps.core.m365 import M365Error, send_mail

        contract = ab.contract
        customer = contract.customer

        if not customer:
            logger.error("OrderConfirmation %s: contract has no customer", ab.id)
            return False

        recipients = list(customer.billing_emails or [])
        recipients.extend(ab.additional_emails or [])
        recipients = list(set(recipients))  # deduplicate

        if not recipients:
            logger.error("OrderConfirmation %s: no recipients", ab.id)
            return False

        if not ab.pdf_file:
            logger.error("OrderConfirmation %s: no PDF file", ab.id)
            return False

        template = self.get_email_template(ab.language)

        company_data = self._get_template_context().get("company", {})
        company_name = company_data.get("company_name", "")

        personal_message_html = ""
        if ab.include_message_in_email and ab.personal_message:
            personal_message_html = f"<p>{ab.personal_message}</p>\n"

        format_kwargs = {
            "order_confirmation_number": ab.order_confirmation_number,
            "customer_name": customer.name,
            "contract_reference": contract.name or str(contract.id),
            "personal_message": ab.personal_message or "",
            "personal_message_html": personal_message_html,
            "company_name": company_name,
        }

        try:
            subject = template["subject"].format(**format_kwargs)
            body_html = template["body"].format(**format_kwargs)
        except (KeyError, ValueError) as e:
            logger.warning("AB email template rendering failed for %s, using default: %s", ab.id, e)
            fallback = AB_EMAIL_TEMPLATES.get(ab.language, AB_EMAIL_TEMPLATES["de"])
            subject = fallback["subject"].format(**format_kwargs)
            body_html = fallback["body"].format(**format_kwargs)

        pdf_bytes = ab.pdf_file.read()
        attachments = [
            {
                "name": f"{ab.order_confirmation_number}.pdf",
                "content_type": "application/pdf",
                "content_bytes": pdf_bytes,
            }
        ]

        try:
            message_id = send_mail(
                self.tenant,
                to=recipients,
                subject=subject,
                body_html=body_html,
                attachments=attachments,
            )
            ab.sent_at = timezone.now()
            ab.sent_to = recipients
            ab.email_message_id = message_id or ""
            ab.status = ab.Status.SENT
            ab.save(update_fields=["sent_at", "sent_to", "email_message_id", "status"])

            logger.info("AB email sent for %s to %s", ab.id, recipients)
            return True
        except M365Error as e:
            logger.error("Failed to send AB email for %s: %s", ab.id, e)
            return False
