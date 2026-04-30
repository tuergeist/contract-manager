## 1. User Setting

- [ ] 1.1 Add `auto_close_match_sheet: bool` (default `true`) to user settings JSON in backend (no migration; settings are JSONField).
- [ ] 1.2 Add GraphQL field on `CurrentUser` / user settings query and a mutation to update.
- [ ] 1.3 Add Toggle in `frontend/src/features/settings/UserSettings.tsx` under a new "Banking Workflow" section.

## 2. Auto-Close Logic

- [ ] 2.1 In `TransactionMatchSheet.tsx` `handleAddMatch`, after `refetch()`/`refetchSuggestions()` complete, evaluate `abs(amount) - totalMatched < 0.01`.
- [ ] 2.2 If fully matched AND user setting is on: schedule a 400ms `setTimeout` to call `onOpenChange(false)`.
- [ ] 2.3 In the timeout callback, re-evaluate from latest state (use a ref or stale-closure-safe pattern). Skip close if no longer fully matched.

## 3. Undo Toast

- [ ] 3.1 On auto-close, capture the just-created `matchId` and show a Sonner toast: "Match gespeichert · [Rückgängig]" with 5s timeout.
- [ ] 3.2 Undo handler calls `deletePaymentMatch(matchId)` and reopens the sheet for the same `transactionId`.

## 4. i18n

- [ ] 4.1 Add German + English keys: `banking.matchView.autoClosed`, `banking.matchView.undo`, `settings.user.autoCloseMatchSheet`.

## 5. Tests

- [ ] 5.1 Vitest: full match → setTimeout schedules close.
- [ ] 5.2 Vitest: partial match → no close scheduled.
- [ ] 5.3 Vitest: user setting off → no auto-close even on full match.
- [ ] 5.4 Vitest: undo toast deletes match.
- [ ] 5.5 Playwright E2E: match a transaction fully → sheet closes within ≤1s.

## 6. Verification

- [ ] 6.1 Type check.
- [ ] 6.2 Manual smoke test in dev.
