## 1. Backend: TodoComment Model

- [x] 1.1 Create TodoComment model with todo FK, text, author FK, created_at
- [x] 1.2 Add migration for TodoComment model
- [x] 1.3 Add commentCount property to TodoItem model

## 2. Backend: Comment GraphQL

- [x] 2.1 Create TodoCommentType with id, text, author, createdAt fields
- [x] 2.2 Add comments field to TodoItemType (returns list of TodoCommentType)
- [x] 2.3 Add addTodoComment mutation with todo ID and text input
- [x] 2.4 Validate comment text is non-empty in mutation
- [x] 2.5 Add commentCount field to TodoItemType

## 3. Backend: Reassign and Queries

- [x] 3.1 Add reassignTodoToSelf mutation
- [x] 3.2 Enforce permission check: can only reassign public todos or own todos
- [x] 3.3 Add todosByAssignee query returning todos grouped by assignee
- [x] 3.4 Extend customerTodos query to include todos from customer's contracts
- [x] 3.5 Add myTodos query for current user's assigned and created todos

## 4. Backend: Tests

- [x] 4.1 Add tests for TodoComment creation
- [x] 4.2 Add tests for addTodoComment mutation (success, empty text, not found)
- [x] 4.3 Add tests for reassignTodoToSelf mutation (success, private todo error)
- [x] 4.4 Add tests for todosByAssignee query
- [x] 4.5 Add tests for customerTodos including contract todos

## 5. Frontend: Todo Board Page

- [x] 5.1 Create /todos route in App.tsx
- [x] 5.2 Add "Todos" entry to Sidebar navigation
- [x] 5.3 Create TodoBoard component with column layout
- [x] 5.4 Implement todosByAssignee GraphQL query
- [x] 5.5 Render columns per assignee with current user first
- [x] 5.6 Render "Unassigned" column for todos without assignee

## 6. Frontend: Todo Card Component

- [x] 6.1 Create TodoCard component showing text, date, entity link, status
- [x] 6.2 Add completion checkbox with toggle mutation
- [x] 6.3 Add comment count badge
- [x] 6.4 Add entity link that navigates to contract/customer detail

## 7. Frontend: Board Interactions

- [x] 7.1 Integrate @dnd-kit for drag-drop between columns
- [x] 7.2 Implement reassign mutation on drop
- [x] 7.3 Add inline edit modal/popover for todo editing
- [x] 7.4 Add delete action with confirmation
- [x] 7.5 Add filter for completion status (show/hide completed)
- [x] 7.6 Add search input to filter todos by text

## 8. Frontend: Comments UI

- [x] 8.1 Create TodoComments component showing comment thread
- [x] 8.2 Add comment input form with submit
- [x] 8.3 Integrate comments into TodoCard expand/modal view
- [x] 8.4 Wire up addTodoComment mutation

## 9. Frontend: Customer Detail Aggregation

- [x] 9.1 Update CustomerDetail to fetch todos including contract todos
- [x] 9.2 Display contract reference on todos from contracts
- [x] 9.3 Ensure todo actions (edit, complete, comment) work in customer view

## 10. Localization

- [x] 10.1 Add English translations for new todo UI strings
- [x] 10.2 Add German translations for new todo UI strings
