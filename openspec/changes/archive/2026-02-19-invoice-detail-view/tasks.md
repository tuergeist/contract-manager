## 1. Backend: Single Invoice Record Query

- [x] 1.1 Add `invoice_record(id: Int!) -> InvoiceRecordType | None` query to `InvoiceQuery` in `backend/apps/invoices/schema.py` — fetch by id filtered to user's tenant, prefetch payment_matches, return via `_convert_record` or null
- [x] 1.2 Add test for `invoice_record` query: returns record for valid id, returns null for missing id, returns null for other tenant's record

## 2. Frontend: Invoice Detail Page

- [x] 2.1 Create `INVOICE_RECORD_QUERY` GraphQL query in new `InvoiceDetail.tsx` — fetch single record with all fields (id, invoiceNumber, billingDate, invoiceDate, periodStart, periodEnd, totalNet, taxRate, taxAmount, totalGross, status, generatedAt, lineItemsSnapshot, invoiceText, pdfUrl, isPaid, paymentMatches, emailSentAt, emailSentTo, emailMessageId, contractId, contractName, customerId, customerName)
- [x] 2.2 Create `AUDIT_LOGS_QUERY` for fetching audit history with entityType "invoice_record" and entityId
- [x] 2.3 Build invoice metadata header section — invoice number, status badge, dates (billing, invoice, period), amounts (net, tax, gross), tax rate, generated-at timestamp
- [x] 2.4 Build customer/contract links section — customer name linking to `/customers/:id`, contract name linking to `/contracts/:id`, show plain text when FK is null
- [x] 2.5 Build line items table — render lineItemsSnapshot as a table with product name, description, quantity, unit price, amount
- [x] 2.6 Build content preview section — iframe with PDF embed when pdfUrl exists, fallback to `/api/invoices/preview-html/?year=Y&month=M&contract_id=C` for HTML preview
- [x] 2.7 Build payment matches section — list each match with transaction date, amount, counterparty, match type, confidence, matched-by user; show empty state when no matches
- [x] 2.8 Build email history section — show sent timestamp, recipients list, message ID when emailSentAt is set; show "Not sent" when null
- [x] 2.9 Build audit timeline section — query audit logs, display timeline of changes with timestamp, user, action, and changed fields; show empty state
- [x] 2.10 Add action buttons in header — "Send Email" (visible when finalized + PDF + customer billing emails), "Void" with confirmation dialog (visible when finalized), "Download PDF" link (visible when pdfUrl exists)

## 3. Frontend: Routing and Navigation

- [x] 3.1 Add `/invoices/:id` route in `App.tsx` pointing to `InvoiceDetail` component
- [x] 3.2 Add translations for invoice detail page labels in `en.json` and `de.json` (page title, section headers, action buttons, empty states)

## 4. Frontend: Link From Existing Pages

- [x] 4.1 On `InvoiceExportPage.tsx` — wrap generated invoice numbers (records with id) in `<Link to={/invoices/${id}}>`
- [x] 4.2 On `ContractDetail.tsx` invoices tab — wrap generated invoice numbers in `<Link to={/invoices/${id}}>`

## 5. Mutations and Actions

- [x] 5.1 Wire "Send Email" button to existing `send_invoice_email` mutation, show success/error toast, refetch record after send
- [x] 5.2 Wire "Void" button to existing `void_invoice` mutation with confirmation dialog, refetch record after void

## 6. Verification

- [x] 6.1 Run `make test-back` — all backend tests pass
- [x] 6.2 Run `npx tsc --noEmit` — no frontend type errors
- [ ] 6.3 Manual verification: navigate to invoice detail from export page and contract detail, confirm all sections render correctly
