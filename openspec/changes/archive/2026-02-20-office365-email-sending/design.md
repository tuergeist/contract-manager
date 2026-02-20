## Context

The system generates ZUGFeRD PDF invoices and stores them in S3 (`InvoiceRecord.pdf_file`). Customers have `billing_emails` (JSONField list). `InvoiceRecord` already has a `SENT` status. Currently there is no email sending capability — users download PDFs and email them manually.

A reference M365 integration exists in `~/git/vsx-zeitabrechnung/scripts/read_shared_mailbox.py` using `msal` + Microsoft Graph API with device flow auth. For server-side use in Docker/Celery, we need client credentials (application permissions) instead.

Tenant configuration lives in `Tenant.settings` (JSONField) for generic settings, with dedicated JSONFields for HubSpot and Clockodo integrations.

## Goals / Non-Goals

**Goals:**
- Configure M365 connection per tenant (Azure AD client credentials)
- Discover and select a shared mailbox to send from
- Send finalized invoices to customer billing emails via Graph API
- Track send status (sent_at, sent_to, message_id) on InvoiceRecord
- Async sending via Celery task

**Non-Goals:**
- Reading incoming mail / inbox sync
- Order confirmation sending (future — the plumbing built here will support it)
- Email template editor (use a hardcoded German/English template for now)
- Bulk sending of all unsent invoices (send one at a time initially)
- CC/BCC configuration (keep simple, add later)

## Decisions

### 1. Client Credentials Flow (Application Permissions)

**Choice:** Use `msal.ConfidentialClientApplication` with client_secret, requesting `https://graph.microsoft.com/.default` scope.

**Why not delegated (device flow)?** The backend runs in Docker without interactive login. Client credentials grant lets Celery tasks send emails without user sessions.

**Requires:** Azure AD app registration with `Mail.Send` application permission + admin consent. Optionally restrict to specific mailboxes via Exchange application access policy.

### 2. Store M365 Config in Tenant.settings

**Choice:** Store credentials in `Tenant.settings["m365"]`:
```json
{
  "m365": {
    "tenant_id": "...",
    "client_id": "...",
    "client_secret": "...",
    "sender_mailbox": "invoices@company.com"
  }
}
```

**Why not a dedicated model/JSONField?** The existing pattern (HubSpot in `hubspot_config`, Clockodo in `time_tracking_config`) uses dedicated JSONFields, but `Tenant.settings` is the newer pattern used for activation checklist and help video links. M365 config is small and fits naturally here. Avoids a migration.

### 3. Send Tracking on InvoiceRecord

**Choice:** Add fields to `InvoiceRecord`:
- `email_sent_at: DateTimeField(null=True)` — when the email was sent
- `email_sent_to: JSONField(default=list)` — list of recipient addresses
- `email_message_id: CharField(blank=True)` — Graph API message ID for reference

**Why not a separate EmailLog model?** Overkill for v1. One invoice = one send event. If we later need retry history or multi-send, we can add a log model then.

The existing `Status.SENT` can be set after successful send, but status transitions should remain manual (user decides when to mark as sent vs. just having the email go out).

### 4. Celery Task for Async Sending

**Choice:** `send_invoice_email_task(record_id)` in `apps/invoices/tasks.py`.

Flow:
1. Fetch InvoiceRecord + Customer + Tenant
2. Acquire M365 token via `ConfidentialClientApplication`
3. Build email: subject from invoice number, body from template, attach PDF
4. POST to `/users/{sender_mailbox}/sendMail` via Graph API
5. Update `email_sent_at`, `email_sent_to`, `email_message_id`

**Error handling:** Log errors, don't retry automatically (avoid duplicate sends). Surface errors in the UI.

### 5. Email Composition

**Template approach:** Simple inline templates (German/English based on `Customer.invoice_language`):
- Subject: `"Rechnung {invoice_number}"` / `"Invoice {invoice_number}"`
- Body: Brief text referencing invoice number, period, amount. Attachment is the ZUGFeRD PDF.

Use Graph API `sendMail` endpoint which accepts base64-encoded attachments directly — no need for draft-then-send.

### 6. Mailbox Discovery

**Choice:** When configuring M365 in settings, provide a "Test Connection & List Mailboxes" button.

Uses Graph API endpoints:
- `/users?$filter=startswith(mail, ...)` or `/users?$select=mail,displayName` to list available mailboxes
- Filtered to show shared mailboxes the app has access to

The selected mailbox is stored as `sender_mailbox` in the config.

## Risks / Trade-offs

**[Client secret storage in DB]** → Secrets are stored in `Tenant.settings` alongside other config. Same pattern as HubSpot API key. For production hardening, could later move to environment variables or a secrets manager, but per-tenant config requires DB storage.

**[Token caching]** → MSAL handles token caching internally per `ConfidentialClientApplication` instance. For Celery workers, each task creates a fresh instance (tokens are short-lived, and client_credentials grants are fast). No persistent token cache needed for app-only auth.

**[Rate limits]** → Microsoft Graph has throttling limits. Single invoice sends are well within limits. If bulk sending is added later, implement backoff.

**[No retry on send failure]** → Intentional to avoid double-sending. Failed sends surface as errors in UI. User can retry manually.

**[Attachment size]** → Graph API `sendMail` supports up to 4MB inline attachments (base64). ZUGFeRD PDFs are typically 50-200KB. For larger attachments, would need upload session — not needed for invoices.
