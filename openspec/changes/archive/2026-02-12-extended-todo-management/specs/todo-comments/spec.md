## ADDED Requirements

### Requirement: Todo comment model
The system SHALL store comments on todos with the following data:
- Reference to the parent todo
- Comment text (required, non-empty)
- Author (the user who created the comment)
- Created timestamp (auto-set on creation)

Comments SHALL be immutable once created (no edit or delete).

#### Scenario: Create a comment on a todo
- **WHEN** user submits a comment on a todo with text "Need more info on deadline"
- **THEN** system creates a comment record linked to that todo
- **AND** sets the author to the current user
- **AND** sets created_at to the current timestamp

#### Scenario: Comments are immutable
- **WHEN** a comment exists on a todo
- **THEN** the system SHALL NOT provide any mutation to edit or delete that comment

### Requirement: Query todo comments
The system SHALL provide a way to retrieve all comments for a todo, ordered by creation time (oldest first).

#### Scenario: Fetch comments for a todo
- **WHEN** user queries comments for a todo that has 3 comments
- **THEN** system returns all 3 comments in chronological order
- **AND** each comment includes id, text, author info, and created_at

#### Scenario: Todo with no comments
- **WHEN** user queries comments for a todo that has no comments
- **THEN** system returns an empty list

### Requirement: Add comment mutation
The system SHALL provide an `addTodoComment` mutation that accepts a todo ID and comment text.

#### Scenario: Successfully add a comment
- **WHEN** user calls addTodoComment with valid todo ID and text "Checking with client"
- **THEN** system creates the comment and returns success with the new comment data

#### Scenario: Add comment to non-existent todo
- **WHEN** user calls addTodoComment with an invalid todo ID
- **THEN** system returns an error "Todo not found"

#### Scenario: Add empty comment rejected
- **WHEN** user calls addTodoComment with empty or whitespace-only text
- **THEN** system returns an error "Comment text is required"

### Requirement: Comments visible on todo queries
The system SHALL include a comments field on TodoItemType that returns all comments for that todo.

#### Scenario: Todo includes comments in response
- **WHEN** user queries a todo that has 2 comments
- **THEN** the todo response includes a comments array with both comments
