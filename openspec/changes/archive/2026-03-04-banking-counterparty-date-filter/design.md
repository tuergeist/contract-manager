## Context

The Banking page has two tabs: Transactions and Counterparties. The Transactions tab already has date range filtering (`dateFrom`/`dateTo`). The Counterparties tab lists all counterparties with aggregated stats (totalDebit, totalCredit, transactionCount) computed across all transactions via Django ORM annotations. There is no way to restrict the date range for these aggregations.

## Goals / Non-Goals

**Goals:**
- Allow users to filter the counterparty list by date range, restricting which transactions are included in balance summation
- Pass the selected date range to the counterparty detail page so it shows consistent data

**Non-Goals:**
- Changing the counterparty detail page's own internal filters (it already has date filtering for its transaction table)
- Adding quick-select presets (e.g., "This year", "Last quarter") — can be added later

## Decisions

### 1. Backend: Add date params to existing `counterparties` query

Add optional `date_from: date | None` and `date_to: date | None` parameters to the `counterparties()` resolver. When provided, apply them as filters on the transaction annotations:

```python
txn_filter = Q()
if date_from:
    txn_filter &= Q(transactions__entry_date__gte=date_from)
if date_to:
    txn_filter &= Q(transactions__entry_date__lte=date_to)
```

Then use this filter in all annotations (total_debit, total_credit, txn_count, first_date, last_date, abs_total). This keeps it backward-compatible — without parameters, behavior is unchanged.

**Alternative considered:** Separate query for filtered counterparties. Rejected because adding optional params is simpler and avoids duplication.

### 2. Frontend: Dedicated date pickers for the counterparties tab

Add `cpDateFrom` and `cpDateTo` state variables (separate from the transactions tab's existing `dateFrom`/`dateTo`). Place two date inputs above the counterparty table, matching the same layout pattern used in the transactions filter row.

Pass these as variables to `BANK_COUNTERPARTIES` query. Reset to page 1 when date filters change.

### 3. Passing date range to counterparty detail

When navigating to a counterparty detail page from the filtered list, pass `dateFrom` and `dateTo` as URL search params (e.g., `/banking/counterparties/123?dateFrom=2026-01-01&dateTo=2026-03-31`). The detail page reads these and passes them to its own query. This is the same pattern used for other filter pass-through in the app.

## Risks / Trade-offs

- **Performance**: The annotation filters add `WHERE` clauses to the subqueries. Since `entry_date` is already indexed (used by transactions query), impact should be minimal.
- **UX consistency**: The transactions tab and counterparties tab have independent date filters. This is intentional — they serve different purposes and users may want different ranges.

## Files Changed

| File | Change |
|------|--------|
| `backend/apps/banking/schema.py` | Add `date_from`, `date_to` params to `counterparties()`, apply to annotations |
| `frontend/src/features/banking/BankingPage.tsx` | Add date picker state/UI for counterparties tab, pass to query |
| `frontend/src/features/banking/CounterpartyDetailPage.tsx` | Read date range from URL params, pass to detail query |
