## ADDED Requirements

### Requirement: User can upload CSV with invoice receiver mapping
The system SHALL allow users to upload a CSV file that maps invoice filenames to receiver email addresses.

#### Scenario: Upload valid CSV
- **WHEN** user uploads a CSV file with columns "filename" and "emails"
- **THEN** system creates an InvoiceImportBatch and ImportedInvoice records for each row with upload_status="pending" and receiver_emails populated

#### Scenario: CSV with multiple emails per invoice
- **WHEN** CSV row contains "invoice-001.pdf" with emails "billing@acme.com,finance@acme.com"
- **THEN** system stores receiver_emails as ["billing@acme.com", "finance@acme.com"] on the ImportedInvoice record

#### Scenario: Reject invalid CSV format
- **WHEN** user uploads a CSV missing required columns
- **THEN** system rejects with error "CSV must contain 'filename' and 'emails' columns"

#### Scenario: Reject oversized CSV
- **WHEN** user uploads a CSV with more than 1000 rows
- **THEN** system rejects with error "CSV exceeds maximum of 1000 rows"

### Requirement: System matches uploaded PDFs to expected invoices by filename
The system SHALL match uploaded PDF files to expected invoice records using case-insensitive filename comparison.

#### Scenario: PDF matches expected filename
- **WHEN** user uploads "Invoice-2025-001.pdf" and an expected invoice exists with expected_filename="invoice-2025-001.pdf"
- **THEN** system links the PDF to the existing ImportedInvoice record and updates upload_status to "uploaded"

#### Scenario: PDF with no matching expected record
- **WHEN** user uploads a PDF that does not match any expected filename
- **THEN** system creates a new ImportedInvoice record with empty receiver_emails

#### Scenario: Duplicate filename in multiple batches
- **WHEN** same filename exists in multiple batches with upload_status="pending"
- **THEN** system matches to the most recently created pending record

### Requirement: User can view pending uploads
The system SHALL display a list of expected invoices from CSV that have not yet been uploaded.

#### Scenario: View pending uploads for a batch
- **WHEN** user views an import batch with 10 expected invoices and 7 uploaded
- **THEN** system shows 3 pending invoices with their expected filenames and receiver emails

#### Scenario: Filter invoice list by upload status
- **WHEN** user selects "Pending Upload" filter on imported invoices page
- **THEN** system shows only invoices where upload_status="pending"

### Requirement: User can delete an import batch
The system SHALL allow users to delete an import batch and its pending invoice records.

#### Scenario: Delete batch with pending invoices only
- **WHEN** user deletes an import batch where all invoices have upload_status="pending"
- **THEN** system removes the batch and all associated pending ImportedInvoice records

#### Scenario: Delete batch with uploaded invoices
- **WHEN** user deletes an import batch that has some invoices with upload_status="uploaded"
- **THEN** system removes the batch, removes pending invoices, but keeps uploaded invoices (clearing their import_batch reference)

### Requirement: Import batches are tenant-isolated
The system SHALL only show import batches belonging to the current user's tenant.

#### Scenario: Tenant isolation for batches
- **WHEN** tenant A has 3 batches and tenant B has 5 batches
- **THEN** user from tenant A sees only their 3 batches
