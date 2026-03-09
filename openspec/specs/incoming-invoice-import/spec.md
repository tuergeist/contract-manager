## ADDED Requirements

### Requirement: Configure invoice inbox per tenant
The system SHALL allow users with `settings.write` permission to configure one or more invoice inboxes. Each inbox is either an IMAP connection or an M365 mailbox. Credentials are stored encrypted in tenant settings.

#### Scenario: Configure IMAP inbox
- **WHEN** user provides IMAP host, port, username, password, and folder name (e.g., "INBOX")
- **THEN** the system stores the inbox configuration and it appears in the inbox list

#### Scenario: Configure M365 inbox
- **WHEN** user provides an M365 mailbox address (using the tenant's existing M365 credentials from `m365-connection`)
- **THEN** the system stores the inbox configuration using the M365 Graph API for mail access

#### Scenario: Test inbox connection
- **WHEN** user clicks "Test Connection" on a configured inbox
- **THEN** the system connects to the mailbox and reports success or the specific error

#### Scenario: Multiple inboxes
- **WHEN** a tenant configures two inboxes (one IMAP, one M365)
- **THEN** both are polled independently on each sync cycle

### Requirement: Periodically fetch invoices from inbox
The system SHALL periodically poll configured inboxes for new emails with PDF attachments. Each PDF attachment is treated as a potential incoming invoice.

#### Scenario: New email with PDF attachment
- **WHEN** a new email arrives with a PDF attachment in a configured inbox folder
- **THEN** the system downloads the PDF, creates an `IncomingInvoice` record, and marks the email as processed (flag or move to subfolder)

#### Scenario: Email with multiple PDF attachments
- **WHEN** an email has 3 PDF attachments
- **THEN** the system creates 3 separate `IncomingInvoice` records, each linked to its respective PDF

#### Scenario: Email without PDF attachments
- **WHEN** a new email has no PDF attachments (e.g., only text or images)
- **THEN** the system skips the email and does not create any invoice record

#### Scenario: Duplicate email detection
- **WHEN** the same email is encountered again (same Message-ID)
- **THEN** the system skips it to avoid duplicate imports

#### Scenario: Polling frequency
- **WHEN** a tenant has active inbox configurations
- **THEN** the system polls every 15 minutes (configurable) via background task

### Requirement: Extract metadata from incoming invoice PDFs
The system SHALL extract key fields from incoming invoice PDFs: supplier name, invoice number, invoice date, due date, net amount, VAT amount, gross amount, and currency.

#### Scenario: Successful extraction
- **WHEN** a PDF is imported and extraction succeeds
- **THEN** the invoice record is updated with extracted fields and status changes to "extracted"

#### Scenario: Extraction fails
- **WHEN** a PDF cannot be parsed (e.g., scanned image without OCR, corrupt file)
- **THEN** the status is set to "extraction_failed" and the PDF is still stored for manual review

#### Scenario: Manual correction
- **WHEN** user reviews an extracted invoice and corrects the supplier name or amount
- **THEN** the system saves the corrected values and marks the invoice as "confirmed"

### Requirement: Incoming invoice stored as receipt even without matching transaction
The system SHALL create and persist incoming invoice records regardless of whether a matching bank transaction exists. The invoice serves as a receipt/Beleg.

#### Scenario: Invoice with no matching transaction
- **WHEN** an incoming invoice for €500 from "Hetzner" is imported but no bank transaction matches
- **THEN** the invoice is stored with status "unmatched" and appears in the incoming invoice list

#### Scenario: Invoice matched to transaction later
- **WHEN** a bank transaction for €500 to counterparty "Hetzner" is imported after the invoice
- **THEN** the system can suggest matching (using existing `banking-invoice-matching` logic, extended for incoming invoices)

### Requirement: Auto-assign incoming invoices to counterparties
The system SHALL attempt to automatically assign incoming invoices to existing counterparties based on supplier name or IBAN matching.

#### Scenario: Supplier name matches counterparty
- **WHEN** an incoming invoice has supplier name "Hetzner Online GmbH" and a counterparty "Hetzner Online GmbH" exists
- **THEN** the system automatically links the invoice to that counterparty

#### Scenario: No counterparty match
- **WHEN** an incoming invoice has a supplier name that doesn't match any counterparty
- **THEN** the invoice remains unlinked and user can manually assign or create a new counterparty

#### Scenario: Manual counterparty assignment
- **WHEN** user selects a counterparty for an unlinked incoming invoice
- **THEN** the system links the invoice to the selected counterparty

### Requirement: List and filter incoming invoices
The system SHALL provide a list view of all incoming invoices with filtering by status, counterparty, date range, and amount range.

#### Scenario: Filter by status
- **WHEN** user filters incoming invoices by status "unmatched"
- **THEN** only invoices without a linked bank transaction are shown

#### Scenario: Search by supplier or invoice number
- **WHEN** user searches for "Hetzner"
- **THEN** invoices matching the supplier name or invoice number are shown
