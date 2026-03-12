## Context

HubSpot addon deals create separate draft contracts. When an addon belongs to an existing subscription, users must manually recreate items on the target contract. The merge feature automates this transfer, preserving deal traceability and handling amendments, Clockodo mappings, and optional scoped order confirmations.

Current state:
- `Contract.has_invoices` property already checks `invoice_records.exists() or imported_invoices.exists()`
- `ContractAmendment` model supports `product_added` type with `arr_delta` and `changes` JSON
- Clockodo provisioning has `preview_activation()` and `provision_projects()` functions
- `ContractItem` has `sort_order`, `start_date`, `billing_start_date`, `added_by_amendment` FK
- `OfferRecord` stores frozen `line_items_snapshot` but has no item-scoping mechanism yet

## Goals / Non-Goals

**Goals:**
- Allow merging a source contract's items into an existing target contract of the same customer
- Preserve HubSpot deal references on transferred items for traceability
- Create proper amendments when merging into active contracts
- Provide a preview before executing the merge
- Keep the operation atomic (all-or-nothing)

**Non-Goals:**
- Merging contracts across different customers
- Partial item transfer (cherry-picking which items to move) — all items transfer
- Merging contracts that have invoices (prevents accounting inconsistencies)
- Automatic Clockodo project creation during merge (preview only; provisioning happens via existing activation flow)
- Scoped offer generation (the `offer-record` spec change is tracked separately)

## Decisions

### 1. New `source_hubspot_deal_id` field on ContractItem

**Decision:** Add a nullable `CharField` on `ContractItem` to store the source contract's `hubspot_deal_id` when items are transferred via merge.

**Rationale:** The deal ID lives at contract level, but once merged the source contract is deleted. Storing it on items preserves the link. A simple CharField is sufficient — no FK needed since HubSpot IDs are opaque strings. This mirrors how `hubspot_deal_id` is stored on Contract itself.

**Alternative considered:** Store merge history in a separate `ContractMergeLog` table. Rejected because it adds complexity without clear benefit — the item-level field plus amendment records provide sufficient audit trail.

### 2. Merge implemented as a service function, exposed via GraphQL mutation

**Decision:** Create `backend/apps/contracts/services/contract_merge.py` with `preview_merge()` and `execute_merge()` functions. Expose via `mergeContractPreview` query and `mergeContract` mutation in schema.py.

**Rationale:** Separating business logic into a service keeps the schema layer thin and makes the merge logic independently testable. This follows the pattern used by `clockodo_provisioning.py`.

**Alternative considered:** Inline everything in the mutation resolver. Rejected for testability and separation of concerns.

### 3. Sort order: append transferred items after existing items

**Decision:** Query `max(sort_order)` for recurring and one-off items separately on the target contract, then assign incrementing sort_orders to transferred items starting from max+1.

**Rationale:** Preserves existing item ordering on the target. Users can reorder after merge via the existing drag-and-drop UI.

### 4. Amendment creation uses existing pattern from add_contract_item

**Decision:** Reuse the same amendment creation logic from `add_contract_item` mutation — create one `ContractAmendment` per transferred item with type `product_added`, computed `arr_delta`, and `changes` JSON.

**Rationale:** Consistency with how manual item additions are tracked. The `added_by_amendment` FK on ContractItem links each item to its amendment.

### 5. Precondition validation in both preview and execute

**Decision:** Validate all preconditions (same customer, no invoices on source, valid statuses, not self-merge) in both `preview_merge()` and `execute_merge()`. Return structured errors.

**Rationale:** Preview validation gives immediate feedback in the UI. Re-validating on execute prevents race conditions (e.g., an invoice generated between preview and confirm).

### 6. Atomic merge via database transaction

**Decision:** Wrap the entire merge (item transfer, amendment creation, source deletion, Clockodo mapping cleanup) in `transaction.atomic()`.

**Rationale:** Partial merges would leave data in an inconsistent state. Django's `transaction.atomic()` handles rollback on any exception.

### 7. Frontend merge dialog on ContractDetail (Detail View 2)

**Decision:** Add a "Merge into Contract" button in the actions area of Detail View 2 (`/contracts/:id/edit` read-only mode), visible only when the contract is draft/active and has no invoices. The merge dialog is a modal with:
1. Target contract selector (Popover/Command pattern, filtered to same customer)
2. Item preview table with editable date fields
3. Amendment and Clockodo impact sections (conditional)

**Rationale:** Detail View 2 is where status actions live. The Popover/Command pattern is already used for product selection in the codebase. A modal keeps the user in context.

### 8. Clockodo preview: read-only, no auto-provisioning

**Decision:** The merge preview shows what Clockodo projects *would* be created for new items (using `preview_activation()` logic), but does NOT auto-create them. Provisioning happens when the user activates or re-provisions from the Clockodo tab.

**Rationale:** Clockodo provisioning is a separate concern. Auto-creating projects during merge would bypass the existing provisioning UI where users configure strategies (per-item vs combined for one-offs).

## Risks / Trade-offs

**[Risk] Source contract deleted but target contract update fails mid-transaction** → Mitigated by `transaction.atomic()`. If any step fails, everything rolls back.

**[Risk] Race condition: invoice created on source between preview and confirm** → Mitigated by re-validating preconditions inside `execute_merge()` within the transaction.

**[Risk] Large number of items on source contract could slow the merge** → Acceptable trade-off. Contracts rarely have more than 20-30 items. Bulk `update()` and `create()` calls keep DB round-trips low.

**[Trade-off] All items must transfer (no cherry-picking)** → Simplifies the feature significantly. If partial merge is needed later, it can be added as an enhancement. The primary use case (addon deals) always involves transferring all items.

**[Trade-off] Merge deletes source contract rather than archiving** → Uses existing `DELETED` status which is already filtered out of lists. The amendment records and `source_hubspot_deal_id` preserve the audit trail.

## Open Questions

- Should the merge button also be visible on the contract list page (as a row action), or only on the detail view? Starting with detail-only and expanding if users request it.
