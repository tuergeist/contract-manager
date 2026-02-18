## Why

The audit log page currently only filters by entity type and action type. Users need to filter by user (who made the change), time range, and entity text (search for a specific contract or customer name) to find relevant entries in a growing log.

## What Changes

- Add **user filter** dropdown to audit log page (backend already supports `userId` param, frontend doesn't expose it)
- Add **date range filter** (from/to date inputs) — requires new backend params `dateFrom`/`dateTo`
- Add **text search filter** on entity name (`entityRepr`) — requires new backend param `search`
- Reset pagination when filters change

## Capabilities

### New Capabilities

_(none — this extends the existing audit-log-ui capability)_

### Modified Capabilities

- `audit-log-ui`: Add user filter, date range filter, and text search to the audit log filtering requirement

## Impact

- **Backend**: `apps/audit/schema.py` — add `date_from`, `date_to`, and `search` parameters to `audit_logs` query
- **Frontend**: `features/audit/AuditLogPage.tsx` — add 3 new filter controls, pass new variables to query
- **Frontend**: `locales/en.json`, `locales/de.json` — new translation keys for filter labels
