## Why

The current invoice detail page (`/invoices/:id`) only handles generated invoices (InvoiceRecord). Imported invoices (from vendor uploads) have no detail page at all — they are managed entirely through inline actions in the list view. Users need a unified detail experience that works for both invoice types, showing all relationships (customer, contract, banking/payments), status, history, and content preview (HTML for generated, PDF for imported). Editing extracted metadata on imported invoices also needs a proper UI rather than modal popups in the list.

## What Changes

- Extend `/invoices/:id` to handle both generated and imported invoices via a `type` query param or auto-detection
- Add a backend query to fetch a single imported invoice by ID with full details
- For generated invoices: keep the existing layout (metadata, line items, content preview, payment matches, email history, audit log) but improve the overall page structure
- For imported invoices: show PDF viewer, extracted metadata (editable: invoice number, date, amount, customer, contract), extraction status, payment matches, receiver emails
- Unified sidebar sections: customer link, contract link, payment matches (banking connection), status badge
- Add imported invoice detail route support in InvoiceList (clicking an imported invoice navigates to detail page)

## Capabilities

### New Capabilities
- `imported-invoice-detail`: Detail page for imported invoices showing PDF, extracted metadata (editable), customer/contract links, payment matches, extraction status, and receiver emails

### Modified Capabilities
- `invoice-detail-view`: Extend to serve as a router that detects invoice type and renders the appropriate detail view, plus minor UX improvements to the generated invoice detail

## Impact

- Backend: Add `imported_invoice(id)` query to invoices schema (new resolver)
- Frontend: Extend `InvoiceDetail.tsx` to handle both invoice types, add imported invoice sub-view
- Frontend: Update `InvoiceList.tsx` to link imported invoices to detail page
- No database migrations needed (existing models are sufficient)
- No breaking changes
