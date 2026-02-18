## 1. Backend — New Query Parameters

- [x] 1.1 Add `date_from: Optional[datetime]`, `date_to: Optional[datetime]`, and `search: Optional[str]` parameters to `audit_logs` resolver in `apps/audit/schema.py`
- [x] 1.2 Apply `timestamp__gte` / `timestamp__lte` filters for date range
- [x] 1.3 Apply `entity_repr__icontains` filter for search text
- [x] 1.4 Write backend tests for the new filter parameters

## 2. Frontend — GraphQL Query Update

- [x] 2.1 Add `userId`, `dateFrom`, `dateTo`, `search` variables to the `AUDIT_LOGS_QUERY` in `AuditLogPage.tsx`

## 3. Frontend — Filter Controls

- [x] 3.1 Add user filter dropdown (fetch users list, pass `userId` to query)
- [x] 3.2 Add date-from and date-to `<input type="date">` fields
- [x] 3.3 Add search text input with 300ms debounce
- [x] 3.4 Ensure all filter changes reset pagination (set `after: null`)

## 4. Translations

- [x] 4.1 Add translation keys for new filter labels in `en.json` and `de.json` (search placeholder, user filter label, date from/to labels)

## 5. Verification

- [x] 5.1 Run `npx tsc --noEmit` — no type errors
- [x] 5.2 Run `make test-back` — backend tests pass
- [x] 5.3 Manual test: filter by user, date range, search text, and combinations
