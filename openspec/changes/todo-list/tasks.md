## 1. Backend Setup

- [x] 1.1 Create new Django app `apps/todos/` with `__init__.py`, `apps.py`, `models.py`, `schema.py`
- [x] 1.2 Register app in `config/settings/base.py` INSTALLED_APPS
- [x] 1.3 Create `TodoItem` model extending `TenantModel` with fields: text, reminder_date, is_public, is_completed, created_by, contract (FK), contract_item (FK), customer (FK)
- [x] 1.4 Add model validation to ensure exactly one of contract/contract_item/customer is set
- [x] 1.5 Create and run migrations

## 2. Backend GraphQL API

- [x] 2.1 Create `TodoItemType` Strawberry type with all fields and linked entity resolution
- [x] 2.2 Add `myTodos` query returning user's private todos + their public todos, sorted by reminder_date
- [x] 2.3 Add `teamTodos` query returning public todos from other tenant users, sorted by reminder_date
- [x] 2.4 Add `createTodo` mutation with inputs: text, reminder_date, is_public, contract_id, contract_item_id, customer_id
- [x] 2.5 Add `updateTodo` mutation for toggling is_completed
- [x] 2.6 Add `deleteTodo` mutation with creator-only permission check
- [x] 2.7 Register todos schema in root Query and Mutation

## 3. Backend Tests

- [x] 3.1 Test TodoItem model validation (exactly one entity required)
- [x] 3.2 Test myTodos query returns correct todos for user
- [x] 3.3 Test teamTodos query excludes own todos and respects tenant isolation
- [x] 3.4 Test createTodo mutation creates todo with correct visibility and entity binding
- [x] 3.5 Test deleteTodo mutation enforces creator-only permission
- [x] 3.6 Test cascade delete when contract/customer is deleted

## 4. Frontend Components

- [x] 4.1 Create `TodoModal` component with form fields: text (required), reminder_date (optional), is_public checkbox
- [x] 4.2 Add entity selector to modal (contract/line item/customer search) - disabled when context is pre-filled
- [x] 4.3 Create `TodoList` component displaying todos with checkbox, text, entity link, reminder date
- [x] 4.4 Add completed todo styling (strikethrough) and toggle functionality
- [x] 4.5 Add delete button with confirmation for todo items

## 5. Frontend Dashboard Integration

- [x] 5.1 Add GraphQL queries for `myTodos` and `teamTodos` in Dashboard
- [x] 5.2 Create "My Todos" section on dashboard with TodoList component
- [x] 5.3 Create "Team Todos" section on dashboard showing creator name
- [x] 5.4 Add "Add Todo" button on dashboard that opens TodoModal without pre-filled context
- [x] 5.5 Wire up todo completion toggle to updateTodo mutation
- [x] 5.6 Wire up todo delete to deleteTodo mutation with optimistic UI update

## 6. Frontend Detail Page Integration

- [x] 6.1 Add "Add Todo" button to ContractDetail page, passing contract context to modal
- [x] 6.2 Add "Add Todo" button to CustomerDetail page, passing customer context to modal
- [x] 6.3 Add "Add Todo" action to contract line item rows, passing line item context to modal

## 7. Translations

- [x] 7.1 Add German translations for todo feature in `de.json`
- [x] 7.2 Add English translations for todo feature in `en.json`
