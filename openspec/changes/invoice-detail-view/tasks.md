## 1. Refactor InvoiceDetail as Router

- [x] 1.1 Extract existing generated invoice detail content from `InvoiceDetail.tsx` into a `GeneratedInvoiceDetail` component (same file)
- [x] 1.2 Make `InvoiceDetail` a thin router: read `type` query param, render `GeneratedInvoiceDetail` or `ImportedInvoiceDetail`
- [x] 1.3 Add auto-fallback: if no `type` param and generated invoice query returns not-found, try imported invoice query

## 2. Imported Invoice Detail — Shell & Data

- [x] 2.1 Create `ImportedInvoiceDetail` component with two-column layout (2/3 main + 1/3 sidebar), loading the `invoice(id)` query
- [x] 2.2 Add header bar with invoice number title, extraction status badge, and action buttons placeholder

## 3. Imported Invoice Detail — Main Column

- [x] 3.1 Add metadata card: invoice number, date, amount/currency, original filename, file size, created by, created at, extraction status
- [x] 3.2 Add inline editing for invoice number, date, and amount fields with explicit save button (calls `updateInvoice` mutation)
- [x] 3.3 Add PDF preview using iframe (from `pdfUrl`), with placeholder for `uploadStatus = 'pending'`
- [x] 3.4 Show extraction error message when `extractionStatus = 'extraction_failed'`

## 4. Imported Invoice Detail — Sidebar

- [x] 4.1 Add customer card: linked customer name as link to `/customers/:id`, or extracted `customerName` with "Link Customer" button opening `CustomerPickerDialog` with `customerMatchSuggestions` query
- [x] 4.2 Add unlink customer action (calls `unlinkCustomerFromInvoice`, disabled when contract is linked)
- [x] 4.3 Add contract card: linked contract name as link to `/contracts/:id`, or "Link Contract" button (disabled without customer), calls `assignInvoiceContract`
- [x] 4.4 Add unlink contract action (calls `assignInvoiceContract` with null contractId)
- [x] 4.5 Add payment matches section: display existing matches (date, amount, counterparty, type, confidence, matched-by); reuse or extract `PaymentMatchModal` from `InvoiceList.tsx` for add/remove
- [x] 4.6 Add receiver emails card: display `receiverEmails` list (hide section when empty)

## 5. Imported Invoice Detail — Actions

- [x] 5.1 Add "Extract" button when `extractionStatus = 'pending'` (calls `extractInvoice`)
- [x] 5.2 Add "Re-extract" button when `extractionStatus = 'extraction_failed'` (calls `reExtractInvoice`)
- [x] 5.3 Add "Confirm" button when `extractionStatus = 'extracted'` (calls `confirmInvoice`)
- [x] 5.4 Add "Download PDF" button (opens `pdfUrl` in new tab)
- [x] 5.5 Add "Delete" button with confirmation dialog (calls `deleteInvoice`, navigates to `/invoices` on success); respect `invoices.generate` permission

## 6. Invoice List — Link Imported Invoices

- [x] 6.1 Make imported invoice rows in `InvoiceList.tsx` link invoice number to `/invoices/:id?type=imported`
- [x] 6.2 Verify generated invoice rows already link to `/invoices/:id` (existing behavior)

## 7. Extract Shared Payment Match Modal

- [ ] 7.1 Extract `PaymentMatchModal` from `InvoiceList.tsx` into a shared component that accepts either `invoiceId` (imported) or `invoiceRecordId` (generated) and calls the appropriate mutations
- [ ] 7.2 Update `InvoiceList.tsx` to use the extracted shared component
- [ ] 7.3 Use the shared component in both `ImportedInvoiceDetail` and `GeneratedInvoiceDetail`

## 8. Translations

- [x] 8.1 Add EN/DE translations for imported invoice detail labels (extraction status values, action buttons, section headers, metadata field labels, placeholder texts)

## 9. Tests

- [x] 9.1 Test: `InvoiceDetail` routes to generated view by default
- [x] 9.2 Test: `InvoiceDetail` routes to imported view when `?type=imported`
- [x] 9.3 Test: Imported invoice metadata editing calls `updateInvoice` mutation
- [x] 9.4 Test: Extraction actions shown based on `extractionStatus`
- [x] 9.5 Test: Customer link/unlink actions work on imported invoice detail
