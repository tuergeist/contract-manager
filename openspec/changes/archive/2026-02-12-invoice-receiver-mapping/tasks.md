## 1. Backend: InvoiceImportBatch Model

- [x] 1.1 Create InvoiceImportBatch model with fields: name, uploaded_at, uploaded_by FK, total_expected, total_uploaded
- [x] 1.2 Add UploadStatus choices: pending, uploaded
- [x] 1.3 Create migration for InvoiceImportBatch

## 2. Backend: ImportedInvoice Extensions

- [x] 2.1 Add import_batch FK to ImportedInvoice (nullable, SET_NULL on delete)
- [x] 2.2 Add expected_filename CharField to ImportedInvoice
- [x] 2.3 Add receiver_emails JSONField to ImportedInvoice (default=list)
- [x] 2.4 Add upload_status CharField to ImportedInvoice with UploadStatus choices
- [x] 2.5 Create migration for ImportedInvoice extensions

## 3. Backend: Customer Billing Emails

- [x] 3.1 Add billing_emails JSONField to Customer model (default=list)
- [x] 3.2 Create migration for Customer.billing_emails

## 4. Backend: CSV Upload GraphQL

- [x] 4.1 Create InvoiceImportBatchType with fields and computed stats
- [x] 4.2 Add uploadInvoiceCsv mutation accepting base64 CSV content
- [x] 4.3 Implement CSV parsing with validation (required columns, max 1000 rows)
- [x] 4.4 Create ImportedInvoice records from CSV rows with upload_status=pending
- [x] 4.5 Add importBatches query with pagination
- [x] 4.6 Add importBatch query for single batch by ID
- [x] 4.7 Add deleteImportBatch mutation (removes batch and pending invoices)

## 5. Backend: Bulk PDF Upload

- [x] 5.1 Add uploadInvoices mutation accepting list of base64 PDF content with filenames
- [x] 5.2 Implement filename matching logic (case-insensitive, most recent pending)
- [x] 5.3 Update matched records with pdf_file and upload_status=uploaded
- [x] 5.4 Create new records for unmatched PDFs
- [x] 5.5 Return per-file results with success/error status
- [x] 5.6 Trigger extraction for each uploaded PDF

## 6. Backend: Email Transfer on Customer Confirmation

- [x] 6.1 Modify confirmCustomerMatch mutation to merge receiver_emails to Customer.billing_emails
- [x] 6.2 Implement case-insensitive email deduplication
- [x] 6.3 Add updateCustomerBillingEmails mutation for manual add/remove
- [x] 6.4 Add email format validation

## 7. Backend: Query Extensions

- [x] 7.1 Add uploadStatus filter to importedInvoices query
- [x] 7.2 Add pendingInvoices query for batch (invoices with upload_status=pending)
- [x] 7.3 Include receiver_emails and upload_status in ImportedInvoiceType
- [x] 7.4 Include billing_emails in CustomerType

## 8. Backend: Tests

- [x] 8.1 Add tests for InvoiceImportBatch model
- [x] 8.2 Add tests for CSV upload mutation (valid CSV, invalid format, oversized)
- [x] 8.3 Add tests for bulk PDF upload with filename matching
- [x] 8.4 Add tests for email transfer on customer confirmation
- [x] 8.5 Add tests for billing email deduplication
- [x] 8.6 Add tests for batch deletion (pending only vs mixed)

## 9. Frontend: CSV Upload UI

- [x] 9.1 Add "Import CSV" button to ImportedInvoiceList page
- [x] 9.2 Create CsvUploadModal with file dropzone
- [x] 9.3 Validate CSV file type
- [x] 9.4 Convert to base64 and call uploadInvoiceCsv mutation
- [x] 9.5 Show upload result with expected invoice count
- [x] 9.6 Display import batches list on page

## 10. Frontend: Bulk PDF Upload

- [x] 10.1 Modify InvoiceUploadModal to accept multiple files
- [x] 10.2 Show file list with individual status indicators
- [x] 10.3 Call uploadInvoices mutation with all files
- [x] 10.4 Display per-file results (matched to expected, new, failed)
- [x] 10.5 Show progress during bulk upload

## 11. Frontend: Pending Uploads View

- [x] 11.1 Add "Pending Upload" filter option to invoice list
- [x] 11.2 Show expected_filename and receiver_emails for pending invoices
- [x] 11.3 Add batch detail view showing pending vs uploaded count
- [x] 11.4 Add delete batch action with confirmation

## 12. Frontend: Customer Billing Emails

- [x] 12.1 Display billing_emails on CustomerDetail page
- [x] 12.2 Add inline add/remove UI for billing emails
- [x] 12.3 Add email format validation on frontend

## 13. Frontend: Invoice Receiver Display

- [x] 13.1 Show receiver_emails on invoice detail/review modal
- [x] 13.2 Show upload_status badge on invoice list rows

## 14. Localization

- [x] 14.1 Add English translations for CSV upload, bulk upload, pending uploads UI
- [x] 14.2 Add German translations for CSV upload, bulk upload, pending uploads UI
