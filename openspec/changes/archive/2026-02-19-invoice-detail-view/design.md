## Context

Invoice records exist with rich data (amounts, dates, line items, payment matches, email history) but are only viewable as table rows on the export page or contract detail tab. There is no way to inspect a single invoice in full. The backend already has most data available via `InvoiceRecordType` in GraphQL and REST endpoints for PDF/HTML preview. The main gap is a single-record query and a frontend detail page.

## Goals / Non-Goals

**Goals:**
- Dedicated detail page at `/invoices/:id` showing complete invoice context
- View invoice content: HTML render for generated invoices, PDF embed for those with stored PDFs
- See linked customer and contract with navigation
- See payment/banking matches with transaction details
- See email delivery info and send/resend emails
- See status change history via audit log
- Perform actions: void invoice, send email

**Non-Goals:**
- Editing invoice content (invoices are immutable once finalized)
- Editing line items or amounts
- Managing imported invoices (separate workflow, different model)
- Bulk operations from the detail view
- Status transitions beyond void (paid is determined by payment matches, not manual)

## Decisions

### 1. New `invoice_record` single-item query

Add a `invoice_record(id: Int!) -> InvoiceRecordType` query to `InvoiceQuery`. This avoids fetching the full paginated list. The existing `_convert_record` helper and `InvoiceRecordType` already include payment matches, email fields, and pdf_url — no schema changes needed to the type.

**Alternative**: Reuse `invoice_records` with `id` filter — rejected because it returns a connection type with pagination overhead for a single item.

### 2. Invoice content preview via existing REST endpoints

- **Generated invoices**: Use `/api/invoices/preview-html/` for inline HTML preview in an iframe. This endpoint already exists and renders the invoice template. It needs the record's `contract_id`, `billing_date` year/month — all available from the record.
- **Stored PDF**: Use `/api/invoices/<id>/pdf/` to fetch the PDF, display in an iframe or `<object>` embed.
- If both exist (generated + PDF), prefer the PDF since it's the finalized artifact.

**Alternative**: Render HTML server-side and return as a GraphQL field — rejected because HTML can be large and GraphQL isn't suited for binary/large content.

### 3. Audit history via existing `auditLogs` query

The existing `audit_logs` GraphQL query supports filtering by `entity_type` and `entity_id`. Query with `entity_type: "invoice_record"` and `entity_id: <id>` to get the full change history. No backend changes needed.

### 4. Page layout

Use a two-column layout similar to contract detail:
- **Left/main column**: Invoice metadata card (number, dates, status, amounts), line items table, content preview (iframe)
- **Right sidebar or tabs**: Payment matches, email history, audit timeline

On smaller screens, stack vertically.

### 5. Actions in header

- **Send Email** button: visible when status is `finalized`, PDF exists, customer has billing emails, and M365 is configured. Uses existing `send_invoice_email` mutation.
- **Void** button: visible when status is `finalized`. Uses existing `void_invoice` mutation with confirmation dialog.
- **Download PDF** link: always visible when `pdf_url` exists.

### 6. Linking from existing pages

Make invoice numbers clickable as `<Link to={/invoices/${id}}>` on:
- `/invoices/export` table (InvoiceExportPage)
- Contract detail invoices tab (ContractDetail)

This is a minimal change — wrap existing invoice number text in a Link component.

## Risks / Trade-offs

- **HTML preview depends on current contract data**: The preview-html endpoint re-renders from current contract state, not the frozen snapshot. For historical accuracy, the stored PDF is more reliable. → Mitigate by preferring PDF when available, showing HTML only as fallback.
- **Audit log may be sparse**: If invoices were created before audit logging was enabled, history will be empty. → Show "No history available" gracefully.
- **N+1 on payment matches**: The single-record query already uses `prefetch_related` for payment matches. No additional concern.
