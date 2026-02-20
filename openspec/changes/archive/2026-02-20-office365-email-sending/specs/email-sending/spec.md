## ADDED Requirements

### Requirement: Send invoice email via Graph API
The system SHALL send a finalized invoice to the customer's billing email addresses via the Microsoft Graph API `sendMail` endpoint, using the configured sender mailbox. The ZUGFeRD PDF SHALL be included as an attachment.

#### Scenario: Send invoice to customer with billing emails
- **WHEN** user triggers "Send Invoice" on a finalized InvoiceRecord and the customer has billing_emails configured
- **THEN** system dispatches a Celery task that sends the email via Graph API to all billing email addresses, with the PDF attached

#### Scenario: Send invoice when customer has no billing emails
- **WHEN** user triggers "Send Invoice" but the customer has no billing_emails
- **THEN** system returns an error indicating no recipient email addresses are available

#### Scenario: Send invoice when M365 is not configured
- **WHEN** user triggers "Send Invoice" but M365 credentials or sender mailbox are not configured
- **THEN** system returns an error indicating email sending is not configured

#### Scenario: Send invoice when PDF is not yet generated
- **WHEN** user triggers "Send Invoice" but the InvoiceRecord has no pdf_file
- **THEN** system returns an error indicating the PDF must be generated first

#### Scenario: Send invoice that is not finalized
- **WHEN** user triggers "Send Invoice" on a draft InvoiceRecord
- **THEN** system returns an error indicating only finalized invoices can be sent

### Requirement: Track email send status on InvoiceRecord
The system SHALL track when an invoice email was sent, to whom, and the Graph API message ID. Fields: `email_sent_at` (DateTimeField), `email_sent_to` (JSONField list), `email_message_id` (CharField).

#### Scenario: Fields populated after successful send
- **WHEN** the Celery task successfully sends the email
- **THEN** `email_sent_at` is set to the current timestamp, `email_sent_to` contains the list of recipient addresses, and `email_message_id` contains the Graph API message ID

#### Scenario: Fields remain null when not sent
- **WHEN** an invoice has never been sent by email
- **THEN** `email_sent_at` is null, `email_sent_to` is empty, `email_message_id` is empty

### Requirement: Email content uses invoice language
The system SHALL compose the email subject and body based on the customer's `invoice_language` setting, falling back to German if not set.

#### Scenario: German invoice email
- **WHEN** customer has `invoice_language` empty or "de"
- **THEN** email subject is "Rechnung {invoice_number}" and body is in German

#### Scenario: English invoice email
- **WHEN** customer has `invoice_language` set to "en"
- **THEN** email subject is "Invoice {invoice_number}" and body is in English

### Requirement: Expose send status in GraphQL
The system SHALL expose `emailSentAt`, `emailSentTo`, and `emailMessageId` on the `InvoiceRecordType` GraphQL type. A `sendInvoiceEmail` mutation SHALL trigger the send.

#### Scenario: Query sent invoice
- **WHEN** user queries an InvoiceRecord that has been sent
- **THEN** response includes `emailSentAt` timestamp and `emailSentTo` list

#### Scenario: Send invoice mutation
- **WHEN** user calls `sendInvoiceEmail(invoiceRecordId: ID!)` with valid permissions
- **THEN** system validates preconditions and dispatches the send task, returning success

#### Scenario: Send requires invoices.write permission
- **WHEN** a user without `invoices.write` permission calls `sendInvoiceEmail`
- **THEN** system returns a permission error

### Requirement: Display send status in invoice list
The system SHALL show an email sent indicator on invoices in the frontend list views, and provide a "Send" action button for finalized invoices that have not been sent.

#### Scenario: Unsent finalized invoice shows send button
- **WHEN** a finalized invoice with `emailSentAt` null is displayed in the invoice list
- **THEN** a "Send" action button (Mail icon) is visible

#### Scenario: Sent invoice shows sent indicator
- **WHEN** an invoice with `emailSentAt` set is displayed in the invoice list
- **THEN** a sent badge with the date is shown and the send button is hidden

#### Scenario: Send button hidden when M365 not configured
- **WHEN** M365 is not configured for the tenant
- **THEN** the send button is not shown on any invoices

### Requirement: Handle send failures gracefully
The system SHALL NOT retry failed sends automatically to avoid duplicate emails. Errors SHALL be logged and surfaced to the user.

#### Scenario: Graph API returns error
- **WHEN** the Graph API returns an error (auth failure, mailbox not found, etc.)
- **THEN** the Celery task logs the error and the `email_sent_at` remains null

#### Scenario: User can retry after failure
- **WHEN** a previous send attempt failed and the user clicks "Send" again
- **THEN** system dispatches a new send task (no deduplication needed since previous attempt left no sent state)
