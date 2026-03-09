## ADDED Requirements

### Requirement: Permissions for cost centers
The system SHALL define a new permission resource `cost_centers` with actions: `read`, `write`, `config`. Viewing cost center assignments requires `cost_centers.read`. Assigning cost centers to transactions/invoices requires `cost_centers.write`. Managing cost center definitions (CRUD) requires `cost_centers.config`.

#### Scenario: Viewer can see cost center assignments
- **WHEN** a user has `cost_centers.read`
- **THEN** they can see cost center columns on transactions and counterparties but cannot change assignments

#### Scenario: Writer can assign cost centers
- **WHEN** a user has `cost_centers.write`
- **THEN** they can assign/change cost centers on transactions, invoices, and set defaults on counterparties

#### Scenario: Config required for cost center management
- **WHEN** a user without `cost_centers.config` tries to create or delete a cost center
- **THEN** the system returns a permission error

### Requirement: Manage cost centers
The system SHALL allow users with `cost_centers.config` permission to create, edit, and delete cost centers. Cost centers are flat (no hierarchy), defined per tenant, with a unique code and a name.

#### Scenario: Create cost center
- **WHEN** user creates a cost center with code "100" and name "Entwicklung"
- **THEN** the cost center appears in the cost center list

#### Scenario: Duplicate code rejected
- **WHEN** user creates a cost center with code "100" and one already exists with that code in the same tenant
- **THEN** the system rejects the creation with an error

#### Scenario: Edit cost center
- **WHEN** user renames cost center "100" from "Entwicklung" to "Engineering"
- **THEN** the name is updated; existing assignments remain intact

#### Scenario: Delete cost center
- **WHEN** user deletes cost center "100" that has no assignments
- **THEN** the cost center is removed

#### Scenario: Delete cost center with assignments
- **WHEN** user deletes a cost center that is assigned to counterparties or used in split rules
- **THEN** the system warns and requires confirmation; assignments are cleared upon deletion

### Requirement: Assign default cost center to counterparty
The system SHALL allow assigning a default cost center to a counterparty. This default is used when booking transactions or incoming invoices for that counterparty.

#### Scenario: Set default cost center on counterparty
- **WHEN** user sets cost center "200 — Marketing" as default on counterparty "Google Ads"
- **THEN** new transactions and incoming invoices for "Google Ads" are pre-assigned to cost center "200"

#### Scenario: Counterparty without cost center
- **WHEN** a counterparty has no default cost center assigned
- **THEN** transactions and invoices for that counterparty have no cost center (null)

#### Scenario: Change default cost center
- **WHEN** user changes the default cost center on a counterparty from "200" to "300"
- **THEN** future transactions use "300"; existing assignments are not retroactively changed

### Requirement: Manually assign cost center to transaction or invoice
The system SHALL allow users to manually assign or change the cost center on individual bank transactions and incoming invoices.

#### Scenario: Assign cost center to transaction
- **WHEN** user assigns cost center "100" to a bank transaction
- **THEN** the transaction's cost center is set to "100"

#### Scenario: Override default cost center
- **WHEN** a transaction's counterparty has default cost center "200" but user assigns "300"
- **THEN** the transaction uses "300" (manual override wins)
