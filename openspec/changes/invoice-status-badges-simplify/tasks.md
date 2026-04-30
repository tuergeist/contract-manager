## 1. Mapping Utility

- [ ] 1.1 Create `frontend/src/features/incoming-invoices/statusMapping.ts` exporting `mapStatus(backend: string): DisplayStatus` and a label/color lookup.
- [ ] 1.2 Unit test the mapping for all 6 backend values.

## 2. Badge Rendering

- [ ] 2.1 Replace existing badge logic in `IncomingInvoicesPage.tsx` row renderer with the new mapping.
- [ ] 2.2 For `inProgress` items, render a small spinner (Loader2 16px) instead of a badge.
- [ ] 2.3 For `error` items, add a Retry-Button next to the badge that triggers re-extraction.

## 3. Filter Dropdown

- [ ] 3.1 Replace status filter `<Select>` options to: `all` / `review` / `ready` / `done`.
- [ ] 3.2 Add separate Toggle "Auch fehlerhafte zeigen" (default `true`).
- [ ] 3.3 Map UI selection to backend status string before issuing query.
- [ ] 3.4 Reverse-map URL query parameter on load to support backwards-compat deep-links.

## 4. i18n

- [ ] 4.1 Add German + English keys: `incomingInvoices.status.review`, `.ready`, `.done`, `.error`, `incomingInvoices.filter.showErrors`.
- [ ] 4.2 Remove (or keep as aliases) the old keys `extracted`, `confirmed`, `matched`, etc.

## 5. Tests

- [ ] 5.1 Vitest: mapping function returns correct DisplayStatus for each input.
- [ ] 5.2 Vitest: filter dropdown selection translates to expected backend filter value.
- [ ] 5.3 Playwright E2E: filter to "Review" only shows extracted items.

## 6. Verification

- [ ] 6.1 Type check.
- [ ] 6.2 Manual smoke test: confirm visually that the list renders consistently across all status combinations.
