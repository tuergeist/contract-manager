## 1. Frontend: Page-Level Pending-IDs

- [ ] 1.1 In `IncomingInvoicesPage.tsx`, derive `pendingIds: string[]` from the loaded invoice list — filter on `extractionStatus in ('extracted', 'confirmed')` AND items missing counterparty assignment for `confirmed`, sorted by current sort selection.
- [ ] 1.2 Pass `pendingIds` as a prop to `<IncomingInvoiceDetail>`.

## 2. Frontend: Detail Sheet — "Confirm + Next" Action

- [ ] 2.1 Add `pendingIds: string[]` prop to `IncomingInvoiceDetail` and compute `nextId` from `pendingIds.indexOf(id) + 1`.
- [ ] 2.2 Add a "Confirm + Next" button next to the existing "Confirm" button. Disable when no `nextId` exists; show "Confirm + Done" instead in that case.
- [ ] 2.3 Implement handler: call `confirmIncomingInvoice` mutation; on success, if `nextId` exists, swap detail view to `nextId` (set internal state, refetch detail query); otherwise close sheet and show toast "Alle eingehenden Rechnungen bearbeitet".
- [ ] 2.4 Defensive: if confirming an invoice does not change its eligibility for the pending list (e.g., still missing CP), continue to advance to the next id in the array — do not loop back to the just-confirmed invoice within this action.

## 3. Frontend: Keyboard Shortcut

- [ ] 3.1 Wire `Cmd+Enter` / `Ctrl+Enter` keydown listener on the sheet root that triggers the same handler as "Confirm + Next".
- [ ] 3.2 Ensure the listener is removed on sheet close to avoid leaks.
- [ ] 3.3 Skip the shortcut when the focused element is an `<input>`/`<textarea>`/`<select>` and the user has unsaved changes — fall through to the input's normal behavior.

## 4. i18n

- [ ] 4.1 Add German + English keys: `incomingInvoices.detail.confirmAndNext`, `incomingInvoices.detail.confirmAndDone`, `incomingInvoices.detail.allConfirmed`.

## 5. Tests

- [ ] 5.1 Vitest unit test: clicking "Confirm + Next" on a non-last invoice transitions the sheet to the next pending id.
- [ ] 5.2 Vitest unit test: clicking on the last pending id closes the sheet and emits the "all done" toast.
- [ ] 5.3 Vitest unit test: keyboard shortcut Cmd/Ctrl+Enter triggers the same flow.
- [ ] 5.4 Playwright E2E: confirm-and-next loop walks through 3 pending invoices and finally closes.

## 6. Verification

- [ ] 6.1 Type check (`npx tsc --noEmit`).
- [ ] 6.2 Manual smoke test in dev environment with at least 3 pending invoices.
- [ ] 6.3 Update changelog entry.
