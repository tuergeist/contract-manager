## ADDED Requirements

### Requirement: Create todo item
The system SHALL allow users to create a todo item with text, optional reminder date, and visibility setting. Each todo MUST be bound to exactly one entity: a contract, a contract line item, or a customer.

#### Scenario: Create private todo from contract detail
- **WHEN** user clicks "Add Todo" on a contract detail page and submits with text "Follow up on renewal" and reminder date "2026-03-01"
- **THEN** system creates a private todo linked to that contract, visible only to the creator

#### Scenario: Create public todo from customer detail
- **WHEN** user clicks "Add Todo" on a customer detail page, enters text "Discuss pricing", checks "Share with team", and submits
- **THEN** system creates a public todo linked to that customer, visible to all tenant users

#### Scenario: Create todo from line item
- **WHEN** user clicks "Add Todo" on a contract line item row and submits with text "Check license count"
- **THEN** system creates a todo linked to that specific line item

#### Scenario: Create todo without reminder date
- **WHEN** user creates a todo without specifying a reminder date
- **THEN** system creates the todo with reminder_date as null

### Requirement: View my todos on dashboard
The system SHALL display a "My Todos" section on the dashboard showing all private todos created by the current user, plus any public todos they created.

#### Scenario: Display private todos
- **WHEN** user views the dashboard
- **THEN** system displays their private todos in the "My Todos" section with todo text, linked entity name, and reminder date

#### Scenario: My todos sorted by reminder date
- **WHEN** user has multiple todos with different reminder dates
- **THEN** system displays todos sorted by reminder date ascending, with null dates at the end

### Requirement: View team todos on dashboard
The system SHALL display a "Team Todos" section on the dashboard showing all public todos within the user's tenant, excluding todos created by the current user.

#### Scenario: Display public todos from other users
- **WHEN** user views the dashboard and other tenant users have created public todos
- **THEN** system displays those public todos in the "Team Todos" section

#### Scenario: Team todos show creator
- **WHEN** user views the "Team Todos" section
- **THEN** each todo displays the creator's name alongside the todo text and linked entity

#### Scenario: Tenant isolation for team todos
- **WHEN** user views "Team Todos"
- **THEN** system only shows public todos from users in the same tenant, never from other tenants

### Requirement: Complete todo item
The system SHALL allow users to mark a todo as completed or uncompleted.

#### Scenario: Mark todo as completed
- **WHEN** user clicks the checkbox on an incomplete todo
- **THEN** system marks the todo as completed and visually indicates completion (e.g., strikethrough)

#### Scenario: Unmark completed todo
- **WHEN** user clicks the checkbox on a completed todo
- **THEN** system marks the todo as incomplete and removes completion styling

#### Scenario: Only creator can complete private todo
- **WHEN** user attempts to complete a private todo they did not create
- **THEN** system rejects the action (private todos are not visible to others anyway)

#### Scenario: Any tenant user can complete public todo
- **WHEN** user marks a public todo created by another tenant user as completed
- **THEN** system marks the todo as completed

### Requirement: Delete todo item
The system SHALL allow the creator of a todo to delete it.

#### Scenario: Delete own todo
- **WHEN** user clicks delete on a todo they created
- **THEN** system permanently removes the todo

#### Scenario: Cannot delete others' todos
- **WHEN** user attempts to delete a public todo created by another user
- **THEN** system rejects the action with an appropriate error

### Requirement: Todo modal with context
The system SHALL provide a modal dialog for creating todos that accepts pre-filled context when launched from entity detail pages.

#### Scenario: Modal pre-fills contract context
- **WHEN** user clicks "Add Todo" from contract detail page
- **THEN** modal opens with contract pre-selected and entity selection disabled

#### Scenario: Modal pre-fills customer context
- **WHEN** user clicks "Add Todo" from customer detail page
- **THEN** modal opens with customer pre-selected and entity selection disabled

#### Scenario: Modal allows manual context from dashboard
- **WHEN** user clicks "Add Todo" from dashboard
- **THEN** modal opens with entity selection enabled, requiring user to choose contract, line item, or customer

### Requirement: Todo display shows linked entity
The system SHALL display the linked entity information for each todo item.

#### Scenario: Display contract reference
- **WHEN** todo is linked to a contract
- **THEN** system displays the contract name as a clickable link to the contract detail page

#### Scenario: Display line item reference
- **WHEN** todo is linked to a contract line item
- **THEN** system displays the product name and parent contract name

#### Scenario: Display customer reference
- **WHEN** todo is linked to a customer
- **THEN** system displays the customer name as a clickable link to the customer detail page

### Requirement: Cascade delete with entity
The system SHALL automatically delete todos when their linked entity is deleted.

#### Scenario: Delete todos when contract deleted
- **WHEN** a contract is deleted
- **THEN** all todos linked to that contract or its line items are deleted

#### Scenario: Delete todos when customer deleted
- **WHEN** a customer is deleted
- **THEN** all todos linked to that customer are deleted
