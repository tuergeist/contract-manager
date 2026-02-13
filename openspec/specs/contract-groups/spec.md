## ADDED Requirements

### Requirement: Contract group model
The system SHALL provide a ContractGroup model that belongs to a Customer and has a name. Groups are tenant-scoped through their customer relationship.

#### Scenario: Create contract group
- **WHEN** user creates a group with name "Maintenance Contracts" for customer ID 5
- **THEN** a ContractGroup record is created with customer_id=5 and name="Maintenance Contracts"

#### Scenario: Group name uniqueness per customer
- **WHEN** user tries to create a group with the same name as an existing group for the same customer
- **THEN** the system SHALL reject the creation with an error

### Requirement: Contract group assignment
The system SHALL allow assigning a contract to a group. A contract MAY belong to zero or one group. The group MUST belong to the same customer as the contract.

#### Scenario: Assign contract to group
- **WHEN** user assigns contract ID 100 to group ID 10
- **AND** both contract and group belong to the same customer
- **THEN** contract.group is set to the group

#### Scenario: Prevent cross-customer assignment
- **WHEN** user tries to assign a contract to a group belonging to a different customer
- **THEN** the system SHALL reject the assignment with an error

#### Scenario: Unassign contract from group
- **WHEN** user sets contract's group to null
- **THEN** the contract is ungrouped

### Requirement: Create contract group mutation
The system SHALL provide a GraphQL mutation `createContractGroup(customerId, name)` that creates a new group. Requires `contracts.write` permission.

#### Scenario: Create group via GraphQL
- **WHEN** authenticated user with contracts.write calls createContractGroup(customerId: 5, name: "Support")
- **THEN** a new ContractGroup is created and returned

#### Scenario: Create group without permission
- **WHEN** user without contracts.write calls createContractGroup
- **THEN** the system returns a permission denied error

### Requirement: Update contract group mutation
The system SHALL provide a GraphQL mutation `updateContractGroup(groupId, name)` to rename a group. Requires `contracts.write` permission.

#### Scenario: Rename group via GraphQL
- **WHEN** authenticated user calls updateContractGroup(groupId: 10, name: "New Name")
- **THEN** the group's name is updated

### Requirement: Delete contract group mutation
The system SHALL provide a GraphQL mutation `deleteContractGroup(groupId)` to delete a group. Contracts in the group SHALL have their group set to null. Requires `contracts.write` permission.

#### Scenario: Delete group with contracts
- **WHEN** user deletes a group that has 3 contracts assigned
- **THEN** the group is deleted
- **AND** the 3 contracts have their group set to null (not deleted)

### Requirement: Query contract groups
The system SHALL provide a GraphQL query `contractGroups(customerId)` returning all groups for a customer.

#### Scenario: List groups for customer
- **WHEN** user queries contractGroups(customerId: 5)
- **THEN** all groups belonging to customer 5 are returned with id, name, and contract count

### Requirement: Assign contract to group mutation
The system SHALL provide a GraphQL mutation `assignContractToGroup(contractId, groupId)` where groupId can be null to unassign. Requires `contracts.write` permission.

#### Scenario: Assign via mutation
- **WHEN** user calls assignContractToGroup(contractId: 100, groupId: 10)
- **THEN** the contract's group is updated

#### Scenario: Unassign via mutation
- **WHEN** user calls assignContractToGroup(contractId: 100, groupId: null)
- **THEN** the contract's group is set to null

### Requirement: Contract type includes group
The ContractType GraphQL type SHALL include a `group` field returning the ContractGroup (or null).

#### Scenario: Query contract with group
- **WHEN** user queries a contract that belongs to group "Maintenance"
- **THEN** the response includes `group: { id, name }`

### Requirement: Customer contracts list shows group
The customer detail page contracts table SHALL display the group name for each contract, or indicate "ungrouped" if no group.

#### Scenario: Display grouped contract
- **WHEN** viewing customer detail with a contract in group "Support"
- **THEN** the contracts table shows "Support" in the group column

#### Scenario: Display ungrouped contract
- **WHEN** viewing customer detail with a contract not in any group
- **THEN** the contracts table shows empty or "-" in the group column

### Requirement: Inline group editing in customer contracts list
The customer detail page SHALL allow changing a contract's group directly from the contracts table via a dropdown/popover, without navigating away.

#### Scenario: Change group inline
- **WHEN** user clicks on a contract's group cell and selects a different group
- **THEN** the contract's group is updated immediately
- **AND** the UI reflects the change without page reload

#### Scenario: Create new group inline
- **WHEN** user is assigning a group and types a new name that doesn't exist
- **THEN** user can create the new group and assign it in one action

### Requirement: Contract edit page group selector
The contract edit page (`/contracts/:id/edit`) overview section SHALL include a group selector dropdown showing groups for the contract's customer.

#### Scenario: Select group in contract form
- **WHEN** user edits contract and selects "Maintenance" from group dropdown
- **AND** saves the contract
- **THEN** the contract's group is set to "Maintenance"

#### Scenario: Group dropdown shows customer's groups
- **WHEN** user opens contract edit page for a contract belonging to customer X
- **THEN** the group dropdown shows only groups belonging to customer X
