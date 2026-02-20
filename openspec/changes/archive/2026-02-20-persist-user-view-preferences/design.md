## Context

Three list pages (CustomerList, ProductList, ContractList) already use a `usePersistedState` hook that wraps `useState` with localStorage read/write. The hook lives at `frontend/src/lib/usePersistedState.ts` and has tests. It uses a simple key-value approach: `localStorage.getItem(key)` on init, `localStorage.setItem(key, JSON.stringify(state))` on change.

Current localStorage keys used by the three pages have no consistent prefix — they are bare strings like `"customerList.sortBy"`. The remaining pages (InvoiceList, BankingPage, CounterpartyDetailPage, AuditLogPage, ProjectList, CustomerDetail) use plain `useState` for all view state, meaning everything resets on navigation.

## Goals / Non-Goals

**Goals:**
- Persist sort column and sort direction on all list/table pages
- Persist key filter selections that represent a user's "default view" (status filter, source filter, active tab)
- Use the existing `usePersistedState` hook — no new abstractions needed
- Adopt a consistent key naming convention across all pages

**Non-Goals:**
- Persisting search terms (go stale, confusing when returning to a page)
- Persisting pagination position (data changes, page may not exist)
- Persisting date range filters (stale dates cause empty results)
- Persisting modal/dialog state
- Server-side preference storage (localStorage is sufficient for this UX improvement)
- Migrating existing keys to the new naming convention (not worth the complexity)

## Decisions

### 1. Reuse `usePersistedState` as-is

The existing hook is simple, tested, and works. No wrapper, no abstraction layer. Just swap `useState` → `usePersistedState` for the relevant state variables.

**Alternative considered:** A `useViewPreferences` hook that bundles all page state into one object. Rejected — it couples unrelated state together and makes partial updates awkward.

### 2. Key naming convention: `cm:<page>:<field>`

New keys will follow `cm:<page>:<field>`, e.g. `cm:invoiceList:sortField`, `cm:banking:activeTab`. Existing keys on CustomerList/ProductList/ContractList won't be renamed — not worth a migration for cosmetic consistency.

### 3. What to persist per page

| Page | Persist | Skip |
|------|---------|------|
| InvoiceList | sortField, sortOrder, sourceFilter, paymentStatus | search, page, uploadStatus |
| BankingPage | activeTab, sortBy, sortOrder, cpSortBy, cpSortOrder | search, dates, amounts, page, direction, unmatchedCredits |
| CounterpartyDetailPage | sortBy, sortOrder | search, dates, amounts, page |
| AuditLogPage | entityTypeFilter, actionFilter | search, dates, userFilter |
| ProjectList | statusFilter | (no sort/page state) |
| CustomerDetail | activeTab, contract sort column/order | modal state |

**Rationale:** Persist state that represents a user's preferred "lens" on data. Skip state that is inherently temporal (search queries, date ranges, pagination).

## Risks / Trade-offs

- **Stale filter values after data changes** → Filters like `sourceFilter: "GENERATED"` are enum-based and stable. Status filters use known values. Low risk.
- **localStorage quota** → Each key is ~50 bytes. Adding ~20 keys is negligible.
- **User confusion if a filter is "stuck"** → Users may not realize a filter is persisted. Mitigated by the fact that filters are always visible in the UI — the user sees what's active.
