## Context

Contract status transitions are handled by `transition_contract_status` mutation in `apps/contracts/schema.py`. The allowed transitions are `draft→active`, `active→paused/cancelled`, `paused→active/cancelled`, `cancelled→ended`. There is no reverse path back to draft.

Amendments are created automatically when non-draft contracts change (items added/removed/modified, status transitions). They are stored via `ContractAmendment` model with a FK to `Contract` (related name `amendments`).

Invoices link to contracts via `invoice_records` (generated invoices) and `imported_invoices` (imported). The presence of any invoice record for a contract means billing has started and reset should be blocked.

The frontend status transition buttons live in `ContractForm.tsx` (Detail View 2) inside a `StatusTransitionDialog` component.

## Goals / Non-Goals

**Goals:**
- Allow reverting an active contract to draft when no invoices exist
- Clear all amendments when resetting to draft (they become meaningless for a draft)
- Allow changing the customer on a draft contract
- Both operations audit-logged and permission-checked

**Non-Goals:**
- Resetting contracts that have invoices (explicitly blocked)
- Resetting from paused/cancelled/ended states
- Changing customer on non-draft contracts
- Migrating or reassigning existing invoices

## Decisions

### 1. Reset to Draft: dedicated mutation vs extending `transitionContractStatus`

**Decision:** Add `active→draft` to the existing `transition_contract_status` mutation's allowed transitions, with extra guard logic (invoice check + amendment deletion) inside the `active→draft` branch.

**Rationale:** The existing mutation already handles all status transitions, permission checks, and result types. Adding a special case keeps the API surface small. The frontend already has a `StatusTransitionDialog` that can show a "Reset to Draft" button.

**Alternative considered:** A separate `resetContractToDraft` mutation. Rejected because it would duplicate permission/tenant checks and require a new frontend mutation wiring.

### 2. Invoice check: which invoice types block reset?

**Decision:** Check both `contract.invoice_records.exists()` and `contract.imported_invoices.exists()`. If either has records, block the reset.

**Rationale:** Any invoice — generated or imported — indicates billing activity that would be inconsistent with a draft contract.

### 3. Amendment cleanup on reset

**Decision:** Delete all amendments for the contract when resetting to draft (`contract.amendments.all().delete()`).

**Rationale:** Amendments track changes to a non-draft contract. Once back in draft, the contract is treated as "not yet finalized" — amendments from the previous activation cycle are no longer meaningful. If the contract is activated again, amendments start fresh.

### 4. Change Customer: separate mutation

**Decision:** New `change_contract_customer` mutation that accepts `contract_id` and `customer_id`. Only allowed when `contract.status == draft`.

**Rationale:** This is not a status transition — it's a field change. It doesn't fit inside `transition_contract_status`. It also needs to update the contract group FK to null (since groups are per-customer).

### 5. Frontend placement

**Decision:**
- "Reset to Draft" button appears alongside existing status buttons in Detail View 2 when contract is active and has no invoices.
- "Change Customer" button appears in Detail View 2 header area when contract is draft, opening a customer selector dialog.

## Risks / Trade-offs

- **Amendment deletion is irreversible** → Mitigated by the invoice guard (if no invoices, the contract hasn't really been "used" yet) and audit logging of the reset action.
- **Race condition: invoice generated between check and reset** → Mitigated by wrapping in `transaction.atomic()` with a `select_for_update()` on the contract.
- **Group becomes invalid after customer change** → Nullify `group` FK when customer changes, since groups are customer-scoped.
