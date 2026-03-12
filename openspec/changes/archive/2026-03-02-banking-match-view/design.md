## Context

Payment matching currently works invoice-first: from an invoice detail page, users open `PaymentMatchModal` to find and link a bank transaction. The banking page shows a single `matchedInvoice` icon per transaction (first match only). There is no way to see all matches for a transaction, compare totals, or detect underpayments/overpayments.

The `InvoicePaymentMatch` model already supports N:M relationships (multiple matches per transaction via `related_name="invoice_matches"`, multiple matches per invoice via `related_name="payment_matches"`). The backend prefetches `invoice_matches` on the transaction list query but only surfaces the first match.

## Goals / Non-Goals

**Goals:**
- Transaction-centric reconciliation: select a transaction, see all its matched invoices with a running total
- Support 1:1 (one transaction, one invoice), 1:N (one transaction, multiple invoices), and N:1 (multiple transactions, one invoice) matching
- Show difference between transaction amount and sum of matched invoice amounts
- Warn on overbooking (matched invoices exceed transaction amount beyond tolerance)
- Allow adding/removing invoice matches inline without leaving the view
- Accessible from the transaction list via a dedicated action button

**Non-Goals:**
- Automatic batch reconciliation (auto-match all unmatched transactions)
- Split transactions (dividing one transaction into sub-amounts)
- New database models or migrations
- Changes to the existing `PaymentMatchModal` (it continues to work from the invoice side)

## Decisions

### 1. Slide-over panel vs. dedicated page

**Decision:** Slide-over panel (Sheet component) opening from the right side of the banking page.

**Rationale:** The user stays in the transaction list context, can close the panel and pick another transaction quickly. A dedicated route would break the flow of working through multiple transactions. The Shadcn `Sheet` component with `side="right"` provides this pattern.

**Alternative considered:** Full page at `/banking/match/:transactionId` — rejected because reconciliation is a rapid workflow where users process many transactions sequentially.

### 2. Backend: new query vs. extending existing transaction query

**Decision:** Add a new `transactionMatchDetails` query that returns a single transaction with all its invoice matches, including invoice details (number, amount, customer, status, type).

**Rationale:** The existing `bankTransactions` list query prefetches matches but only exposes the first one. Extending the list query to return all matches per transaction would bloat the list response. A dedicated detail query keeps the list lean and gives the match view exactly what it needs.

**Shape:**
```graphql
transactionMatchDetails(transactionId: ID!) {
  transaction { id, entryDate, valueDate, amount, currency, counterparty, bookingText, reference, accountName }
  matches [{ id, invoiceId, invoiceRecordId, invoiceNumber, invoiceAmount, customerName, matchType, confidence, matchedAt }]
  totalMatched   # sum of matched invoice amounts
  difference     # transaction.amount - totalMatched
}
```

### 3. Invoice search within the panel

**Decision:** Reuse the existing `searchTransactions`-style approach but for invoices — add a `searchInvoicesForMatching` query that finds imported invoices and invoice records by number, customer, or amount range.

**Rationale:** The existing `PaymentMatchModal` has `findPaymentMatches` (auto-suggest) and `searchTransactions` (manual search). The match view flips the direction: given a transaction, search for invoices. A dedicated query avoids overloading existing ones.

**Filters:** invoice number (text search), customer name, amount range, date range, unmatched-only toggle.

### 4. Overbooking guard

**Decision:** Client-side calculation with visual warning. No backend enforcement.

**Rationale:** The tolerance threshold (default 3%) is a UX hint, not a business rule. Some legitimate scenarios exceed it (e.g., advance payments, credits). The backend already allows creating any match via `createPaymentMatch`. The frontend shows:
- Green: difference = 0 (or within 0.01 rounding)
- Yellow: difference > 0 (underpaid / unmatched remainder)
- Orange warning: difference < 0 and abs(difference) > 3% of transaction amount (overbooking)
- Info text showing the numeric difference

### 5. Reuse existing mutations

**Decision:** Reuse `createPaymentMatch`, `createPaymentMatchForRecord`, and `deletePaymentMatch` mutations as-is.

**Rationale:** These mutations handle all validation, duplicate checks, and status transitions (invoice → paid). No changes needed. The match view simply calls them and refetches `transactionMatchDetails`.

### 6. Component structure

```
TransactionMatchSheet (Sheet wrapper)
├── TransactionSummary (left/top: transaction details + running balance)
├── MatchedInvoicesList (matched invoices with amounts, running total, remove button)
│   └── MatchedInvoiceRow (per match: invoice info, amount, cumulative total)
├── MatchDifferenceBanner (difference display with color coding)
└── InvoiceSearch (search panel to find and add invoices)
    ├── SearchFilters (number, customer, amount, unmatched-only)
    └── InvoiceSearchResults (clickable rows to create match)
```

## Risks / Trade-offs

**[Stale match data after concurrent edits]** → Panel refetches `transactionMatchDetails` after every add/remove. No optimistic updates for match operations since they're infrequent.

**[Large invoice search results]** → Paginate with limit 20, add filters to narrow down. Invoice number search is the most common path and typically returns few results.

**[Multiple browser tabs editing same transaction]** → Acceptable risk for internal tool. Last write wins (existing behavior for all mutations).

**[3% overbooking threshold is arbitrary]** → Hardcoded initially. Can be made configurable in settings later if needed. The warning is non-blocking — users can still create the match.
