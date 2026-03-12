## Why

HubSpot addon deals create separate draft contracts in the contract database, one per deal. When an addon belongs to an existing contract (e.g., a customer buys an additional module for their current subscription), there's no way to merge the draft into the target contract. Users must manually recreate items, which is error-prone and loses the HubSpot deal reference.

## What Changes

- **Merge source contract into existing contract**: A "Merge into Contract" action on contracts lets users select a target contract of the same customer and transfer all items. The source contract can be draft or active, but **must have no invoices** linked to it (neither generated nor imported). This prevents accounting inconsistencies.
- **Item date handling**: Each transferred item gets its own `start_date` and `billing_start_date` (defaulting from the source draft, editable during merge). The target contract's billing cycle/anchor is preserved.
- **Amendment tracking**: Merging into an active contract creates amendments (type `product_added`) for each transferred item, just like manually adding items.
- **Order confirmation flow**: After merge, users can optionally generate an order confirmation (AB) for the newly added items on the target contract via the existing AB flow.
- **Clockodo project handling**: If the target contract has Clockodo mappings, the merge preview shows what projects would be created/updated for the new items. Existing mappings on the source draft are discarded (source is deleted).
- **Source contract cleanup**: After successful merge, the source draft contract is deleted (status → DELETED). Its `hubspot_deal_id` is stored on the target contract or items for traceability.
- **HubSpot deal reference preservation**: The source draft's `hubspot_deal_id` is saved on transferred items (new field) so the addon deal remains traceable.

## Capabilities

### New Capabilities
- `contract-merge`: Merge a source contract (draft or active, with no invoices) into an existing contract of the same customer, with date configuration, amendment tracking, and source cleanup.

### Modified Capabilities
- `offer-record`: Offer generation must support scoping to specific items (the newly merged ones) rather than always covering all contract items — so users can send an offer/AB for just the addon.

## Impact

- **Backend**: `apps/contracts/models.py` (new field on ContractItem for `source_hubspot_deal_id`), `apps/contracts/schema.py` (new `merge_contract` mutation + preview query), `apps/contracts/services/clockodo_provisioning.py` (preview update)
- **Frontend**: New merge dialog on ContractDetail (draft/active contracts without invoices), item date editor, target contract selector (same customer), Clockodo preview section
- **Migrations**: New field on ContractItem
- **No breaking changes**: Existing contracts/items are unaffected; merge is opt-in and guarded by the no-invoices precondition
