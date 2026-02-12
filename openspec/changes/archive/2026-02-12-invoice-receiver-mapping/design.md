## Context

Users import outgoing invoices by uploading PDFs, which are then processed for extraction. Currently this is one file at a time with no way to track intended recipients. Users have CSV exports from their invoicing systems that map invoice filenames to billing email addresses.

The invoice-import-matching change added ImportedInvoice model with extraction and payment matching. This change extends it with receiver tracking and bulk operations.

## Goals / Non-Goals

**Goals:**
- CSV upload creates "expected invoice" records before PDFs arrive
- Bulk PDF upload matches files to expected records by filename
- Track pending uploads (CSV entries without matching PDF)
- Store receiver emails on invoices, transfer to Customer on confirmation
- Support 1+ receiver emails per invoice

**Non-Goals:**
- Email sending (future feature)
- HubSpot sync for billing contacts (separate feature)
- Editing receiver emails after customer confirmation
- Complex CSV formats (keep it simple: filename, emails)

## Decisions

### 1. InvoiceImportBatch model for CSV uploads

Create a batch record to group expected invoices from a single CSV upload.

```python
class InvoiceImportBatch(TenantModel):
    name = models.CharField(max_length=255)  # CSV filename or user-provided
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    total_expected = models.IntegerField(default=0)
    total_uploaded = models.IntegerField(default=0)
```

**Rationale**: Grouping by batch allows users to track progress per import session and delete a batch if needed.

**Alternative considered**: No batch, just create ImportedInvoice records directly. Rejected because it loses the "session" context and makes pending tracking harder.

### 2. Extend ImportedInvoice for receiver tracking

Add fields to existing model rather than creating a separate mapping table:

```python
class ImportedInvoice(TenantModel):
    # ... existing fields ...
    import_batch = models.ForeignKey(InvoiceImportBatch, null=True, on_delete=models.SET_NULL)
    expected_filename = models.CharField(max_length=255, blank=True)
    receiver_emails = models.JSONField(default=list)  # ["billing@acme.com", "finance@acme.com"]
    upload_status = models.CharField(choices=UploadStatus.choices, default="pending")
```

**UploadStatus choices**: `pending` (from CSV, no PDF yet), `uploaded` (PDF received)

**Rationale**: Keeps invoice data together. JSONField for emails is simple and sufficient for 1-5 emails per invoice.

**Alternative considered**: Separate ExpectedInvoice model. Rejected as it complicates the data model for minimal benefit.

### 3. Customer.billing_emails as JSONField

```python
class Customer(TenantModel):
    # ... existing fields ...
    billing_emails = models.JSONField(default=list)
```

**Rationale**: Simple storage for a list of emails. No need for a separate BillingContact model since we don't need to track per-contact metadata.

### 4. CSV format: simple two-column

```csv
filename,emails
invoice-2025-001.pdf,billing@acme.com
invoice-2025-002.pdf,"billing@other.com,finance@other.com"
```

- Column 1: filename (must match uploaded PDF filename exactly)
- Column 2: comma-separated emails (quoted if multiple)

**Rationale**: Minimal format that users can easily create from their invoicing system exports.

### 5. Filename matching: exact match, case-insensitive

When PDF is uploaded, match against `expected_filename` using case-insensitive comparison.

**Rationale**: Simple and predictable. Users control filenames.

**Alternative considered**: Fuzzy matching on invoice number extracted from filename. Rejected as too error-prone.

### 6. Bulk upload: process sequentially with progress

Upload mutation accepts multiple files, processes each:
1. Store PDF
2. Match to expected record by filename (or create new if no match)
3. Trigger extraction
4. Return list of results with success/failure per file

**Rationale**: Sequential processing is simpler and provides clear per-file feedback.

### 7. Transfer emails to Customer on confirmation

When user confirms customer match on an invoice:
1. Get receiver_emails from invoice
2. Merge into Customer.billing_emails (avoid duplicates)
3. Keep receiver_emails on invoice for audit trail

**Rationale**: Emails belong to the company, not just one invoice. Merging builds the customer's contact list over time.

## Risks / Trade-offs

**[Duplicate emails across invoices]** → Merge with deduplication when transferring to Customer. Store as lowercase for comparison.

**[Large CSV files]** → Limit to 1000 rows per upload. Show clear error if exceeded.

**[Filename conflicts]** → If same filename appears in multiple batches, match to most recent pending record. Warn user if ambiguous.

**[PDF uploaded without CSV]** → Allow it. Invoice gets created with empty receiver_emails, can be edited later.

## Migration Plan

1. Add InvoiceImportBatch model with migration
2. Add fields to ImportedInvoice (import_batch, expected_filename, receiver_emails, upload_status)
3. Add billing_emails to Customer
4. Deploy backend, run migrations
5. Deploy frontend with new CSV upload UI

**Rollback**: All changes are additive. Existing invoices continue to work. Remove UI to disable feature if needed.
