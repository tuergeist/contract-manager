## NEW Requirements

### Requirement: Active contract can be reset to draft

The system SHALL allow resetting an active contract to draft status when no invoices have been generated or imported for that contract.

#### Scenario: Reset active contract with no invoices
- **WHEN** user triggers "Reset to Draft" on an active contract
- **AND** the contract has no generated or imported invoices
- **THEN** contract status changes to `draft`
- **AND** all amendments for the contract are deleted
- **AND** the action is audit-logged

#### Scenario: Block reset when invoices exist
- **WHEN** user triggers "Reset to Draft" on an active contract
- **AND** the contract has at least one generated or imported invoice
- **THEN** the system returns an error
- **AND** the contract status remains `active`

#### Scenario: Block reset for non-active contracts
- **WHEN** user triggers "Reset to Draft" on a contract that is not active (paused, cancelled, ended, draft)
- **THEN** the system returns an error indicating the transition is not allowed

#### Scenario: Reset to Draft button visibility
- **WHEN** user views an active contract in Detail View 2
- **AND** the contract has no invoices
- **THEN** a "Reset to Draft" button is visible alongside the other status transition buttons

#### Scenario: Reset to Draft button hidden when invoices exist
- **WHEN** user views an active contract in Detail View 2
- **AND** the contract has at least one invoice
- **THEN** the "Reset to Draft" button is not shown

#### Scenario: Permission required
- **WHEN** user without contract write permission attempts to reset a contract
- **THEN** the system returns a permission error
