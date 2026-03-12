## ADDED Requirements

### Requirement: Estimated delivery date field on contract items
Contract items with delivery tracking (`delivery_status IS NOT NULL`) SHALL have an optional `estimated_delivery_date` (Date) field. Items without delivery tracking SHALL NOT have an ETA. The ETA MAY be set, updated, or cleared at any time while the item is pending. When an item is marked as delivered, the ETA SHALL be cleared automatically.

#### Scenario: Set ETA on pending deliverable item
- **WHEN** a user sets `estimated_delivery_date` to 2026-04-15 on a pending deliverable item
- **THEN** the item's `estimated_delivery_date` is stored as 2026-04-15

#### Scenario: Clear ETA on pending item
- **WHEN** a user clears the `estimated_delivery_date` on a pending item
- **THEN** the item's `estimated_delivery_date` is set to NULL

#### Scenario: ETA cleared when item is delivered
- **WHEN** a pending item with `estimated_delivery_date = 2026-04-15` is marked as delivered
- **THEN** the item's `estimated_delivery_date` is set to NULL

#### Scenario: ETA rejected on item without delivery tracking
- **WHEN** a user attempts to set `estimated_delivery_date` on an item with `delivery_status = NULL`
- **THEN** the system ignores the ETA value (field is not applicable)

#### Scenario: ETA on already-delivered item
- **WHEN** a user attempts to set `estimated_delivery_date` on a delivered item
- **THEN** the system ignores the ETA value (item is already delivered)

### Requirement: Revenue forecast includes pending items with ETA
The revenue forecast and recognition schedule SHALL include pending deliverable items that have an `estimated_delivery_date` set. The item SHALL be projected into the forecast as if it will be delivered on the ETA date. Pending items without an ETA SHALL remain excluded from forecasts (existing behavior).

#### Scenario: Pending one-off with ETA included in forecast
- **WHEN** a revenue forecast is calculated and a pending one-off item has `estimated_delivery_date = 2026-06-01` and `unit_price = 10000`
- **THEN** the item appears in the forecast at the ETA date with its full value

#### Scenario: Pending one-off without ETA excluded from forecast
- **WHEN** a revenue forecast is calculated and a pending one-off item has `estimated_delivery_date = NULL`
- **THEN** the item does not appear in the forecast (existing behavior unchanged)

#### Scenario: Dependent recurring item included when dependency has ETA
- **WHEN** a recurring item depends on a pending one-off that has `estimated_delivery_date = 2026-06-01`
- **THEN** the recurring item appears in the forecast starting from the later of its own `billing_start_date` and the dependency's ETA

#### Scenario: Dependent recurring item excluded when dependency has no ETA
- **WHEN** a recurring item depends on a pending one-off that has `estimated_delivery_date = NULL`
- **THEN** the recurring item does not appear in the forecast (existing behavior unchanged)

### Requirement: Dashboard KPIs include pending items with ETA
Dashboard forecast KPIs (current year forecast, next year forecast) SHALL include pending deliverable items that have an `estimated_delivery_date` set, projecting them at their ETA date. ARR KPI SHALL NOT include pending items regardless of ETA (ARR only counts active, delivered items).

#### Scenario: Current year forecast includes pending item with ETA in current year
- **WHEN** dashboard KPIs are calculated and a pending one-off has `estimated_delivery_date` within the current year
- **THEN** the item's value is included in the current year forecast total

#### Scenario: Pending item with ETA in next year excluded from current year forecast
- **WHEN** a pending item has `estimated_delivery_date` in the next calendar year
- **THEN** the item is excluded from the current year forecast but included in the next year forecast

#### Scenario: ARR excludes pending items regardless of ETA
- **WHEN** ARR is calculated and a pending recurring item has an ETA set
- **THEN** the item is NOT included in the ARR calculation

### Requirement: ETA displayed on Projects page
The Projects page SHALL display the `estimated_delivery_date` for each pending item. The ETA SHALL be editable inline or via a date picker directly on the Projects page.

#### Scenario: ETA column shown on Projects page
- **WHEN** a user views the Projects page
- **THEN** each pending item row displays its `estimated_delivery_date` (or empty if not set)

#### Scenario: Set ETA from Projects page
- **WHEN** a user clicks the ETA field on a pending item and selects a date
- **THEN** the item's `estimated_delivery_date` is updated and the page reflects the change

#### Scenario: Delivered items do not show ETA
- **WHEN** a user views delivered items on the Projects page
- **THEN** the ETA column shows the `delivered_at` date instead (or is empty)

### Requirement: ETA in contract detail item display
The contract detail items section SHALL display the `estimated_delivery_date` for pending deliverable items. The ETA SHALL be editable via the item edit modal.

#### Scenario: ETA shown on contract detail item row
- **WHEN** a user views a contract's items and an item has `estimated_delivery_date = 2026-05-01`
- **THEN** the item row displays "ETA: 2026-05-01" alongside the delivery status badge

#### Scenario: ETA editable in item edit modal
- **WHEN** a user opens the edit modal for a pending deliverable item
- **THEN** an "Estimated Delivery Date" date picker is available and pre-filled with the current ETA

### Requirement: GraphQL API for estimated delivery date
The GraphQL schema SHALL expose `estimatedDeliveryDate` on `ContractItemType`. The `AddContractItemInput` and `UpdateContractItemInput` types SHALL accept an optional `estimatedDeliveryDate` field. The field SHALL only be persisted for items with delivery tracking enabled.

#### Scenario: Query item with ETA
- **WHEN** a client queries a contract's items
- **THEN** each item includes `estimatedDeliveryDate` (Date or null)

#### Scenario: Set ETA via add item mutation
- **WHEN** a client adds a contract item with delivery tracking and `estimatedDeliveryDate = "2026-06-01"`
- **THEN** the created item has `estimated_delivery_date = 2026-06-01`

#### Scenario: Update ETA via update item mutation
- **WHEN** a client updates a pending deliverable item with `estimatedDeliveryDate = "2026-07-01"`
- **THEN** the item's `estimated_delivery_date` is changed to 2026-07-01

#### Scenario: Clear ETA via update item mutation
- **WHEN** a client updates an item with `estimatedDeliveryDate = null`
- **THEN** the item's `estimated_delivery_date` is set to NULL
