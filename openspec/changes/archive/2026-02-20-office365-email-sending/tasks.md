## 1. Dependencies & Model Changes

- [x] 1.1 Add `msal` and `requests` to backend dependencies (Dockerfile, requirements)
- [x] 1.2 Add `email_sent_at` (DateTimeField, null), `email_sent_to` (JSONField, default=list), `email_message_id` (CharField, blank) fields to InvoiceRecord model
- [x] 1.3 Create and run migration for InvoiceRecord email tracking fields

## 2. M365 Connection Backend

- [x] 2.1 Create `backend/apps/integrations/m365.py` — helper module with `get_m365_token(tenant)` using `ConfidentialClientApplication`, `list_mailboxes(tenant)` via Graph API, `send_mail(tenant, to, subject, body_html, attachments)` via Graph API sendMail endpoint
- [x] 2.2 Add GraphQL types: `M365SettingsType` (isConfigured, senderMailbox, clientId masked), `M365MailboxType` (email, displayName)
- [x] 2.3 Add query `m365Settings` — returns current M365 config status (no secret exposed)
- [x] 2.4 Add mutation `saveM365Settings(tenantId, clientId, clientSecret, azureTenantId)` — stores credentials in Tenant.settings["m365"], requires settings.write
- [x] 2.5 Add mutation `testM365Connection` — acquires token, returns success/error
- [x] 2.6 Add mutation `discoverM365Mailboxes` — lists available mailboxes from Graph API
- [x] 2.7 Add mutation `selectM365Mailbox(mailbox)` — stores sender_mailbox in config

## 3. Email Sending Backend

- [x] 3.1 Create email templates — inline German/English subject+body templates using invoice_number, period, amount, company name
- [x] 3.2 Create Celery task `send_invoice_email_task(record_id)` — fetch record+customer+tenant, acquire token, compose email with PDF attachment, send via Graph API, update email tracking fields
- [x] 3.3 Add mutation `sendInvoiceEmail(invoiceRecordId)` — validate preconditions (finalized, has PDF, has billing_emails, M365 configured), dispatch Celery task, requires invoices.write
- [x] 3.4 Expose `emailSentAt`, `emailSentTo`, `emailMessageId` on InvoiceRecordType

## 4. Backend Tests

- [x] 4.1 Test saveM365Settings stores credentials correctly
- [x] 4.2 Test M365 settings query returns masked data
- [x] 4.3 Test sendInvoiceEmail validates preconditions (no PDF, no billing emails, not finalized, M365 not configured)
- [x] 4.4 Test send_invoice_email_task composes correct email and updates tracking fields (mock Graph API)

## 5. Frontend — Settings Page

- [x] 5.1 Add M365 configuration section to Settings page — fields for Azure Tenant ID, Client ID, Client Secret, with Save button
- [x] 5.2 Add "Test Connection" button that calls testM365Connection mutation and shows success/error
- [x] 5.3 Add mailbox discovery — "Discover Mailboxes" button that calls discoverM365Mailboxes, shows list in a Select dropdown
- [x] 5.4 Add sender mailbox selector — Select from discovered mailboxes, calls selectM365Mailbox on change
- [x] 5.5 Show current M365 status (configured/not configured, selected sender mailbox) on initial load via m365Settings query

## 6. Frontend — Invoice Send Action

- [x] 6.1 Add `emailSentAt`, `emailSentTo` to invoice list GraphQL queries (ImportedInvoiceList, ContractDetail invoices tab)
- [x] 6.2 Add `SEND_INVOICE_EMAIL` mutation and `M365_SETTINGS` query to ImportedInvoiceList
- [x] 6.3 Add Send button (Mail icon) on finalized generated invoices with emailSentAt=null, hidden when M365 not configured
- [x] 6.4 Add sent indicator badge (date + envelope icon) for invoices with emailSentAt set
- [x] 6.5 Handle send action — confirm dialog showing recipients, call mutation, show success/error toast

## 7. Translations & Verification

- [x] 7.1 Add translation keys for M365 settings section, send button, sent badge, error messages (en + de)
- [x] 7.2 Run `make test-back` — all tests pass
- [x] 7.3 Run `npx tsc --noEmit` — no type errors
