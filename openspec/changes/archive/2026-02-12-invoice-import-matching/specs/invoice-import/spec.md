## ADDED Requirements

### Requirement: User can upload invoice PDF
The system SHALL allow users to upload a PDF file of an outgoing invoice they have issued to a customer.

#### Scenario: Upload single invoice PDF
- **WHEN** user selects a PDF file and clicks upload
- **THEN** system stores the PDF in object storage and creates an ImportedInvoice record with status "pending_extraction"

#### Scenario: Reject non-PDF files
- **WHEN** user attempts to upload a file that is not a PDF
- **THEN** system rejects the upload with error "Only PDF files are supported"

#### Scenario: Reject oversized files
- **WHEN** user uploads a PDF larger than the configured maximum size (10MB)
- **THEN** system rejects the upload with error "File too large"

### Requirement: Imported invoice stores metadata
The system SHALL store the following fields for each imported invoice: invoice_number, invoice_date, total_amount, currency, customer_name, customer (FK, nullable), pdf_file, extraction_status, and created_by.

#### Scenario: Invoice record created on upload
- **WHEN** a PDF is successfully uploaded
- **THEN** system creates an ImportedInvoice with extraction_status="pending", pdf_file pointing to stored file, and created_by set to current user

#### Scenario: Invoice linked to customer after matching
- **WHEN** extraction completes and customer is matched
- **THEN** system updates the invoice's customer FK to the matched Customer record

### Requirement: User can view list of imported invoices
The system SHALL display imported invoices in a paginated table showing invoice number, date, customer, amount, payment status, and extraction status.

#### Scenario: View invoice list
- **WHEN** user navigates to the imported invoices page
- **THEN** system displays invoices sorted by invoice_date descending with pagination (25 per page)

#### Scenario: Filter by payment status
- **WHEN** user selects "Unpaid" filter
- **THEN** system shows only invoices without a matching payment transaction

#### Scenario: Search by invoice number
- **WHEN** user types "2025-001" in the search field
- **THEN** system shows only invoices where invoice_number contains "2025-001"

### Requirement: User can delete imported invoice
The system SHALL allow users to delete an imported invoice and its associated PDF.

#### Scenario: Delete invoice
- **WHEN** user clicks delete on an invoice and confirms
- **THEN** system removes the ImportedInvoice record and deletes the PDF from storage

#### Scenario: Delete invoice with payment match
- **WHEN** user deletes an invoice that has payment matches
- **THEN** system also removes the InvoicePaymentMatch records

### Requirement: Imported invoices are tenant-isolated
The system SHALL only show imported invoices belonging to the current user's tenant.

#### Scenario: Tenant isolation
- **WHEN** tenant A has 50 invoices and tenant B has 30 invoices
- **THEN** user from tenant A sees only their 50 invoices
