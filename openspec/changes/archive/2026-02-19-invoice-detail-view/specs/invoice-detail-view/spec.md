## ADDED Requirements

### Requirement: Invoice detail page displays invoice metadata

The system SHALL provide a detail page at `/invoices/:id` that displays the full metadata of a single invoice record including invoice number, billing date, invoice date, period, amounts (net, tax, gross), tax rate, status, and generation timestamp.

#### Scenario: User navigates to invoice detail
- **WHEN** user navigates to `/invoices/123`
- **THEN** the page SHALL display the invoice record with id 123
- **AND** show invoice number, billing date, invoice date, period start/end, total net, tax rate, tax amount, total gross, status, and generated-at timestamp

#### Scenario: Invoice not found
- **WHEN** user navigates to `/invoices/999` and no record exists with that id
- **THEN** the page SHALL display an error message indicating the invoice was not found

### Requirement: Invoice detail shows linked customer and contract

The detail page SHALL display the associated customer name and contract name as clickable links navigating to their respective detail pages.

#### Scenario: Customer and contract links displayed
- **WHEN** user views an invoice detail page
- **THEN** the customer name SHALL link to `/customers/:customerId`
- **AND** the contract name SHALL link to `/contracts/:contractId`

#### Scenario: Customer or contract was deleted
- **WHEN** the invoice's customer or contract has been deleted (null foreign key)
- **THEN** the page SHALL display the denormalized name without a link

### Requirement: Invoice detail shows content preview

The detail page SHALL display the invoice content inline. For records with a stored PDF, it SHALL embed the PDF. For records without a PDF, it SHALL render the invoice HTML via the preview endpoint.

#### Scenario: Invoice has stored PDF
- **WHEN** user views an invoice that has a pdf_url
- **THEN** the page SHALL embed the PDF in an iframe for viewing

#### Scenario: Invoice has no PDF but is generated
- **WHEN** user views a generated invoice without a stored PDF
- **THEN** the page SHALL load and display the HTML preview via `/api/invoices/preview-html/` in an iframe

### Requirement: Invoice detail shows payment matches

The detail page SHALL display all payment matches linked to the invoice, showing transaction date, amount, counterparty, match type, confidence, and who matched it.

#### Scenario: Invoice has payment matches
- **WHEN** user views an invoice with one or more payment matches
- **THEN** the page SHALL list each match with transaction date, amount, counterparty name, match type, confidence percentage, and matched-by user

#### Scenario: Invoice has no payment matches
- **WHEN** user views an invoice with no payment matches
- **THEN** the page SHALL display a message indicating no payments have been matched

### Requirement: Invoice detail shows email delivery history

The detail page SHALL display email delivery information including when the invoice was sent, to which recipients, and the message ID.

#### Scenario: Invoice was sent by email
- **WHEN** user views an invoice where email_sent_at is set
- **THEN** the page SHALL display the sent timestamp, list of recipients, and message ID

#### Scenario: Invoice was not sent by email
- **WHEN** user views an invoice where email_sent_at is null
- **THEN** the page SHALL indicate the invoice has not been sent by email

### Requirement: Invoice detail shows status change history

The detail page SHALL display the audit log for the invoice record, showing a timeline of status changes and other modifications.

#### Scenario: Invoice has audit history
- **WHEN** user views an invoice with audit log entries
- **THEN** the page SHALL display a timeline of changes including timestamp, user, action, and changed fields

#### Scenario: Invoice has no audit history
- **WHEN** user views an invoice with no audit log entries
- **THEN** the page SHALL display a message indicating no history is available

### Requirement: Invoice detail allows sending email

The detail page SHALL provide a "Send Email" action for finalized invoices that have a generated PDF and a customer with billing emails configured.

#### Scenario: Send email button available
- **WHEN** user views a finalized invoice with a PDF and customer billing emails
- **THEN** a "Send Email" button SHALL be visible

#### Scenario: Send email succeeds
- **WHEN** user clicks "Send Email"
- **THEN** the system SHALL enqueue the email delivery
- **AND** display a success message

#### Scenario: Send email not available
- **WHEN** the invoice is not finalized, has no PDF, or customer has no billing emails
- **THEN** the "Send Email" button SHALL not be visible

### Requirement: Invoice detail allows voiding

The detail page SHALL provide a "Void" action for finalized invoices, with a confirmation dialog.

#### Scenario: Void button available
- **WHEN** user views a finalized invoice
- **THEN** a "Void" button SHALL be visible

#### Scenario: Void with confirmation
- **WHEN** user clicks "Void"
- **THEN** the system SHALL show a confirmation dialog
- **AND** upon confirmation, call the void_invoice mutation
- **AND** update the displayed status to "voided"

#### Scenario: Void not available for non-finalized invoices
- **WHEN** user views an invoice that is not finalized (e.g., voided, sent, paid)
- **THEN** the "Void" button SHALL not be visible

### Requirement: Invoice detail provides PDF download

The detail page SHALL provide a download link for the invoice PDF when available.

#### Scenario: PDF download available
- **WHEN** user views an invoice with a pdf_url
- **THEN** a "Download PDF" link SHALL be visible that opens the PDF in a new tab

#### Scenario: No PDF available
- **WHEN** user views an invoice without a pdf_url
- **THEN** no download link SHALL be shown

### Requirement: Existing pages link to invoice detail

Invoice numbers on the export page and contract detail invoices tab SHALL be clickable links navigating to the invoice detail page.

#### Scenario: Invoice number links on export page
- **WHEN** user views the invoice export page with generated records
- **THEN** each invoice number SHALL be a link to `/invoices/:id`

#### Scenario: Invoice number links on contract detail
- **WHEN** user views the invoices tab on a contract detail page
- **THEN** each generated invoice number SHALL be a link to `/invoices/:id`
