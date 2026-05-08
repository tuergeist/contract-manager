"""Celery tasks for offer email sending."""
import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


EMAIL_TEMPLATES = {
    "de": {
        "subject": "Angebot {offer_number}",
        "body": """\
<p>Sehr geehrte Damen und Herren,</p>
<p>anbei erhalten Sie unser Angebot <strong>{offer_number}</strong> \
über {total_gross} {currency} für den Zeitraum {period_start} – {period_end}.</p>
<p>Das Angebot ist gültig bis {valid_until}.</p>
<p>Das Angebot finden Sie als PDF im Anhang.</p>
<p>Mit freundlichen Grüßen<br>{company_name}</p>""",
    },
    "en": {
        "subject": "Offer {offer_number}",
        "body": """\
<p>Dear Sir or Madam,</p>
<p>Please find attached our offer <strong>{offer_number}</strong> \
for {total_gross} {currency} covering the period {period_start} – {period_end}.</p>
<p>This offer is valid until {valid_until}.</p>
<p>The offer is attached as a PDF.</p>
<p>Best regards,<br>{company_name}</p>""",
    },
}


@shared_task(bind=True, acks_late=True)
def send_offer_email_task(
    self, offer_id: int, recipients: list[str], user_id: int | None = None
) -> bool:
    """Send an offer email via M365 Graph API.

    No automatic retry to avoid duplicate sends.
    """
    from apps.core.m365 import M365Error, send_mail
    from apps.offers.models import OfferRecord

    try:
        record = OfferRecord.objects.select_related(
            "customer", "tenant"
        ).get(id=offer_id)
    except OfferRecord.DoesNotExist:
        logger.error("OfferRecord %s not found for email sending", offer_id)
        return False

    if not record.pdf_file:
        logger.error("OfferRecord %s has no PDF file", offer_id)
        return False

    if not recipients:
        logger.error("No recipients for OfferRecord %s", offer_id)
        return False

    # Determine language (explicit field → derive from country → fallback)
    lang = "en"
    if record.customer:
        lang = record.customer.get_effective_invoice_language(default="en")
    if lang not in EMAIL_TEMPLATES:
        lang = "en"

    template = EMAIL_TEMPLATES[lang]
    company_data = record.company_data_snapshot or {}
    company_name = company_data.get("company_name", "")
    currency = record.tenant.currency if record.tenant else "EUR"

    format_kwargs = dict(
        offer_number=record.offer_number,
        total_gross=f"{record.total_gross:,.2f}",
        currency=currency,
        period_start=record.period_start.strftime("%d.%m.%Y"),
        period_end=record.period_end.strftime("%d.%m.%Y"),
        valid_until=record.valid_until.strftime("%d.%m.%Y") if record.valid_until else "—",
        company_name=company_name,
    )

    try:
        subject = template["subject"].format(**format_kwargs)
        body_html = template["body"].format(**format_kwargs)
    except (KeyError, ValueError) as e:
        logger.warning(
            "Offer email template rendering failed for record %s, falling back: %s",
            offer_id, e,
        )
        fallback = EMAIL_TEMPLATES["en"]
        subject = fallback["subject"].format(**format_kwargs)
        body_html = fallback["body"].format(**format_kwargs)

    # Read PDF attachment
    pdf_bytes = record.pdf_file.read()
    attachments = [
        {
            "name": f"{record.offer_number}.pdf",
            "content_type": "application/pdf",
            "content_bytes": pdf_bytes,
        }
    ]

    from apps.core.m365 import get_document_bcc
    bcc = get_document_bcc(record.tenant, "offer")

    try:
        message_id = send_mail(
            record.tenant,
            to=recipients,
            subject=subject,
            body_html=body_html,
            attachments=attachments,
            bcc=bcc or None,
        )
        record.email_sent_at = timezone.now()
        record.email_sent_to = recipients
        record.email_message_id = message_id or ""
        record.status = OfferRecord.Status.SENT
        record.save(update_fields=[
            "email_sent_at", "email_sent_to", "email_message_id", "status",
        ])

        logger.info("Offer email sent for record %s to %s", offer_id, recipients)
        return True
    except M365Error as e:
        logger.error("Failed to send offer email for record %s: %s", offer_id, e)
        return False
