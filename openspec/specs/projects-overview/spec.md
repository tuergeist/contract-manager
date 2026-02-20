## Requirements

### Requirement: Projects page listing deliverable items
The system SHALL provide a dedicated "Projects" page at `/projects` that lists all contract items with delivery tracking enabled (`delivery_status IS NOT NULL`) across all contracts in the tenant.

#### Scenario: Projects page shows pending deliverables
- **WHEN** a user navigates to `/projects`
- **THEN** the page displays all items with `delivery_status = pending` or `delivery_status = delivered`, showing item name/product, customer, contract, status, and delivered date (if applicable)

#### Scenario: Projects page with no deliverables
- **WHEN** no contract items have delivery tracking enabled
- **THEN** the page shows an empty state message

### Requirement: Projects page filtering
The projects page SHALL support filtering by delivery status (pending / delivered / all) and by customer.

#### Scenario: Filter by pending status
- **WHEN** a user filters the projects list by status "pending"
- **THEN** only items with `delivery_status = pending` are shown

#### Scenario: Filter by customer
- **WHEN** a user selects a customer filter
- **THEN** only items from contracts belonging to that customer are shown

#### Scenario: Default filter shows pending items
- **WHEN** a user opens the projects page without setting any filter
- **THEN** the list defaults to showing items with `delivery_status = pending`

### Requirement: Projects page shows dependent items
Each project item on the projects page SHALL display the number of dependent items that are blocked waiting for its delivery.

#### Scenario: Project item with dependents
- **WHEN** a one-off item has 2 recurring items depending on it
- **THEN** the projects page shows "2 dependent items" next to that item

#### Scenario: Project item with no dependents
- **WHEN** a deliverable item has no dependent items
- **THEN** no dependent count is shown

### Requirement: Mark delivered from projects page
Users SHALL be able to mark items as delivered directly from the projects page, including setting the delivery date and billing start dates for dependent items.

#### Scenario: Mark delivered from projects page
- **WHEN** a user clicks "Mark as delivered" on a project item and enters a delivery date
- **THEN** the item's delivery status changes to `delivered` and the user is prompted to set billing dates for dependent items

### Requirement: Navigation to contract from projects page
Each item on the projects page SHALL link to its parent contract detail page.

#### Scenario: Navigate to contract
- **WHEN** a user clicks the contract name on a project item
- **THEN** they are navigated to the contract detail page

### Requirement: Projects in main navigation
The projects page SHALL appear in the main navigation bar, between "Contracts" and "Invoices".

#### Scenario: Navigation link visible
- **WHEN** a user views the main navigation
- **THEN** a "Projects" link is visible between "Contracts" and "Invoices"
