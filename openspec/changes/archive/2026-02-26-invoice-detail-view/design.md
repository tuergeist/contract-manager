## Context

The existing invoice detail page (`/invoices/:id` in `InvoiceDetail.tsx`) only handles generated invoices (`InvoiceRecord`). It has a two-column layout: main content (metadata, amounts, line items, preview) and sidebar (payment matches, email history, audit log).

Imported invoices (`ImportedInvoice`) have no detail page — all interactions happen through inline actions and modals in `InvoiceList.tsx` (extract, link customer, link contract, payment matching, view PDF, delete). The backend already has an `invoice(id)` query that returns a single imported invoice with all fields needed for a detail page.

The two invoice types have different models, different GraphQL types (`InvoiceRecordType` vs `InvoiceType`), and different ID spaces (both are auto-incrementing integers, so IDs can collide).

## Goals / Non-Goals

**Goals:**
- Unified detail page experience for both invoice types at `/invoices/:id`
- Imported invoice detail with PDF preview, editable metadata, relationship management, and payment matching
- All imported invoice list actions available on the detail page
- Imported invoices clickable from the invoice list

**Non-Goals:**
- Merging the two invoice models or GraphQL types into one
- Changing the generated invoice detail layout (only adding routing logic)
- Adding new backend queries or mutations (all needed endpoints already exist)
- Batch operations from the detail page

## Decisions

### 1. Type detection via query parameter with auto-fallback

Use `?type=imported` query parameter to distinguish invoice types. The `InvoiceDetail` component checks this parameter first. If `type=imported`, it renders the imported invoice view. If absent or `type=generated`, it loads the generated invoice. If the generated invoice query returns not-found and no `type` was specified, fall back to trying the imported invoice query.

**Why query param over path segments:** Both types share the `/invoices` namespace and use integer IDs. A query param (`?type=imported`) keeps the URL structure clean and avoids adding new routes. The invoice list already knows the type when generating links, so it can set the param. Direct URL access without the param still works via fallback.

**Alternative considered:** Separate routes like `/invoices/imported/:id`. Rejected — it fragments the URL space and requires route changes for a concept that's really one entity type viewed differently.

### 2. Separate component for imported invoice detail

Create `ImportedInvoiceDetail` as a new component within the same file (or a sibling file). `InvoiceDetail.tsx` becomes a thin router: check `type` param → render either `GeneratedInvoiceDetail` (existing content extracted into its own component) or `ImportedInvoiceDetail`.

**Why separate component over conditional rendering:** The two types have fundamentally different data shapes, actions, and layout needs. Generated invoices have line items, HTML preview, email history, void/send actions. Imported invoices have editable metadata, extraction status, PDF-only preview, customer/contract linking. Mixing them with conditionals would create a tangled component.

**Alternative considered:** Single component with type-based conditionals. Rejected — the overlap is only the shell layout (header + two columns + payment matches). The content diverges too much.

### 3. Reuse existing layout pattern (two-column with sidebar)

Imported invoice detail uses the same two-column layout as generated invoices: main area (2/3) for PDF preview and metadata, sidebar (1/3) for relationships and payment matches. This keeps the UI consistent.

**Main column for imported invoices:**
- Metadata card: invoice number (editable), date (editable), amount (editable), currency, original filename, extraction status badge
- PDF preview: embedded iframe (same pattern as generated invoice PDF viewer, using `pdfUrl` directly)

**Sidebar:**
- Customer card: linked customer name (link to detail) or extracted name + "Link" button → `CustomerPickerDialog` with `customerMatchSuggestions`
- Contract card: linked contract (link to detail) or "Link" button (disabled without customer)
- Payment matches card: reuse same `PaymentMatchesSection` from generated invoice detail
- Receiver emails card: simple list of email addresses from `receiverEmails` JSON field

### 4. Inline metadata editing with save button

Editable fields (invoice number, date, amount) use inline editing — click to edit, save button to persist via `updateInvoice` mutation. No auto-save on blur (explicit save avoids accidental changes). Fields are only editable when extraction status is `extracted` or `confirmed` (not while extraction is in progress).

**Alternative considered:** Modal-based editing like the current list view approach. Rejected — the detail page has room for inline editing and it's a smoother UX than opening modals for individual fields.

### 5. Extraction actions in the header bar

Extraction-related actions (Extract, Re-extract, Confirm) appear as buttons in the header bar alongside Download PDF and Delete. The button shown depends on `extractionStatus`:
- `pending` → "Extract" button
- `extracting` → spinner/disabled state
- `extracted` → "Confirm" button
- `extraction_failed` → "Re-extract" button (+ error message in metadata card)
- `confirmed` → no extraction button needed

### 6. Invoice list links with type parameter

In `InvoiceList.tsx`, imported invoice rows get a clickable invoice number linking to `/invoices/:id?type=imported`. Generated invoices already link to `/invoices/:id`. The `UnifiedRow` type already has a `source` field (`'imported'` or `'generated'`) that determines which link format to use.

## Risks / Trade-offs

- **ID collision between generated and imported invoices** → The fallback detection (try generated first, then imported) handles this. With the `type` param, links from the list are unambiguous. Only manually typed URLs without `type` could hit the fallback path.
- **Duplicated payment match UI** → The payment match section is currently embedded in `InvoiceList.tsx` as `PaymentMatchModal`. Extracting it for reuse on the detail page requires some refactoring. Mitigation: extract the modal into a shared component used by both list and detail.
- **Imported invoice detail is read-heavy** → The `invoice(id)` query already returns all needed fields in one call. No additional queries needed except `customerMatchSuggestions` (only when linking a customer) and `findPaymentMatches` (only when adding payment matches).

## Open Questions

_(none)_
