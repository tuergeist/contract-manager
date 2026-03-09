## Tasks

### 1. Backend: Inbox configuration model & API
- [ ] 1.1 Create `InvoiceInbox` model: tenant FK, type (imap/m365), host, port, username, encrypted password, folder, m365_mailbox, is_active, poll_interval_minutes, last_polled_at
- [ ] 1.2 Add migration for `InvoiceInbox`
- [ ] 1.3 Add `InvoiceInboxType` Strawberry type
- [ ] 1.4 Add `invoice_inboxes` query (list all for tenant)
- [ ] 1.5 Add `createInvoiceInbox` mutation (requires `settings.write`)
- [ ] 1.6 Add `updateInvoiceInbox` mutation
- [ ] 1.7 Add `deleteInvoiceInbox` mutation
- [ ] 1.8 Add `testInvoiceInboxConnection` mutation — connect via IMAP or M365 Graph API, return success/error

### 2. Backend: Incoming invoice model
- [ ] 2.1 Create `IncomingInvoice` model: tenant FK, counterparty FK (nullable), supplier_name, invoice_number, invoice_date, due_date, net_amount, vat_amount, gross_amount, currency, pdf_file, original_filename, file_size, extraction_status, email_message_id (for dedup), inbox FK, source_email_subject, source_email_date, cost_center FK (nullable)
- [ ] 2.2 Add migration for `IncomingInvoice`
- [ ] 2.3 Add unique constraint on (tenant, email_message_id, original_filename) for dedup

### 3. Backend: IMAP polling service
- [ ] 3.1 Create `InboxPollingService` with `poll_inbox(inbox: InvoiceInbox)` method
- [ ] 3.2 Implement IMAP connection: connect, select folder, search UNSEEN
- [ ] 3.3 Extract PDF attachments from email MIME parts
- [ ] 3.4 Create `IncomingInvoice` record per PDF attachment, store PDF to object storage
- [ ] 3.5 Mark processed emails (IMAP flag or move to subfolder)
- [ ] 3.6 Skip emails already imported (check email_message_id + filename)

### 4. Backend: M365 Graph API polling
- [ ] 4.1 Extend `InboxPollingService` with M365 mail read via Graph API (using tenant M365 credentials)
- [ ] 4.2 Fetch unread messages from configured mailbox/folder
- [ ] 4.3 Download PDF attachments via Graph API
- [ ] 4.4 Mark messages as read after processing

### 5. Backend: PDF metadata extraction
- [ ] 5.1 Create `IncomingInvoiceExtractionService` — extract supplier name, invoice number, date, amounts from PDF (reuse existing extraction patterns from `ImportedInvoice`)
- [ ] 5.2 Update `IncomingInvoice` status to "extracted" on success, "extraction_failed" on failure
- [ ] 5.3 Trigger extraction after inbox polling creates new records

### 6. Backend: Auto-assign counterparty
- [ ] 6.1 After extraction, attempt to match supplier_name against existing `Counterparty.name` (case-insensitive, fuzzy)
- [ ] 6.2 If IBAN extracted, match against `Counterparty.iban`
- [ ] 6.3 Link matched counterparty to `IncomingInvoice`; leave null if no match

### 7. Backend: Background polling task
- [ ] 7.1 Create Celery task `poll_invoice_inboxes` — iterate active inboxes, call polling service
- [ ] 7.2 Register periodic task (Celery Beat) with configurable interval (default 15 min)
- [ ] 7.3 Add last_polled_at tracking and skip if polled recently

### 8. Backend: GraphQL queries & mutations for incoming invoices
- [ ] 8.1 Add `IncomingInvoiceType` Strawberry type
- [ ] 8.2 Add `incomingInvoices` query with filters: status, counterparty_id, date_from, date_to, search, amount_min, amount_max, pagination
- [ ] 8.3 Add `incomingInvoice(id)` detail query
- [ ] 8.4 Add `updateIncomingInvoice` mutation (manual correction of extracted fields, counterparty assignment, confirm)
- [ ] 8.5 Add `deleteIncomingInvoice` mutation

### 9. Frontend: Inbox settings UI
- [ ] 9.1 Add "Invoice Inboxes" section to Settings page
- [ ] 9.2 Create/edit inbox form (type toggle IMAP/M365, connection fields)
- [ ] 9.3 Test connection button with status feedback
- [ ] 9.4 Delete inbox with confirmation

### 10. Frontend: Incoming invoices list page
- [ ] 10.1 Add "Incoming Invoices" entry to sidebar navigation
- [ ] 10.2 Build list view with table: supplier, invoice number, date, gross amount, status, counterparty
- [ ] 10.3 Add filter controls: status, date range, search, counterparty
- [ ] 10.4 Empty state when no incoming invoices exist

### 11. Frontend: Incoming invoice detail / edit
- [ ] 11.1 Click row to open detail view (or sheet)
- [ ] 11.2 Show PDF preview + extracted fields
- [ ] 11.3 Allow editing extracted fields (supplier, amounts, date)
- [ ] 11.4 Counterparty selector (search existing, assign)
- [ ] 11.5 Confirm button to finalize extraction

### 12. i18n
- [ ] 12.1 Add translation keys for inbox settings, incoming invoices list, detail view, statuses to `en.json` and `de.json`

### 13. Tests
- [ ] 13.1 Test IMAP polling: new email creates record, duplicate skipped, no-PDF skipped
- [ ] 13.2 Test M365 polling: same scenarios via Graph API mock
- [ ] 13.3 Test extraction service: successful extraction, failed extraction
- [ ] 13.4 Test counterparty auto-assignment: name match, IBAN match, no match
- [ ] 13.5 Test GraphQL queries: list with filters, detail, update, delete
- [ ] 13.6 Test inbox CRUD mutations
- [ ] 13.7 Test tenant isolation on all queries
