## Why

Users lose their sorting, filter selections, search terms, and pagination position every time they navigate away from a page and come back. This forces repeated re-configuration of views, especially on pages like the invoice list and banking page where users frequently apply filters. Three list pages (CustomerList, ProductList, ContractList) already persist sort preferences via a `usePersistedState` hook backed by localStorage — the rest of the app should follow the same pattern.

## What Changes

- Extend usage of the existing `usePersistedState` hook to all list/table pages that have user-configurable view state
- Persist sort column + sort direction on pages that don't already do so (InvoiceList, BankingPage, CounterpartyDetailPage, AuditLogPage, ProjectList, CustomerDetail contracts table)
- Persist filter selections (status filters, source filters, payment status, active tab on banking page)
- Do NOT persist: search terms (stale searches are confusing), pagination position (data may have changed), modal/dialog state, date range filters (quickly become stale)

## Capabilities

### New Capabilities
- `view-preference-persistence`: Extend `usePersistedState` usage across all list pages to remember sort preferences and key filter selections in localStorage

### Modified Capabilities

## Impact

- **Frontend only** — no backend changes needed
- Files to modify: `InvoiceList.tsx`, `BankingPage.tsx`, `CounterpartyDetailPage.tsx`, `AuditLogPage.tsx`, `ProjectList.tsx`, `CustomerDetail.tsx`
- Existing `usePersistedState` hook is reused as-is
- localStorage keys should follow a consistent naming convention (e.g., `cm:<page>:<field>`)
