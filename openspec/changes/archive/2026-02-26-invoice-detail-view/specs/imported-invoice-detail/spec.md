## ADDED Requirements

### Requirement: Imported invoice detail page
The system SHALL provide a detail page for imported invoices at `/invoices/:id?type=imported` showing all invoice metadata, PDF preview, relationships, and payment information. The page SHALL use the existing `invoice(id)` GraphQL query.

#### Scenario: View imported invoice detail
- **WHEN** a user navigates to `/invoices/:id?type=imported` for an existing imported invoice
- **THEN** the page displays the invoice metadata, PDF preview, customer/contract links, payment matches, and receiver emails

#### Scenario: Imported invoice not found
- **WHEN** a user navigates to `/invoices/:id?type=imported` with an invalid ID
- **THEN** the page displays an error message indicating the invoice was not found

### Requirement: Imported invoice PDF preview
The detail page SHALL display the imported invoice's PDF in an embedded viewer. The PDF SHALL be loaded from the `pdfUrl` field.

#### Scenario: PDF available
- **WHEN** viewing an imported invoice that has a PDF file uploaded (`uploadStatus = 'uploaded'`)
- **THEN** the page displays the PDF in an embedded viewer

#### Scenario: PDF not yet uploaded
- **WHEN** viewing an imported invoice with `uploadStatus = 'pending'` (CSV row without PDF)
- **THEN** the page displays a placeholder indicating the PDF has not been uploaded yet

### Requirement: Imported invoice metadata display
The detail page SHALL display extracted metadata: invoice number, invoice date, total amount (with currency), original filename, file size, extraction status, and creation info (created by, created at).

#### Scenario: Fully extracted invoice
- **WHEN** viewing an imported invoice with `extractionStatus = 'extracted'` or `'confirmed'`
- **THEN** all extracted fields (invoice number, date, amount) are displayed

#### Scenario: Pending extraction
- **WHEN** viewing an imported invoice with `extractionStatus = 'pending'`
- **THEN** the page shows a notice that extraction is pending and displays an "Extract" action button

#### Scenario: Failed extraction
- **WHEN** viewing an imported invoice with `extractionStatus = 'extraction_failed'`
- **THEN** the page shows the extraction error message and a "Re-extract" action button

### Requirement: Imported invoice metadata editing
The detail page SHALL allow editing extracted metadata fields (invoice number, invoice date, total amount) inline. Changes SHALL be saved via the `updateInvoice` mutation.

#### Scenario: Edit invoice number
- **WHEN** a user edits the invoice number field and saves
- **THEN** the `updateInvoice` mutation is called and the field updates on success

#### Scenario: Edit invoice date
- **WHEN** a user edits the invoice date field and saves
- **THEN** the `updateInvoice` mutation is called and the field updates on success

#### Scenario: Edit total amount
- **WHEN** a user edits the total amount field and saves
- **THEN** the `updateInvoice` mutation is called and the field updates on success

### Requirement: Imported invoice customer link
The detail page SHALL display the linked customer (if any) with a link to the customer detail page. If no customer is linked, the page SHALL show the extracted `customerName` and a button to open the customer picker with AI-suggested matches.

#### Scenario: Customer linked
- **WHEN** viewing an imported invoice with a linked `customerId`
- **THEN** the customer name is displayed as a link to `/customers/:customerId` with an option to unlink

#### Scenario: Customer name extracted but not linked
- **WHEN** viewing an imported invoice with `customerName` but no `customerId`
- **THEN** the extracted name is shown with a "Link Customer" button that opens the customer picker with `customerMatchSuggestions`

#### Scenario: No customer information
- **WHEN** viewing an imported invoice with no `customerName` and no `customerId`
- **THEN** the page shows "No customer" with a "Link Customer" button

### Requirement: Imported invoice contract link
The detail page SHALL display the linked contract (if any) with a link to the contract detail page. The user SHALL be able to link or unlink a contract via the `assignInvoiceContract` mutation.

#### Scenario: Contract linked
- **WHEN** viewing an imported invoice with a linked `contractId`
- **THEN** the contract name is displayed as a link to `/contracts/:contractId` with an option to unlink

#### Scenario: No contract linked
- **WHEN** viewing an imported invoice with no `contractId`
- **THEN** a "Link Contract" action is available (requires customer to be linked first)

### Requirement: Imported invoice payment matches
The detail page SHALL display existing payment matches and allow adding/removing matches. The system SHALL show AI-suggested matches from `findPaymentMatches` query.

#### Scenario: View existing payment matches
- **WHEN** viewing an imported invoice with payment matches
- **THEN** each match displays the transaction date, amount, counterparty, match type, confidence, and matched-by user

#### Scenario: Add payment match
- **WHEN** a user clicks "Add Payment Match" on an unpaid imported invoice
- **THEN** a modal shows AI-suggested matches and a manual search option, and linking a match calls `createPaymentMatch`

#### Scenario: Remove payment match
- **WHEN** a user removes a payment match
- **THEN** the `deletePaymentMatch` mutation is called and the match is removed from the display

### Requirement: Imported invoice receiver emails
The detail page SHALL display the receiver email addresses from the CSV import mapping (the `receiverEmails` JSON field), if any exist.

#### Scenario: Receiver emails present
- **WHEN** viewing an imported invoice with `receiverEmails` containing entries
- **THEN** the email addresses are displayed in a list

#### Scenario: No receiver emails
- **WHEN** viewing an imported invoice with empty or null `receiverEmails`
- **THEN** the receiver emails section is not shown

### Requirement: Imported invoice actions
The detail page SHALL provide action buttons for: extract/re-extract (based on extraction status), confirm extraction, delete invoice, and download PDF.

#### Scenario: Extract action on pending invoice
- **WHEN** viewing an imported invoice with `extractionStatus = 'pending'`
- **THEN** an "Extract" button is available that calls the `extractInvoice` mutation

#### Scenario: Re-extract action on failed invoice
- **WHEN** viewing an imported invoice with `extractionStatus = 'extraction_failed'`
- **THEN** a "Re-extract" button is available that calls the `reExtractInvoice` mutation

#### Scenario: Confirm action on extracted invoice
- **WHEN** viewing an imported invoice with `extractionStatus = 'extracted'`
- **THEN** a "Confirm" button is available that calls the `confirmInvoice` mutation

#### Scenario: Delete imported invoice
- **WHEN** a user with `invoices.generate` permission clicks "Delete"
- **THEN** a confirmation dialog appears, and on confirmation the `deleteInvoice` mutation is called and the user is navigated back to `/invoices`

#### Scenario: Download PDF
- **WHEN** viewing an imported invoice with a PDF file
- **THEN** a "Download PDF" button opens the PDF in a new tab
