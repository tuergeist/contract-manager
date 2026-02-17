## RENAMED Requirements

### Requirement: GraphQL invoice query names
- FROM: `importedInvoices` query, `importedInvoice` query
- TO: `invoices` query, `invoice` query

### Requirement: GraphQL invoice mutation names
- FROM: `updateImportedInvoice`, `deleteImportedInvoice`, `confirmImportedInvoice`
- TO: `updateInvoice`, `deleteInvoice`, `confirmInvoice`

### Requirement: GraphQL invoice type names
- FROM: `ImportedInvoiceType`, `ImportedInvoiceConnection`, `ImportedInvoiceResult`, `UpdateImportedInvoiceInput`
- TO: `InvoiceType`, `InvoiceConnection`, `InvoiceResult`, `UpdateInvoiceInput`

### Requirement: Frontend component and interface names
- FROM: `ImportedInvoiceList` component (file: `ImportedInvoiceList.tsx`), `ImportedInvoice` interface, `ImportBatch` interface
- TO: `InvoiceList` component (file: `InvoiceList.tsx`), `Invoice` interface, `InvoiceImportBatch` interface

## MODIFIED Requirements

### Requirement: Imported invoice stores metadata
The system SHALL store the following fields for each imported invoice: invoice_number, invoice_date, total_amount, currency, customer_name, customer (FK, nullable), pdf_file, extraction_status, created_by, import_batch (FK, nullable), expected_filename, receiver_emails, and upload_status.

The Django model SHALL remain named `ImportedInvoice` with its existing database table. The GraphQL type exposed to the frontend SHALL be named `InvoiceType`.

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

#### Scenario: GraphQL type name reflects generic invoice concept
- **WHEN** the frontend queries for invoices
- **THEN** the GraphQL schema SHALL expose the type as `InvoiceType` (not `ImportedInvoiceType`)
