## Why

Users need a way to track follow-up tasks related to contracts, line items, and customers without leaving the application. Currently, there's no integrated task management, forcing users to rely on external tools or memory for reminders like "renew contract X" or "follow up on pricing with customer Y".

## What Changes

- Add a `TodoItem` model that stores tasks bound to entities (contract, line item, customer)
- Users can create private (only visible to themselves) or public (visible to all tenant users) todo items
- Each todo item has: text description, reminder date, visibility (private/public), and entity binding
- Add "Add Todo" button accessible from contract detail, line item rows, and customer detail pages
- Modal for creating/editing todos with context pre-filled based on where the button was clicked
- Dashboard shows todo list separated into two sections:
  - **My Todos**: Private todos created by the current user
  - **Team Todos**: Public todos visible to all tenant users
  - Each entry displays: todo text, referenced entity (contract/line item/customer), and reminder date

## Capabilities

### New Capabilities
- `todo-management`: CRUD operations for todo items with visibility control and entity binding

### Modified Capabilities
<!-- None - this is a new standalone feature -->

## Impact

- **Backend**: New `TodoItem` model in `apps/todos/` app, GraphQL mutations/queries
- **Frontend**: New modal component, todo list sections on dashboard, "Add Todo" buttons on detail pages
- **Database**: New table for todo items with foreign keys to contracts, contract items, customers
- **Permissions**: Todos respect tenant isolation; private todos only visible to creator
