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

    # Pre-flight: the offer must still be a draft when we attempt to send.
    # We re-check inside the post-send transaction with select_for_update
    # to guard against a concurrent Finalize. See
    # openspec/specs/offer-finalize/spec.md::Send failure does not lock.
    if record.status != OfferRecord.Status.DRAFT:
        logger.warning(
            "Skipping send for OfferRecord %s: status=%s is already locked",
            offer_id, record.status,
        )
        return False

    try:
        message_id = send_mail(
            record.tenant,
            to=recipients,
            subject=subject,
            body_html=body_html,
            attachments=attachments,
            bcc=bcc or None,
        )
    except M365Error as e:
        # Send failed — leave the offer fully editable so the user can retry.
        logger.error("Failed to send offer email for record %s: %s", offer_id, e)
        return False

    # Send succeeded. Persist email metadata + transition draft → sent
    # under a row-level lock so a concurrent Finalize cannot overwrite us.
    from django.db import transaction
    from apps.offers.services import OfferLockedError, OfferService

    try:
        with transaction.atomic():
            locked = (
                # of=("self",) — contract FK is nullable so select_related
                # produces a LEFT OUTER JOIN that Postgres refuses to lock.
                OfferRecord.objects.select_for_update(of=("self",))
                .select_related("contract", "tenant")
                .get(id=record.id)
            )
            if locked.status != OfferRecord.Status.DRAFT:
                # Another path won the race (Finalize). Email already went
                # out — log loudly but do not overwrite the lock.
                logger.error(
                    "Concurrent lock detected on OfferRecord %s: status=%s "
                    "but email was already dispatched. Email metadata NOT "
                    "persisted to avoid corrupting the locked state.",
                    offer_id, locked.status,
                )
                return False

            locked.email_sent_at = timezone.now()
            locked.email_sent_to = recipients
            locked.email_message_id = message_id or ""
            locked.status = OfferRecord.Status.SENT
            locked.save(update_fields=[
                "email_sent_at", "email_sent_to", "email_message_id",
                "status", "updated_at",
            ])

            # Copy the PDF onto the contract as an attachment. Idempotent
            # if the offer was already attached by a previous run.
            try:
                service = OfferService(locked.tenant)
                service.attach_pdf_to_contract(locked)
            except OfferLockedError:
                # Should not happen — we hold the lock. Log defensively.
                logger.exception(
                    "Unexpected OfferLockedError during attach for %s",
                    offer_id,
                )

        logger.info("Offer email sent for record %s to %s", offer_id, recipients)
        return True
    except Exception:
        # Email already went out; persisting metadata failed. Log + return
        # success so we do not double-send on retry. The offer stays in
        # draft until manual intervention.
        logger.exception(
            "Email sent but persisting status failed for OfferRecord %s",
            offer_id,
        )
        return False
