## Requirements

### Requirement: Item delivery tracking
Contract items SHALL have an optional `delivery_status` field with values `pending` or `delivered`. Items without delivery tracking have `delivery_status = NULL`. When an item's delivery status is set to `delivered`, a `delivered_at` date SHALL be recorded.

#### Scenario: One-off item created with delivery tracking
- **WHEN** a one-off item is added to a contract with delivery tracking enabled
- **THEN** the item's `delivery_status` is set to `pending` and `delivered_at` is NULL

#### Scenario: Item marked as delivered
- **WHEN** a user marks a pending item as delivered and provides a delivery date
- **THEN** the item's `delivery_status` changes to `delivered` and `delivered_at` is set to the provided date

#### Scenario: Item created without delivery tracking
- **WHEN** a contract item is added without delivery tracking
- **THEN** the item's `delivery_status` is NULL and billing proceeds normally

#### Scenario: Delivered status reverted to pending
- **WHEN** a user reverts a delivered item back to pending
- **THEN** the item's `delivery_status` changes to `pending` and `delivered_at` is cleared

### Requirement: Item-to-item dependency linking
A contract item SHALL be linkable to another item in the same contract via a `depends_on` relationship. An item MAY depend on at most one other item. The dependency target MUST be in the same contract.

#### Scenario: Recurring item linked to one-off dependency
- **WHEN** a recurring item is set to depend on a one-off item in the same contract
- **THEN** the recurring item's `depends_on` references the one-off item

#### Scenario: Dependency target must be in same contract
- **WHEN** a user attempts to set a dependency to an item in a different contract
- **THEN** the system rejects the operation with an error

#### Scenario: Self-dependency rejected
- **WHEN** a user attempts to set an item to depend on itself
- **THEN** the system rejects the operation with an error

#### Scenario: Dependency target deleted
- **WHEN** an item that is a dependency target is deleted
- **THEN** the dependent item's `depends_on` is set to NULL (dependency removed)

### Requirement: Billing blocked for undelivered items
Items with `delivery_status = pending` SHALL NOT appear in the billing schedule and SHALL NOT be included in generated invoices.

#### Scenario: Pending one-off item excluded from billing
- **WHEN** the billing schedule is calculated for a contract with a pending one-off item
- **THEN** the pending item does not appear in any billing event

#### Scenario: Delivered one-off item included in billing
- **WHEN** a one-off item has `delivery_status = delivered` and `billing_start_date` is set
- **THEN** the item appears in the billing schedule at its `billing_start_date`

### Requirement: Billing blocked for items with unresolved dependencies
Items whose `depends_on` target has `delivery_status = pending` (or is otherwise not delivered) SHALL NOT appear in the billing schedule. Items whose `depends_on` target has `delivery_status = delivered` or `delivery_status = NULL` (no tracking) SHALL be billed normally, provided their own `billing_start_date` is set.

#### Scenario: Recurring item blocked by pending dependency
- **WHEN** the billing schedule is calculated and a recurring item depends on a pending one-off
- **THEN** the recurring item does not appear in any billing event

#### Scenario: Recurring item unblocked after dependency delivered
- **WHEN** a dependency is marked as delivered and the dependent item has a `billing_start_date`
- **THEN** the dependent recurring item appears in the billing schedule from its `billing_start_date`

#### Scenario: Item with no dependency bills normally
- **WHEN** an item has `depends_on = NULL`
- **THEN** it is billed according to its own dates as usual

### Requirement: Delivery triggers dependent item activation
When an item is marked as delivered, the system SHALL prompt the user to set `billing_start_date` on any dependent items that have `billing_start_date = NULL`. The default suggested date SHALL be the `delivered_at` date.

#### Scenario: Dependency delivered — dependent item gets billing date
- **WHEN** a one-off item with two dependent recurring items is marked as delivered on 2025-03-15
- **THEN** the user is prompted to set billing_start_date for both dependent items, defaulting to 2025-03-15

#### Scenario: Dependent item already has billing date
- **WHEN** a dependency is delivered but the dependent item already has a `billing_start_date`
- **THEN** the existing `billing_start_date` is kept unchanged

### Requirement: Revenue forecast excludes blocked items
The revenue forecast/recognition schedule SHALL exclude items that are blocked (pending delivery or unresolved dependency).

#### Scenario: Pending item excluded from forecast
- **WHEN** a revenue forecast is calculated and a contract has a pending one-off and a dependent recurring item
- **THEN** neither the pending one-off nor the blocked recurring item appear in the forecast

#### Scenario: Delivered items included in forecast
- **WHEN** the dependency is delivered and all billing dates are set
- **THEN** both items appear in the revenue forecast from their respective billing start dates

### Requirement: GraphQL API for dependencies and delivery
The GraphQL schema SHALL expose `delivery_status`, `delivered_at`, `depends_on`, and `dependent_items` on `ContractItemType`. Mutations SHALL be provided to mark items as delivered, revert delivery, and set/clear dependencies.

#### Scenario: Query item with dependency info
- **WHEN** a client queries a contract's items
- **THEN** each item includes `deliveryStatus`, `deliveredAt`, `dependsOn { id }`, and `dependentItems { id }`

#### Scenario: Mark item as delivered via mutation
- **WHEN** a client calls the deliver mutation with an item ID and delivery date
- **THEN** the item's delivery status changes to `delivered` and `delivered_at` is set

#### Scenario: Set dependency via mutation
- **WHEN** a client calls the set-dependency mutation with an item ID and a target item ID
- **THEN** the item's `depends_on` is set to the target item
