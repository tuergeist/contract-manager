## ADDED Requirements

### Requirement: User can upload multiple invoice PDFs at once
The system SHALL allow users to upload multiple PDF files in a single operation.

#### Scenario: Bulk upload multiple PDFs
- **WHEN** user selects 5 PDF files and clicks upload
- **THEN** system processes each file, matching to expected records or creating new ones, and returns results for each file

#### Scenario: Partial failure in bulk upload
- **WHEN** user uploads 5 PDFs and 2 fail validation (e.g., too large)
- **THEN** system processes the 3 valid PDFs and returns errors for the 2 failed ones

#### Scenario: Bulk upload progress feedback
- **WHEN** user initiates a bulk upload of 10 PDFs
- **THEN** system shows upload progress and individual file status as each completes

## MODIFIED Requirements

### Requirement: Imported invoice stores metadata
The system SHALL store the following fields for each imported invoice: invoice_number, invoice_date, total_amount, currency, customer_name, customer (FK, nullable), pdf_file, extraction_status, created_by, import_batch (FK, nullable), expected_filename, receiver_emails, and upload_status.

#### Scenario: Invoice record created on upload
- **WHEN** a PDF is successfully uploaded
- **THEN** system creates an ImportedInvoice with extraction_status="pending", pdf_file pointing to stored file, and created_by set to current user

#### Scenario: Invoice linked to customer after matching
- **WHEN** extraction completes and customer is matched
- **THEN** system updates the invoice's customer FK to the matched Customer record

#### Scenario: Invoice created from CSV
- **WHEN** a CSV row is processed
- **THEN** system creates an ImportedInvoice with upload_status="pending", expected_filename from CSV, receiver_emails from CSV, and no pdf_file

#### Scenario: Invoice updated when PDF matches expected
- **WHEN** a PDF is uploaded that matches an expected_filename
- **THEN** system updates the existing record with pdf_file and sets upload_status="uploaded"
