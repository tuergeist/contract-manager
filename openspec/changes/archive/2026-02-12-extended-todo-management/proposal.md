## Why

The current todo system is basic—todos are only visible in their linked entity's detail page (contract or customer), there's no way to collaborate on todos via comments, and users can't easily see all their work across entities. A dedicated board view with assignee columns and the ability to comment and reassign would make todos a proper lightweight task management system.

## What Changes

- Show todos from a customer's contracts aggregated on the customer detail page (in addition to customer-specific todos)
- Add immutable comments (answers) to todos, visible as a thread
- Allow any user to reassign a todo to themselves ("take over")
- Add a new dedicated "Todos" page with a Kanban-style board view:
  - One column per assignee (users with assigned todos)
  - Current user's column appears first
  - Unassigned todos in a separate column
  - Full CRUD operations available inline (edit, complete, delete, reassign, comment)
- Add "Todos" to the main navigation menu

## Capabilities

### New Capabilities
- `todo-comments`: Immutable comment/answer system for todos with author and timestamp
- `todo-board-view`: Kanban-style board UI with columns per assignee, drag-drop reassignment, and inline editing

### Modified Capabilities
- `todo-management`: Add reassign-to-self mutation, aggregate contract todos under customer view, update queries to include comments

## Impact

- **Backend**:
  - New `TodoComment` model with todo FK, author, text, created_at
  - New `todoComments` query and `addTodoComment` mutation
  - New `reassignTodoToSelf` mutation (or extend updateTodo)
  - Extend customer todos query to include contract todos
- **Frontend**:
  - New `/todos` route and TodoBoard component
  - Add Todos to sidebar navigation
  - CustomerDetail: show aggregated todos from contracts
  - TodoItem component: show comments thread, add comment form
- **Dependencies**: May want a drag-drop library for board (e.g., @dnd-kit already in use)
