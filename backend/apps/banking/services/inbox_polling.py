"""Service for polling email inboxes for incoming invoice PDFs."""

import email
import imaplib
import logging
from email.utils import parsedate_to_datetime
from datetime import datetime

import httpx
from django.core.files.base import ContentFile

from apps.banking.models import IncomingInvoice, InvoiceInbox

logger = logging.getLogger(__name__)


class InboxPollingService:
    """Polls configured email inboxes for PDF attachments and creates IncomingInvoice records."""

    def poll_inbox(self, inbox: InvoiceInbox) -> list[IncomingInvoice]:
        if inbox.inbox_type == InvoiceInbox.InboxType.IMAP:
            return self._poll_imap(inbox)
        elif inbox.inbox_type == InvoiceInbox.InboxType.M365:
            return self._poll_m365(inbox)
        return []

    def _poll_imap(self, inbox: InvoiceInbox) -> list[IncomingInvoice]:
        created = []
        try:
            if inbox.use_ssl:
                conn = imaplib.IMAP4_SSL(inbox.host, inbox.port)
            else:
                conn = imaplib.IMAP4(inbox.host, inbox.port)

            conn.login(inbox.username, inbox.password)
            conn.select(inbox.folder)

            status, msg_ids = conn.search(None, "UNSEEN")
            if status != "OK" or not msg_ids[0]:
                conn.close()
                conn.logout()
                return created

            for msg_id in msg_ids[0].split():
                status, msg_data = conn.fetch(msg_id, "(RFC822)")
                if status != "OK":
                    continue

                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email)

                message_id = msg.get("Message-ID", "").strip()
                subject = msg.get("Subject", "")
                date_header = msg.get("Date", "")
                email_date = None
                if date_header:
                    try:
                        email_date = parsedate_to_datetime(date_header)
                    except Exception:
                        pass

                pdfs_found = False
                for part in msg.walk():
                    content_type = part.get_content_type()
                    filename = part.get_filename()
                    if not filename:
                        continue
                    if content_type != "application/pdf" and not filename.lower().endswith(".pdf"):
                        continue

                    if message_id and IncomingInvoice.objects.filter(
                        tenant=inbox.tenant,
                        email_message_id=message_id,
                        original_filename=filename,
                    ).exists():
                        pdfs_found = True
                        continue

                    pdf_data = part.get_payload(decode=True)
                    if not pdf_data:
                        continue

                    invoice = IncomingInvoice(
                        tenant=inbox.tenant,
                        inbox=inbox,
                        original_filename=filename,
                        file_size=len(pdf_data),
                        email_message_id=message_id,
                        source_email_subject=subject[:500],
                        source_email_date=email_date,
                        extraction_status=IncomingInvoice.ExtractionStatus.PENDING,
                    )
                    invoice.pdf_file.save(filename, ContentFile(pdf_data), save=False)
                    invoice.save()
                    created.append(invoice)
                    pdfs_found = True

                if pdfs_found:
                    conn.store(msg_id, "+FLAGS", "\\Seen")

            conn.close()
            conn.logout()
        except Exception as e:
            logger.error("IMAP polling error for inbox %s: %s", inbox.id, e)

        return created

    def _poll_m365(self, inbox: InvoiceInbox) -> list[IncomingInvoice]:
        from apps.core.m365 import get_m365_token, GRAPH_BASE

        created = []
        try:
            token = get_m365_token(inbox.tenant)
            mailbox = inbox.m365_mailbox
            headers = {"Authorization": f"Bearer {token}"}

            url = (
                f"{GRAPH_BASE}/users/{mailbox}/messages"
                f"?$filter=isRead eq false&$select=id,subject,receivedDateTime,internetMessageId"
                f"&$top=50&$orderby=receivedDateTime desc"
            )
            resp = httpx.get(url, headers=headers, timeout=30)
            if resp.status_code != 200:
                logger.error("M365 fetch messages failed: %s %s", resp.status_code, resp.text[:200])
                return created

            messages = resp.json().get("value", [])

            for msg in messages:
                msg_id = msg.get("internetMessageId", "")
                graph_msg_id = msg["id"]
                subject = msg.get("subject", "")
                received = msg.get("receivedDateTime")
                email_date = None
                if received:
                    try:
                        email_date = datetime.fromisoformat(received.replace("Z", "+00:00"))
                    except Exception:
                        pass

                att_url = f"{GRAPH_BASE}/users/{mailbox}/messages/{graph_msg_id}/attachments"
                att_resp = httpx.get(att_url, headers=headers, timeout=30)
                if att_resp.status_code != 200:
                    continue

                attachments = att_resp.json().get("value", [])
                pdfs_found = False

                for att in attachments:
                    import base64
                    filename = att.get("name", "")
                    content_type = att.get("contentType", "")
                    if not filename.lower().endswith(".pdf") and content_type != "application/pdf":
                        continue

                    if msg_id and IncomingInvoice.objects.filter(
                        tenant=inbox.tenant,
                        email_message_id=msg_id,
                        original_filename=filename,
                    ).exists():
                        pdfs_found = True
                        continue

                    content_bytes = att.get("contentBytes")
                    if not content_bytes:
                        continue
                    pdf_data = base64.b64decode(content_bytes)

                    invoice = IncomingInvoice(
                        tenant=inbox.tenant,
                        inbox=inbox,
                        original_filename=filename,
                        file_size=len(pdf_data),
                        email_message_id=msg_id,
                        source_email_subject=subject[:500],
                        source_email_date=email_date,
                        extraction_status=IncomingInvoice.ExtractionStatus.PENDING,
                    )
                    invoice.pdf_file.save(filename, ContentFile(pdf_data), save=False)
                    invoice.save()
                    created.append(invoice)
                    pdfs_found = True

                if pdfs_found:
                    patch_url = f"{GRAPH_BASE}/users/{mailbox}/messages/{graph_msg_id}"
                    httpx.patch(
                        patch_url,
                        headers={**headers, "Content-Type": "application/json"},
                        json={"isRead": True},
                        timeout=15,
                    )
        except Exception as e:
            logger.error("M365 polling error for inbox %s: %s", inbox.id, e)

        return created

    def test_connection(self, inbox: InvoiceInbox) -> tuple[bool, str]:
        if inbox.inbox_type == InvoiceInbox.InboxType.IMAP:
            return self._test_imap(inbox)
        elif inbox.inbox_type == InvoiceInbox.InboxType.M365:
            return self._test_m365(inbox)
        return False, "Unknown inbox type"

    def _test_imap(self, inbox: InvoiceInbox) -> tuple[bool, str]:
        try:
            if inbox.use_ssl:
                conn = imaplib.IMAP4_SSL(inbox.host, inbox.port)
            else:
                conn = imaplib.IMAP4(inbox.host, inbox.port)
            conn.login(inbox.username, inbox.password)
            status, _ = conn.select(inbox.folder)
            conn.close()
            conn.logout()
            if status == "OK":
                return True, "Connection successful"
            return False, f"Could not select folder: {inbox.folder}"
        except Exception as e:
            return False, str(e)

    def _test_m365(self, inbox: InvoiceInbox) -> tuple[bool, str]:
        try:
            from apps.core.m365 import get_m365_token, GRAPH_BASE
            token = get_m365_token(inbox.tenant)
            resp = httpx.get(
                f"{GRAPH_BASE}/users/{inbox.m365_mailbox}/mailFolders/inbox",
                headers={"Authorization": f"Bearer {token}"},
                timeout=15,
            )
            if resp.status_code == 200:
                return True, "Connection successful"
            return False, f"M365 API error: {resp.status_code}"
        except Exception as e:
            return False, str(e)
