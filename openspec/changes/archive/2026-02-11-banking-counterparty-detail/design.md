## Context

The banking module already stores transactions with `counterparty_name` as a free-text field parsed from MT940 `:86:` subfield `?32`/`?33`. There is no separate counterparty/creditor model — names come directly from bank data and may have slight variations (e.g., "SoftwareOne Deutschland GmbH" vs "SoftwareOne Deutschland Gmb"). The existing `BankingPage.tsx` has a transaction table with filters, sorting, and pagination. Counterparty names appear in a truncated column and are shown in full only when a row is expanded.

## Goals / Non-Goals

**Goals:**
- Auto-generate a counterparty list from existing transaction data (no manual data entry)
- Show aggregated metrics per counterparty (total amount, count, date range)
- Provide a detail view for a single counterparty with all their transactions
- Make counterparty names clickable throughout the banking UI

**Non-Goals:**
- Counterparty name normalization/deduplication (e.g., merging "SoftwareOne GmbH" with "SoftwareOne Deutschland GmbH") — future enhancement
- Separate counterparty model/table — derive everything from transactions at query time
- Creditor master data management (addresses, tax IDs, etc.)

## Decisions

### 1. Query-time aggregation, no separate model
Aggregate counterparties from `BankTransaction.counterparty_name` using Django ORM `values().annotate()`. No new database table needed.

**Rationale**: Counterparty data comes from bank statements and is inherently inconsistent. A derived view stays automatically in sync with imports. A separate model would require sync logic and offer little benefit without name normalization.

### 2. URL-based counterparty identification
Use URL-encoded counterparty name in the route: `/banking/counterparty/:name`. The detail view passes the name as a filter to the existing `bankTransactions` query.

**Rationale**: Since there's no counterparty ID (no model), the name itself is the identifier. URL encoding handles special characters. This avoids creating synthetic IDs.

### 3. Reuse existing transaction query for detail view
The counterparty detail view reuses the existing `bankTransactions` GraphQL query with a new `counterpartyName` exact-match filter (distinct from the existing `search` which does partial match).

**Rationale**: Avoids duplicating transaction query logic. The detail view is just a pre-filtered transaction table.

### 4. Counterparty list as a new section/tab on the banking page
Add a "Counterparties" tab or section to the existing banking page rather than a separate top-level route.

**Rationale**: Keeps banking as a cohesive feature. The counterparty list is a lens on transaction data, not a separate entity.

## Risks / Trade-offs

- **[Performance]** Aggregating across all transactions for the counterparty list could be slow with large datasets → Add DB index on `counterparty_name` (already exists), use pagination, and consider caching if needed
- **[Name inconsistency]** Same creditor may appear under slightly different names → Accepted for now; future enhancement could add name grouping/aliasing
- **[URL encoding]** Special characters in counterparty names (umlauts, ampersands, slashes) → Use `encodeURIComponent`/`decodeURIComponent` consistently
