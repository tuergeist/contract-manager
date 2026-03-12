## 1. Backend: GraphQL Queries

- [x] 1.1 Add `transactionMatchDetails` query to `backend/apps/banking/schema.py` — accepts `transactionId`, returns transaction fields, all invoice matches (with invoice number, amount, customer name, type, match type, confidence, matched_at), `totalMatched`, and `difference`
- [x] 1.2 Add `TransactionMatchDetailsType` and `MatchDetailType` Strawberry types for the query response
- [x] 1.3 Add `searchInvoicesForMatching` query to `backend/apps/invoices/schema.py` — accepts `search` (text), `unmatchedOnly` (bool), `limit` (int, default 20); searches both ImportedInvoice and InvoiceRecord by invoice_number; returns unified result list with invoice number, amount, customer name, type (imported/generated), status
- [x] 1.4 Add `InvoiceSearchResultType` Strawberry type for the search response
- [x] 1.5 Write backend tests for `transactionMatchDetails` (single match, multiple matches, total calculation, tenant isolation)
- [x] 1.6 Write backend tests for `searchInvoicesForMatching` (text search, unmatched filter, pagination, mixed results)

## 2. Frontend: TransactionMatchSheet Component

- [x] 2.1 Create `TransactionMatchSheet.tsx` in `frontend/src/features/banking/` — Sheet component with `side="right"`, accepts `transactionId` and `open`/`onOpenChange` props
- [x] 2.2 Add GraphQL query `TRANSACTION_MATCH_DETAILS` and wire it to the sheet (fetches on open / when transactionId changes)
- [x] 2.3 Build transaction summary header section — display entry date, value date, amount, currency, counterparty, booking text, reference, account name
- [x] 2.4 Build matched invoices list — each row shows invoice number (linked), type badge, customer name, amount, match type, remove button
- [x] 2.5 Build difference banner — calculate and color-code: green (matched/within rounding), yellow (underpaid), orange (overbooking >3%)
- [x] 2.6 Wire remove button to `deletePaymentMatch` mutation, refetch `transactionMatchDetails` on success

## 3. Frontend: Invoice Search Panel

- [x] 3.1 Add GraphQL query `SEARCH_INVOICES_FOR_MATCHING` in the sheet component
- [x] 3.2 Build invoice search UI — text input for invoice number, unmatched-only toggle
- [x] 3.3 Build search results list — each row shows invoice number, customer, amount, type badge, status; clickable to add match
- [x] 3.4 Wire click-to-match: call `createPaymentMatch` or `createPaymentMatchForRecord` based on invoice type, refetch match details on success
- [x] 3.5 Handle duplicate match error from mutation (show toast)

## 4. Integration: Banking Page

- [x] 4.1 Add match action button to transaction rows in `BankingPage.tsx` — icon button with matched/unmatched visual state
- [x] 4.2 Add `selectedTransactionId` state and render `TransactionMatchSheet` in BankingPage
- [x] 4.3 Refetch transaction list after sheet closes (to update matched indicator)
- [x] 4.4 Add match action button to transaction rows in `CounterpartyDetailPage.tsx` (same pattern)

## 5. i18n and Polish

- [x] 5.1 Add translation keys to `en.json` and `de.json` for: sheet title, matched invoices header, difference labels, overbooking warning, search placeholder, empty state hint, remove confirmation
- [x] 5.2 Use `formatCurrency` from `@/lib/utils` for all amount displays (German locale)
