## 1. Backend - GraphQL Schema

- [x] 1.1 Add `MatchedInvoiceType` strawberry type with fields: id, invoice_number, is_paid, pdf_url
- [x] 1.2 Add optional `matched_invoice` field to `BillingEvent` type

## 2. Backend - Invoice Matching Logic

- [x] 2.1 Create helper function to find matching invoice for a billing event (contract_id + date within ±15 days)
- [x] 2.2 Integrate invoice matching into `billing_schedule` query resolver
- [x] 2.3 Handle multiple matches by selecting closest date

## 3. Frontend - GraphQL Query

- [x] 3.1 Update `BILLING_SCHEDULE_QUERY` to include matchedInvoice fields (id, invoiceNumber, isPaid, pdfUrl)

## 4. Frontend - ForecastTab UI

- [x] 4.1 Add "Invoice" column header to forecast table
- [x] 4.2 Display invoice number as link to PDF (opens in new tab)
- [x] 4.3 Display paid/unpaid badge next to invoice number
- [x] 4.4 Show dash or empty cell when no matched invoice

## 5. Translations

- [x] 5.1 Add translation keys for "Invoice" column header and paid/unpaid badges (if not already present)
