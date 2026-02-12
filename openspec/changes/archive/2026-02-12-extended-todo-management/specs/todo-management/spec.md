## ADDED Requirements

### Requirement: Reassign todo to self
The system SHALL allow any user to reassign a public todo to themselves.

#### Scenario: User takes over unassigned todo
- **WHEN** user calls reassignTodoToSelf on a todo with no current assignee
- **THEN** todo's assigned_to is set to the current user

#### Scenario: User takes over todo from another user
- **WHEN** user Bob calls reassignTodoToSelf on a todo currently assigned to Alice
- **THEN** todo's assigned_to is changed from Alice to Bob

#### Scenario: Cannot reassign private todo of another user
- **WHEN** user tries to reassign a private todo they did not create
- **THEN** system returns an error "Cannot reassign private todo"

#### Scenario: Reassign own todo to self is no-op
- **WHEN** user calls reassignTodoToSelf on a todo already assigned to themselves
- **THEN** system returns success (no change needed)

### Requirement: Customer view shows contract todos
The system SHALL display todos from all of a customer's contracts on the customer detail page, in addition to direct customer todos.

#### Scenario: Customer with contract todos
- **WHEN** user views customer "Acme Corp" detail page
- **AND** Acme Corp has 2 direct todos and 3 contracts with 5 total todos
- **THEN** the todos section shows all 7 todos
- **AND** each todo indicates its source (customer vs which contract)

#### Scenario: Contract todos show contract reference
- **WHEN** a todo is linked to a contract (not directly to customer)
- **THEN** the todo displays the contract name/reference in the customer view

### Requirement: Query all user todos
The system SHALL provide a query to fetch all todos for the current user (assigned to them or created by them), across all entities.

#### Scenario: Fetch user's todos across entities
- **WHEN** user queries their todos
- **THEN** system returns todos where user is assignee OR creator
- **AND** includes todos from contracts, contract items, and customers

#### Scenario: Query supports filtering
- **WHEN** user queries todos with filter isCompleted=false
- **THEN** only incomplete todos are returned

### Requirement: Query todos by assignee
The system SHALL provide a query to fetch todos grouped by assignee for the board view.

#### Scenario: Fetch todos grouped for board
- **WHEN** board queries todos for display
- **THEN** system returns todos with assignee information
- **AND** includes unassigned todos (assignee=null)

### Requirement: Include comments count
The system SHALL include a comment count on todo queries for efficient display.

#### Scenario: Todo shows comment count
- **WHEN** user queries todos
- **THEN** each todo includes a commentCount field with the number of comments
