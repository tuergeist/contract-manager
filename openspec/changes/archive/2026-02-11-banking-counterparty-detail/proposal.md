## Why

The banking module stores thousands of transactions but provides no way to understand costs at the creditor level. To get a picture of what we spend per supplier (e.g., "BG Verkehr", "Piepenbrock", "SoftwareOne"), users currently have to search manually for each name. An auto-generated creditor list with aggregated totals and a drill-down detail view gives immediate visibility into the company's cost structure.

## What Changes

- Add a backend query that aggregates transactions by unique counterparty name, returning each creditor's total amount, transaction count, and date range
- Make counterparty names in the transaction table clickable, navigating to a creditor detail view
- Add a new creditor list view (tab or section on the banking page) showing all creditors with totals
- Add a creditor detail view showing all transactions with that specific counterparty, reusing the existing transaction table with filters

## Capabilities

### New Capabilities
- `counterparty-list`: Auto-generated list of all unique counterparties with aggregated totals (total spent/received, transaction count, last transaction date), sortable and searchable
- `counterparty-detail`: Detail view for a single counterparty showing all their transactions in a filtered table, accessible by clicking a counterparty name anywhere in the banking UI

### Modified Capabilities
- `bank-transactions`: Counterparty name in the transaction table becomes a clickable link navigating to the counterparty detail view

## Impact

- **Backend**: New GraphQL query `bankCounterparties` with aggregation; minor change to transaction query (no schema changes needed, just frontend linking)
- **Frontend**: New components/views for counterparty list and detail; modification to BankingPage transaction table to make counterparty names clickable
- **Routing**: New route `/banking/counterparty/:name` or similar for the detail view
