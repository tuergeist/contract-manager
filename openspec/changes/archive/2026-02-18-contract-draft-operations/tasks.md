## 1. Backend — Reset to Draft

- [x] 1.1 In `transition_contract_status` mutation, add `Contract.Status.DRAFT` to `allowed_transitions[Contract.Status.ACTIVE]`
- [x] 1.2 Add guard: when transitioning `active→draft`, check `contract.invoice_records.exists()` and `contract.imported_invoices.exists()` — return error if either is true
- [x] 1.3 Use `select_for_update()` on the contract query for the `active→draft` path to prevent race conditions
- [x] 1.4 Delete all amendments when resetting to draft: `contract.amendments.all().delete()`
- [x] 1.5 Skip amendment creation for the `active→draft` transition (no amendment for reset itself)

## 2. Backend — Change Customer

- [x] 2.1 Add `change_contract_customer` mutation accepting `contract_id: ID!` and `customer_id: ID!`, returning `ContractResult`
- [x] 2.2 Validate contract is in draft status, return error otherwise
- [x] 2.3 Update `contract.customer` to the new customer and set `contract.group = None`
- [x] 2.4 Save the contract (audit logging happens automatically via signals)

## 3. Backend — Tests

- [x] 3.1 Test: reset active contract with no invoices succeeds, status becomes draft, amendments deleted
- [x] 3.2 Test: reset active contract with generated invoices returns error
- [x] 3.3 Test: reset active contract with imported invoices returns error
- [x] 3.4 Test: reset non-active contract (draft, paused, etc.) returns error
- [x] 3.5 Test: change customer on draft contract succeeds, group set to null
- [x] 3.6 Test: change customer on non-draft contract returns error

## 4. Frontend — Reset to Draft

- [x] 4.1 Add `{ from: 'active', to: 'draft', label: 'resetToDraft', confirmKey: 'confirmResetToDraft', isReversible: false }` to `STATUS_TRANSITIONS` in `ContractForm.tsx`
- [x] 4.2 Conditionally show the reset button only when contract has no invoices (need to pass invoice count or `hasInvoices` flag to ContractForm, or add a field to the GraphQL contract query)
- [x] 4.3 Add translation keys for `resetToDraft` and `confirmResetToDraft` in `en.json` and `de.json`

## 5. Frontend — Change Customer

- [x] 5.1 Add `CHANGE_CONTRACT_CUSTOMER_MUTATION` GraphQL mutation in `ContractForm.tsx`
- [x] 5.2 Add "Change Customer" button in Detail View 2 header, visible only when contract is draft
- [x] 5.3 Add `ChangeCustomerDialog` with searchable customer list (reuse existing `CUSTOMERS_QUERY` and Popover/Command pattern)
- [x] 5.4 Add translation keys for change customer button, dialog title, and confirmation in `en.json` and `de.json`

## 6. Verification

- [x] 6.1 Run `npx tsc --noEmit` — no type errors
- [x] 6.2 Run `make test-back` — all tests pass
- [ ] 6.3 Manual test: reset active contract to draft, verify amendments cleared
- [ ] 6.4 Manual test: change customer on draft contract, verify group nullified
