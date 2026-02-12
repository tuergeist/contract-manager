## Why

When importing outgoing invoices, users need to track who should receive each invoice (billing contacts). Currently, invoices can be uploaded one at a time with no way to associate receiver emails. Users have CSV exports from their invoicing system that map invoice filenames to billing email addresses. Supporting CSV-based receiver mapping and bulk PDF upload streamlines the import workflow and establishes billing contact data for customers.

## What Changes

- Add CSV upload to define expected invoices with their receiver email addresses (1+ emails per invoice)
- Support bulk PDF upload (multiple files at once)
- Match uploaded PDFs to CSV entries by filename
- Show "pending uploads" view listing invoices from CSV that haven't been uploaded yet
- Store receiver emails on imported invoices, then transfer to Customer as billing contacts when customer is confirmed
- Add billing_emails field to Customer model for long-term storage of billing contacts

## Capabilities

### New Capabilities
- `invoice-receiver-mapping`: CSV upload defining expected invoices with receiver emails, filename-based matching to uploaded PDFs, pending upload tracking

### Modified Capabilities
- `invoice-import`: Add bulk PDF upload, expected_filename field, link to receiver mapping, upload_status tracking
- `customer-billing-contacts`: Add billing_emails field to Customer for storing company billing contact emails

## Impact

- **Backend Models**: Add billing_emails to Customer, add expected_filename and receiver_emails to ImportedInvoice, add InvoiceImportBatch model for CSV uploads
- **GraphQL API**: New mutations for CSV upload, bulk PDF upload; new queries for pending uploads
- **Frontend**: New CSV upload UI, bulk file dropzone, pending uploads table in import workflow
- **Database**: Migrations for new fields and models
