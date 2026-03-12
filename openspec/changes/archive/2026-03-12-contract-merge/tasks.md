## 1. Model & Migration

- [x] 1.1 Add `source_hubspot_deal_id` CharField (nullable, blank) to ContractItem model
- [x] 1.2 Create and run migration for the new field
- [x] 1.3 Expose `source_hubspot_deal_id` on ContractItemType in schema.py (read-only)

## 2. Merge Service

- [x] 2.1 Create `backend/apps/contracts/services/contract_merge.py` with validation helpers: `validate_merge_preconditions(source, target)` returning structured errors
- [x] 2.2 Implement `preview_merge(source, target)` — returns items list, amendment info (active target), Clockodo preview (if configured)
- [x] 2.3 Implement `execute_merge(source, target, item_overrides)` — atomic transaction: transfer items with sort_order append, apply date overrides, set `source_hubspot_deal_id`, create amendments (if active target), delete source Clockodo mappings, set source status to DELETED
- [x] 2.4 Write tests for precondition validation (same customer, no invoices, valid statuses, not self-merge, target not deleted/cancelled/ended)
- [x] 2.5 Write tests for execute_merge (item transfer, sort_order, date overrides, amendment creation, HubSpot deal ID preservation, source deletion, atomicity on failure)

## 3. GraphQL API

- [x] 3.1 Add `MergeContractInput` input type with `source_contract_id`, `target_contract_id`, `item_overrides` (list of `{item_id, start_date?, billing_start_date?}`)
- [x] 3.2 Add `MergeContractPreviewType` result type with items list, amendment_summary, clockodo_preview
- [x] 3.3 Add `merge_contract_preview` query field — calls `validate_merge_preconditions` + `preview_merge`, requires `contracts.read`
- [x] 3.4 Add `merge_contract` mutation — calls `execute_merge`, requires `contracts.write`, returns updated target contract or errors
- [x] 3.5 Write tests for preview query and merge mutation (happy path + error cases)

## 4. Offer Record Scoping (Modified Capability)

- [x] 4.1 Add `scoped_item_ids` JSONField (nullable) to OfferRecord model, create migration
- [x] 4.2 Update offer creation logic to accept optional `item_ids` parameter — when provided, snapshot only those items and store IDs in `scoped_item_ids`
- [x] 4.3 Update `generateOrderConfirmation` mutation to accept optional `itemIds` input
- [x] 4.4 Write tests for scoped offer creation (subset of items, correct totals, scoped_item_ids stored)

## 5. Frontend — Merge Dialog

- [x] 5.1 Add `mergeContractPreview` query and `mergeContract` mutation to GraphQL operations
- [x] 5.2 Create `MergeContractDialog` component — target contract selector (Popover/Command, same customer, excludes source + non-mergeable), item preview table with editable start_date/billing_start_date per item, amendment summary (conditional on active target), Clockodo impact section (conditional), confirm/cancel buttons
- [x] 5.3 Add "Merge into Contract" button in ContractDetail Detail View 2 actions area — visible only when contract is draft/active AND `has_invoices` is false
- [x] 5.4 Handle merge success: navigate to target contract, show success toast with item count
- [x] 5.5 Add German and English translations for all merge UI strings

## 6. Integration & E2E

- [x] 6.1 Add E2E test: merge a draft contract into an active contract, verify items transferred and source deleted
- [x] 6.2 Add E2E test: verify merge button hidden when contract has invoices
- [x] 6.3 Verify Clockodo preview section appears/hides correctly based on tenant config
