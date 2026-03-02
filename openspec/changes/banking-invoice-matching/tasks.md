## 1. Backend: Suggested Matches Query

- [x] 1.1 Add `SuggestedMatchType` Strawberry type — extends `InvoiceSearchResultType` fields plus `amountDifference: Decimal`
- [x] 1.2 Add `SuggestedMatchesResultType` Strawberry type — `items: List[SuggestedMatchType]`, `customerName: str`, `customerId: int`
- [x] 1.3 Add `suggested_invoice_matches` query to `BankingQuery` — accepts `transactionId`, loads transaction with `select_related("counterparty__customer")`, returns `SuggestedMatchesResultType | None`
- [x] 1.4 Implement candidate fetching: query ImportedInvoice (status in confirmed/sent) and InvoiceRecord (exclude voided/paid) for the linked customer, filter `invoice_date <= transaction.entry_date` (or null date), exclude invoices already matched to this transaction
- [x] 1.5 Implement amount-proximity ranking: sort merged candidates by `abs(invoice_amount - abs(transaction.amount))`, cap at 20 results
- [x] 1.6 Add `customer_id` field to `TransactionMatchDetailsType` — resolve from `counterparty.customer_id` (null if no link), so frontend knows whether to fetch suggestions

## 2. Backend: Tests

- [x] 2.1 Write tests for `suggestedInvoiceMatches`: linked counterparty returns candidates, unlinked returns null, respects date filter, excludes paid, excludes already-matched, tenant isolation
- [x] 2.2 Write tests for amount ranking: exact match first, closest amount ranked higher, mixed imported/generated types
- [x] 2.3 Write test for `customer_id` field on `transactionMatchDetails` response

## 3. Frontend: Suggestions Section

- [x] 3.1 Add `SUGGESTED_INVOICE_MATCHES` GraphQL query to `TransactionMatchSheet.tsx`
- [x] 3.2 Fetch suggestions when sheet opens and `customerId` is present on match details response — skip query when null
- [x] 3.3 Build "Suggested matches" section above manual search — show customer name as header, list candidates with invoice number, amount, type badge, and amount difference indicator
- [x] 3.4 Highlight exact amount matches (green badge or styling)
- [x] 3.5 Wire click-to-match on suggestion rows — reuse existing `handleAddMatch` function, refetch both suggestions and match details after mutation
- [x] 3.6 Show empty state when all suggestions are already matched ("All invoices from this customer are matched")
- [x] 3.7 Hide suggestions section entirely when `customerId` is null (unlinked counterparty)

## 4. i18n

- [x] 4.1 Add translation keys to `en.json` and `de.json`: suggested matches header, exact match badge, empty state text, amount difference label
