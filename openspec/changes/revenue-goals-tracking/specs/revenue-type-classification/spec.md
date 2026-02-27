## ADDED Requirements

### Requirement: Products have a revenue type classification
Each Product SHALL have a `revenue_type` field with one of three values: `advanced_development`, `training_implementation`, or `recurring`.

#### Scenario: Revenue type choices
- **WHEN** viewing or editing a product's revenue type
- **THEN** the available choices SHALL be: "Advanced Development", "Training + Implementation", "Recurring Revenue"

#### Scenario: Subscription products default to recurring
- **WHEN** a new product is created with type=subscription
- **THEN** the revenue_type SHALL default to `recurring`

#### Scenario: One-off products have no default
- **WHEN** a new product is created with type=one_off
- **THEN** the revenue_type SHALL be blank and the user MUST select one before saving

#### Scenario: Revenue type is required on products
- **WHEN** a user attempts to save a product without a revenue_type
- **THEN** the system SHALL display a validation error requiring the field to be set

### Requirement: Product list displays revenue type
The product list SHALL display the revenue type for each product.

#### Scenario: Revenue type column in product list
- **WHEN** user views the product list
- **THEN** each product row SHALL display its revenue type as a human-readable label

#### Scenario: Product list can filter by revenue type
- **WHEN** user filters the product list by revenue type
- **THEN** only products with the selected revenue type SHALL be displayed

### Requirement: Product form includes revenue type selector
The product create/edit form SHALL include a revenue type field.

#### Scenario: Revenue type selector on product form
- **WHEN** user creates or edits a product
- **THEN** the form SHALL include a dropdown for selecting the revenue type

#### Scenario: Revenue type is editable
- **WHEN** user changes a product's revenue type and saves
- **THEN** the new revenue type SHALL be persisted

### Requirement: Contract items inherit revenue type from product
When a contract item is linked to a product, it SHALL inherit the product's revenue type unless explicitly overridden.

#### Scenario: Item inherits product revenue type
- **WHEN** a contract item is linked to a product with revenue_type=recurring
- **AND** the item has no explicit revenue_type set
- **THEN** the item's effective revenue type SHALL be `recurring`

#### Scenario: Item override takes precedence
- **WHEN** a contract item is linked to a product with revenue_type=recurring
- **AND** the item has revenue_type=advanced_development explicitly set
- **THEN** the item's effective revenue type SHALL be `advanced_development`

### Requirement: Contract items without a product require explicit revenue type
When a contract item has no linked product, the user MUST set the revenue_type explicitly.

#### Scenario: No-product item requires revenue type
- **WHEN** a user adds or edits a contract item without selecting a product
- **THEN** the revenue type field SHALL be required and the form SHALL not submit without it

#### Scenario: Discount items require revenue type
- **WHEN** a user adds a line item with a negative unit price and no product
- **THEN** the revenue type field SHALL be required

#### Scenario: Revenue type field appears when product is cleared
- **WHEN** a user removes the product from an existing contract item
- **THEN** the revenue type field SHALL become visible and required

### Requirement: Contract item form shows revenue type
The add/edit contract item modal SHALL display the revenue type field contextually.

#### Scenario: Revenue type hidden when product is selected
- **WHEN** a contract item has a linked product
- **THEN** the revenue type field SHALL be hidden or shown as read-only with the inherited value

#### Scenario: Revenue type editable when no product
- **WHEN** a contract item has no linked product
- **THEN** the revenue type field SHALL be visible and editable as a required dropdown

#### Scenario: Revenue type override option
- **WHEN** a contract item has a linked product
- **THEN** the user SHALL be able to optionally override the inherited revenue type

### Requirement: GraphQL exposes revenue type on products and items
The GraphQL API SHALL expose revenue_type on ProductType and ContractItemType, and effective_revenue_type on ContractItemType.

#### Scenario: ProductType includes revenue_type field
- **WHEN** querying products via GraphQL
- **THEN** each product SHALL include a `revenueType` field

#### Scenario: ContractItemType includes revenue_type and effective_revenue_type
- **WHEN** querying contract items via GraphQL
- **THEN** each item SHALL include `revenueType` (explicit value or null) and `effectiveRevenueType` (resolved value)

#### Scenario: Product mutations accept revenue_type
- **WHEN** creating or updating a product via GraphQL
- **THEN** the mutation SHALL accept an optional `revenueType` input field

#### Scenario: Contract item mutations accept revenue_type
- **WHEN** adding or updating a contract item via GraphQL
- **THEN** the mutation SHALL accept an optional `revenueType` input field

### Requirement: Data migration classifies existing products
The system SHALL provide a migration that classifies existing products based on their type.

#### Scenario: Subscription products migrated to recurring
- **WHEN** the migration runs
- **THEN** all existing products with type=subscription SHALL have revenue_type set to `recurring`

#### Scenario: One-off products left unclassified
- **WHEN** the migration runs
- **THEN** existing products with type=one_off SHALL have revenue_type left as null (requiring manual classification)

#### Scenario: Existing contract items left as null
- **WHEN** the migration runs
- **THEN** existing contract items SHALL have revenue_type left as null (they inherit from their product)
