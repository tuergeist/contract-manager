## Context

The audit log page (`/audit-log`) currently filters by entity type and action type via dropdowns. The backend `audit_logs` query already accepts `user_id` but the frontend doesn't expose it. Date range and text search are not supported at all.

The backend query lives in `apps/audit/schema.py` (cursor-based pagination with `AuditLogConnection`). The frontend page is `features/audit/AuditLogPage.tsx` with its own inline GraphQL query (separate from the `useAuditLogs` hook used on detail pages).

## Goals / Non-Goals

**Goals:**
- Users can filter audit log by who made the change (user dropdown)
- Users can filter by date range (from/to date inputs)
- Users can search by entity name (text input matching `entity_repr`)
- Filters reset pagination to first page

**Non-Goals:**
- Full-text search across change details (old/new values)
- Saved filter presets
- Changes to the `useAuditLogs` hook (detail page activity tabs)

## Decisions

### Backend: Add 3 new query parameters

Add `date_from: Optional[datetime]`, `date_to: Optional[datetime]`, and `search: Optional[str]` to the existing `audit_logs` resolver.

- `date_from`/`date_to`: Filter with `timestamp__gte` / `timestamp__lte`
- `search`: Filter with `entity_repr__icontains`

This keeps the approach consistent with the existing filter parameters — simple Django ORM filters, no new indexes needed. The `entity_repr` field is already stored as a string on every audit log entry.

### Frontend: Add filter controls inline with existing filters

Add to the existing filter bar in `AuditLogPage.tsx`:
1. **User dropdown** — fetch distinct users from a lightweight query (reuse tenant users list). Pass `userId` to the query.
2. **Date from / Date to** — native `<input type="date">` fields. Simple, no library needed.
3. **Search input** — text input with debounce (300ms). Pass `search` to the query.

All filters pass as GraphQL variables. The query already refetches on variable change via Apollo's `cache-and-network` policy.

### User list: Use existing tenant users

The settings page already fetches users. Add `userId` + `userName` extraction from audit log entries as a simpler alternative — but a dedicated users query is cleaner. Use the existing `users` query from the settings/team section to populate the dropdown.

## Risks / Trade-offs

- **`icontains` on `entity_repr`** — No index, but audit logs are tenant-scoped and the table size is manageable. If performance becomes an issue later, a `GIN` trigram index can be added.
- **Debounced search** — 300ms delay is a UX trade-off to avoid excessive queries. Acceptable for this use case.
