## Context

The TransactionMatchSheet already supports viewing matched invoices and manually searching for invoices to match. The Counterparty model has an optional `customer` ForeignKey. When a counterparty is linked to a customer, we know whose invoices to suggest — but today the user must manually type the invoice number to find them.

The `transactionMatchDetails` query already loads the transaction with `select_related("counterparty")`, so the customer link is available. ImportedInvoice and InvoiceRecord both have customer ForeignKeys and amount/date fields needed for ranking.

## Goals / Non-Goals

**Goals:**
- Auto-suggest unpaid invoices from the linked customer when the match sheet opens
- Rank suggestions by amount proximity so the best match is first
- One-click matching from suggestions (same flow as manual search results)
- Zero extra clicks for the common case (counterparty linked, obvious invoice match)

**Non-Goals:**
- Auto-matching without user confirmation (always requires a click)
- Fuzzy customer name matching for unlinked counterparties (that's a separate feature)
- Multi-transaction batch matching
- Changing the counterparty-customer linking flow

## Decisions

### 1. New query `suggestedInvoiceMatches` on BankingQuery

Add the suggestions query to `BankingQuery` in `backend/apps/banking/schema.py` rather than the invoices schema, since it takes a `transactionId` and needs transaction context. The resolver:

1. Loads the transaction with `select_related("counterparty__customer")`
2. Returns empty list if `counterparty.customer` is null
3. Queries ImportedInvoice (status in confirmed, sent) and InvoiceRecord (excluding voided, paid) for that customer
4. Filters to `invoice_date <= transaction.entry_date` (or null invoice_date)
5. Excludes invoices already matched to this transaction (via existing InvoicePaymentMatch)
6. Sorts by `abs(invoice_amount - abs(transaction.amount))` in Python after fetching both querysets

**Why not extend `transactionMatchDetails`?** Suggestions are a separate concern. Keeping them in a dedicated query means the match details query stays fast (no extra invoice lookups), and the frontend can fetch suggestions lazily or skip them for unlinked counterparties.

### 2. Reuse `InvoiceSearchResultType` for candidates

The suggestion response reuses `InvoiceSearchResultType` from the invoices schema (same fields: id, invoiceNumber, amount, customerName, invoiceType, status, invoiceDate, isPaid) plus an `amountDifference` field. Wrap in a new `SuggestedMatchesType` with `items` list and `customerName` (for the section header).

**Alternative considered:** Creating a completely new type. Rejected because the fields are identical and reusing the type keeps the frontend simple — same rendering logic for suggestions and search results.

### 3. Frontend: suggestions section in TransactionMatchSheet

Add a `SUGGESTED_INVOICE_MATCHES` query that fires when the sheet opens (alongside the existing `TRANSACTION_MATCH_DETAILS` query). Show results above the search panel in a "Suggested matches" section with the customer name as header.

Each suggestion row reuses the same rendering as search results, plus an amount difference indicator. Clicking a suggestion calls the same `handleAddMatch` function. After adding, refetch both queries to update the list.

When `counterparty.customer` is null (no link), skip the suggestions query entirely — check via a `customerId` field added to `TransactionMatchDetailsType`.

### 4. Amount ranking in Python, not SQL

Both ImportedInvoice and InvoiceRecord use different amount fields (`total_amount` vs `total_gross`). Computing `abs(amount - txn_amount)` across two merged querysets is simpler in Python. The candidate set is small (one customer's unpaid invoices, typically <20), so this has no performance concern.

## Risks / Trade-offs

- **[Small candidate set assumption]** → Ranking in Python works for typical invoice volumes per customer (<50). If a customer has hundreds of unpaid invoices, we'd need pagination. Mitigation: cap at 20 candidates.
- **[Extra query on sheet open]** → One additional GraphQL query per sheet open for linked counterparties. Mitigation: the query is simple (two filtered querysets on indexed fields) and only fires when counterparty is linked.
- **[Stale suggestions after match]** → After adding a match, the suggestion should disappear. Mitigation: refetch the suggestions query after mutation, same pattern as the match details refetch.
