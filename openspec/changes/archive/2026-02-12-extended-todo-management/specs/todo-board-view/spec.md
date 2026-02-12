## ADDED Requirements

### Requirement: Todos navigation entry
The system SHALL add a "Todos" entry to the main navigation menu, linking to `/todos`.

#### Scenario: Todos visible in navigation
- **WHEN** user views the sidebar navigation
- **THEN** a "Todos" menu item is visible
- **AND** clicking it navigates to `/todos`

### Requirement: Board view layout
The system SHALL display todos in a Kanban-style board with columns representing assignees.

#### Scenario: Board displays columns per assignee
- **WHEN** user views the todo board and there are todos assigned to users Alice and Bob
- **THEN** board displays a column for Alice and a column for Bob
- **AND** each column shows that user's assigned todos

#### Scenario: Current user column appears first
- **WHEN** user Alice views the todo board
- **THEN** Alice's column appears as the leftmost column

#### Scenario: Unassigned todos column
- **WHEN** there are todos with no assignee
- **THEN** board displays an "Unassigned" column containing those todos

#### Scenario: Empty assignee columns hidden
- **WHEN** a user has no assigned todos
- **THEN** that user's column is not displayed (except for the current user)

### Requirement: Todo card display
Each todo on the board SHALL display as a card showing:
- Todo text (truncated if long)
- Reminder date (if set)
- Entity link (contract/customer name, clickable)
- Completion status indicator
- Comment count (if any)

#### Scenario: Todo card shows key info
- **WHEN** a todo card is displayed
- **THEN** it shows the todo text, reminder date, linked entity, and completion status

#### Scenario: Entity link navigates to detail
- **WHEN** user clicks the entity link on a todo card
- **THEN** user is navigated to that contract or customer's detail page

### Requirement: Inline todo editing
The system SHALL allow editing a todo directly from the board view.

#### Scenario: Edit todo text inline
- **WHEN** user clicks edit on a todo card
- **THEN** a form or modal appears allowing edits to text, reminder date, and assignee
- **AND** saving updates the todo

#### Scenario: Complete todo from board
- **WHEN** user clicks the complete checkbox on a todo card
- **THEN** todo is marked as completed
- **AND** card visually indicates completion (e.g., strikethrough, muted colors)

#### Scenario: Delete todo from board
- **WHEN** user clicks delete on a todo card and confirms
- **THEN** todo is deleted from the system

### Requirement: Reassign via drag-drop
The system SHALL allow reassigning a todo by dragging its card to a different assignee column.

#### Scenario: Drag todo to another user's column
- **WHEN** user drags a todo card from Alice's column to Bob's column
- **THEN** todo is reassigned to Bob
- **AND** card moves to Bob's column

#### Scenario: Drag todo to unassigned column
- **WHEN** user drags a todo card to the Unassigned column
- **THEN** todo's assignee is set to null

### Requirement: Add comment from board
The system SHALL allow adding comments to a todo from the board view.

#### Scenario: Add comment via card action
- **WHEN** user clicks comment icon on a todo card
- **THEN** a comment input appears (inline or modal)
- **AND** submitting adds the comment to the todo

### Requirement: Filter and search
The system SHALL provide filtering options on the board.

#### Scenario: Filter by completion status
- **WHEN** user selects "Show completed" filter
- **THEN** board includes completed todos (normally hidden or at bottom)

#### Scenario: Search todos
- **WHEN** user types "deadline" in search box
- **THEN** only todos containing "deadline" in text are shown

### Requirement: Board respects permissions
The system SHALL respect todo visibility rules (is_public, created_by) when displaying the board.

#### Scenario: Private todos only visible to creator
- **WHEN** user views board and there are private todos created by other users
- **THEN** those private todos are not visible to the current user
