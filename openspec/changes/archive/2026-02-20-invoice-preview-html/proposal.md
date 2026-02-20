## Why

Before exporting/generating invoices, users need a way to verify that all invoice data (customer address, line items, amounts, tax, PO numbers, etc.) is correct. Currently the only "preview" on `/invoices/export` is a summary table showing totals and expandable line items — but it doesn't show the actual rendered invoice layout. The separate `/api/invoices/preview/` endpoint generates a PDF with dummy data, which isn't useful for verifying real invoices. Users need an inline HTML preview of each real invoice (minus the invoice number, which is only assigned on generation) so they can do a final check before committing.

## What Changes

- Add an HTML preview mode on the `/invoices/export` page that renders each invoice as it would appear on the final PDF — including company header, customer billing address, billing period, line items table, subtotal/tax/total, PO number, order confirmation number, and invoice text
- The preview shows all real data for the selected month except the invoice number (which is assigned only upon generation)
- Backend provides a new endpoint (or extends the existing export endpoint) that returns rendered HTML for invoice previews rather than triggering a file download
- Preview is rendered inline on the page (e.g. in a modal or expandable section per invoice row) so users can review without leaving the page

## Capabilities

### New Capabilities
- `invoice-html-preview`: Inline HTML preview of real invoices on the export page, showing the full rendered invoice layout with all data except invoice number

### Modified Capabilities
- `invoice-export`: The export page gains a preview action per invoice row (UI change to surface the HTML preview)

## Impact

- **Frontend**: `InvoiceExportPage.tsx` — add preview trigger (button/icon per row) and inline HTML rendering (iframe or modal)
- **Backend**: `apps/invoices/views.py` — new endpoint or new format parameter to return rendered invoice HTML
- **Backend**: `apps/invoices/services.py` — method to render invoice HTML without converting to PDF
- **Templates**: Existing `invoices/invoice.html` template is reused for rendering
- **Translations**: New i18n keys for preview button/labels in `de.json` and `en.json`
