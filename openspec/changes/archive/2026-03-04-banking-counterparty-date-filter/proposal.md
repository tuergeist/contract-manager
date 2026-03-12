## Why

The counterparty list on the Banking page sums all transactions regardless of time period. Users need to analyze counterparty balances for specific periods (e.g., a fiscal year, a quarter, or a custom range) but currently have no way to restrict the date range for the summation.

## What Changes

- Add date range filter (from/to) to the counterparty list on the Banking page
- Backend `counterparties` query gains `dateFrom` and `dateTo` parameters that restrict which transactions are included in the aggregation (totalDebit, totalCredit, transactionCount, firstDate, lastDate)
- Frontend adds date picker controls above the counterparty table
- The counterparty detail page also respects the selected date range when navigated to from the filtered list

## Capabilities

### New Capabilities

- `counterparty-date-filter`: Date range filtering for counterparty balance summation on the Banking page

### Modified Capabilities

_None_

## Impact

- `backend/apps/banking/schema.py` — Add `date_from` / `date_to` parameters to `counterparties()` resolver, apply to transaction aggregation
- `frontend/src/features/banking/BankingPage.tsx` — Add date picker controls, pass date range variables to query
- `frontend/src/features/banking/CounterpartyDetailPage.tsx` — Accept date range from navigation state/params
