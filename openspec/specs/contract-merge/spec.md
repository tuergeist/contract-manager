## ADDED Requirements

### Requirement: Merge eligibility preconditions

The system SHALL allow merging a source contract into a target contract only when all preconditions are met.

#### Scenario: Source contract has no invoices
- **WHEN** user attempts to merge a source contract that has generated or imported invoices linked to it
- **THEN** the system SHALL reject the merge with an error "Source contract has invoices and cannot be merged"

#### Scenario: Source contract status is draft or active
- **WHEN** user attempts to merge a source contract with status other than `draft` or `active`
- **THEN** the system SHALL reject the merge with an error "Only draft or active contracts can be merged"

#### Scenario: Source and target belong to same customer
- **WHEN** user attempts to merge contracts belonging to different customers
- **THEN** the system SHALL reject the merge with an error "Contracts must belong to the same customer"

#### Scenario: Source and target are different contracts
- **WHEN** user attempts to merge a contract into itself
- **THEN** the system SHALL reject the merge with an error "Cannot merge a contract into itself"

#### Scenario: Target contract is not deleted or cancelled
- **WHEN** user attempts to merge into a contract with status `deleted`, `cancelled`, or `ended`
- **THEN** the system SHALL reject the merge with an error "Target contract is not in a mergeable state"

### Requirement: Merge preview shows transfer details

The system SHALL provide a preview of the merge operation before execution.

#### Scenario: Preview lists items to transfer
- **WHEN** user requests a merge preview for source and target contracts
- **THEN** the system SHALL return a list of all items from the source contract with their current `start_date`, `billing_start_date`, product, quantity, and unit price

#### Scenario: Preview shows Clockodo impact
- **WHEN** the target contract has Clockodo project mappings and tenant has Clockodo configured
- **THEN** the preview SHALL include what Clockodo projects would be created for the transferred items
- **WHEN** the target contract has no Clockodo mappings or Clockodo is not configured
- **THEN** the preview SHALL omit the Clockodo section

#### Scenario: Preview shows amendment summary
- **WHEN** the target contract status is `active`
- **THEN** the preview SHALL indicate that amendments will be created for each transferred item
- **WHEN** the target contract status is `draft`
- **THEN** the preview SHALL indicate that no amendments will be created

### Requirement: Merge transfers items to target contract

The system SHALL transfer all items from the source contract to the target contract during merge.

#### Scenario: Items transferred with configurable dates
- **WHEN** user executes a merge with optional per-item date overrides
- **THEN** the system SHALL move each ContractItem from the source to the target contract
- **AND** apply user-provided `start_date` and `billing_start_date` overrides per item (if given)
- **AND** preserve all other item fields (product, quantity, unit_price, price_period, is_one_off, delivery_status, etc.)

#### Scenario: Items transferred without date overrides
- **WHEN** user executes a merge without providing date overrides
- **THEN** the system SHALL keep each item's existing `start_date` and `billing_start_date` unchanged

#### Scenario: Item sort order appended to target
- **WHEN** items are transferred to the target contract
- **THEN** transferred recurring items SHALL be appended after existing recurring items (sort_order continues)
- **AND** transferred one-off items SHALL be appended after existing one-off items

#### Scenario: ContractItemPrice records transferred
- **WHEN** a source item has ContractItemPrice records (period-specific pricing)
- **THEN** the system SHALL transfer those price records along with the item

### Requirement: Amendments created for non-draft target

The system SHALL create amendment records when merging into a non-draft target contract.

#### Scenario: Amendment per transferred item on active target
- **WHEN** items are merged into a target contract with status `active`
- **THEN** the system SHALL create one ContractAmendment per transferred item with:
  - `type` = `product_added`
  - `effective_date` = item's `start_date` (or today if null)
  - `description` auto-generated mentioning merge from source contract
  - `arr_delta` calculated using the standard ARR calculation
  - `changes` JSON containing product, quantity, unit_price, price_period

#### Scenario: No amendments for draft target
- **WHEN** items are merged into a target contract with status `draft`
- **THEN** the system SHALL NOT create any amendments

### Requirement: HubSpot deal reference preserved on items

The system SHALL preserve the source contract's HubSpot deal ID on transferred items for traceability.

#### Scenario: Deal ID stored on transferred items
- **WHEN** the source contract has a `hubspot_deal_id`
- **THEN** each transferred item SHALL have its `source_hubspot_deal_id` field set to the source contract's `hubspot_deal_id`

#### Scenario: Source has no deal ID
- **WHEN** the source contract has no `hubspot_deal_id`
- **THEN** the transferred items' `source_hubspot_deal_id` SHALL remain null

### Requirement: Source contract deleted after merge

The system SHALL delete the source contract after a successful merge.

#### Scenario: Source set to deleted
- **WHEN** all items have been transferred successfully
- **THEN** the system SHALL set the source contract's status to `DELETED`

#### Scenario: Clockodo mappings on source discarded
- **WHEN** the source contract has TimeTrackingProjectMapping records
- **THEN** the system SHALL delete those mappings (source is being deleted)

#### Scenario: Merge is atomic
- **WHEN** any step of the merge fails (item transfer, amendment creation, source deletion)
- **THEN** the system SHALL roll back the entire operation and return an error

### Requirement: GraphQL mutation for contract merge

The system SHALL expose a `mergeContract` mutation and `mergeContractPreview` query.

#### Scenario: Preview query
- **WHEN** user calls `mergeContractPreview(sourceContractId, targetContractId)`
- **THEN** the system SHALL return the preview data (items, Clockodo impact, amendment info)
- **AND** validate all preconditions, returning errors if any fail

#### Scenario: Merge mutation
- **WHEN** user calls `mergeContract(input: MergeContractInput)` with sourceContractId, targetContractId, and optional itemOverrides
- **THEN** the system SHALL execute the merge and return the updated target contract
- **AND** require `contracts.write` permission

#### Scenario: Item overrides input
- **WHEN** user provides `itemOverrides` in the merge input
- **THEN** each override SHALL contain `itemId`, optional `startDate`, optional `billingStartDate`
- **AND** only provided date fields SHALL be applied (others keep original values)

### Requirement: Merge action in contract detail UI

The system SHALL show a merge action on eligible source contracts.

#### Scenario: Merge button visible on eligible contracts
- **WHEN** viewing a contract that is draft or active AND has no invoices
- **THEN** the UI SHALL show a "Merge into Contract" button

#### Scenario: Merge button hidden on ineligible contracts
- **WHEN** viewing a contract that has invoices or is in a non-mergeable status
- **THEN** the UI SHALL NOT show the merge button

#### Scenario: Merge dialog flow
- **WHEN** user clicks "Merge into Contract"
- **THEN** the UI SHALL show a dialog with:
  1. Target contract selector (filtered to same customer, excluding source and non-mergeable contracts)
  2. Preview of items to transfer with editable start_date and billing_start_date per item
  3. Amendment summary (if target is active)
  4. Clockodo impact (if applicable)
  5. Confirm button to execute the merge

#### Scenario: Post-merge navigation
- **WHEN** merge completes successfully
- **THEN** the UI SHALL navigate to the target contract detail page
- **AND** show a success notification mentioning how many items were transferred
