## NEW Requirements

### Requirement: Draft contract customer can be changed

The system SHALL allow changing the customer of a contract while it is in draft status.

#### Scenario: Change customer on draft contract
- **WHEN** user selects a new customer for a draft contract
- **THEN** the contract's customer is updated to the selected customer
- **AND** the contract's group is set to null (groups are customer-scoped)
- **AND** the action is audit-logged

#### Scenario: Block customer change on non-draft contract
- **WHEN** user attempts to change the customer on a contract that is not in draft status
- **THEN** the system returns an error
- **AND** the customer remains unchanged

#### Scenario: Change Customer button visibility
- **WHEN** user views a draft contract in Detail View 2
- **THEN** a "Change Customer" button or link is visible near the customer name

#### Scenario: Change Customer button hidden for non-draft
- **WHEN** user views a non-draft contract in Detail View 2
- **THEN** the "Change Customer" option is not shown

#### Scenario: Customer selector dialog
- **WHEN** user clicks "Change Customer"
- **THEN** a dialog opens with a searchable list of customers
- **AND** user can select a customer and confirm

#### Scenario: Permission required
- **WHEN** user without contract write permission attempts to change the customer
- **THEN** the system returns a permission error
