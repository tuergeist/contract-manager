## Why

Invoices exist in the system but lack a dedicated detail view. Users currently see invoices only as rows in the export page or contract detail tab, with no way to inspect an individual invoice's full context — its payment status, banking links, email delivery history, status timeline, or rendered content. This forces users to cross-reference multiple pages to get a complete picture of a single invoice.

## What Changes

- Add a new `/invoices/:id` detail page for generated invoice records (InvoiceRecord)
- Display invoice metadata: number, dates, amounts, status, customer, contract
- Show rendered invoice content inline (HTML preview for generated invoices, PDF embed for imported)
- Show payment/banking matches with links to transaction details
- Show email delivery history (when sent, to whom, message ID)
- Show audit log / status change history for the invoice
- Allow sending invoice email directly from the detail view
- Allow voiding an invoice from the detail view
- Link back to related customer and contract detail pages

## Capabilities

### New Capabilities
- `invoice-detail-view`: Detail page for inspecting a single invoice record with full context — content preview, payment matches, email history, status timeline, and actions (send email, void)

### Modified Capabilities
- `invoice-generation`: Add GraphQL query to fetch a single invoice record by ID with all related data (payment matches, audit log entries)

## Impact

- **Frontend**: New route `/invoices/:id`, new `InvoiceDetail` component in `frontend/src/features/invoices/`
- **Backend GraphQL**: New `invoice_record(id)` query returning full record with nested payment matches and audit entries
- **Backend REST**: Uses existing `/api/invoices/preview-html/` endpoint for generated invoice HTML preview and existing `/api/invoices/<id>/pdf/` for PDF viewing
- **Existing pages**: Invoice tables on `/invoices/export` and contract detail should link invoice numbers to the new detail page
