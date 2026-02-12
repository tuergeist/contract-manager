## Context

The todo system currently supports basic CRUD operations on todos linked to contracts, contract items, or customers. Todos have an `assigned_to` field and visibility control (`is_public`). The system lacks collaboration features (comments), a unified view across entities, and the ability for non-owners to take ownership.

The frontend uses React with Shadcn/ui components and @dnd-kit for drag-and-drop (already used in contract items reordering). The backend uses Django with Strawberry-GraphQL.

## Goals / Non-Goals

**Goals:**
- Enable lightweight collaboration on todos via immutable comments
- Provide a Kanban-style board view for managing all todos across entities
- Allow users to self-assign ("take over") todos they can view
- Show contract-related todos aggregated on customer detail pages

**Non-Goals:**
- Full project management features (subtasks, dependencies, priorities)
- Real-time collaboration (WebSocket updates)
- Notifications/email for todo assignments or comments
- Workflow automation (auto-assignment rules)

## Decisions

### 1. TodoComment as separate model (not JSON field)

**Decision:** Create a `TodoComment` Django model with FK to `TodoItem`.

**Rationale:**
- Enables proper querying, indexing, and audit logging
- Consistent with existing patterns (all entities are models)
- Allows future extensions (reactions, mentions) without migrations

**Alternatives considered:**
- JSON field on TodoItem: Simpler but no relational integrity, harder to query

### 2. Comments are immutable (no edit/delete)

**Decision:** Once created, comments cannot be modified or deleted.

**Rationale:**
- Simplifies implementation (no update/delete mutations)
- Provides audit trail—what was said stays said
- Common pattern in task management systems (like GitHub issue comments being edit-tracked)

### 3. Board view uses existing GraphQL queries with new grouping

**Decision:** Add a `todosByAssignee` query that returns todos grouped by assignee, rather than fetching all and grouping client-side.

**Rationale:**
- Server-side grouping is more efficient for large todo counts
- Allows pagination per column if needed later
- Client still receives structured data ready for display

**Alternatives considered:**
- Client-side grouping: Simpler but doesn't scale, wasteful re-renders

### 4. Drag-drop uses @dnd-kit (already in project)

**Decision:** Reuse @dnd-kit for drag-drop reassignment on the board.

**Rationale:**
- Already a dependency (used for contract item reordering)
- Well-documented, accessible, performant
- Consistent DX across the codebase

### 5. Reassign-to-self as dedicated mutation

**Decision:** Add `reassignTodoToSelf` mutation rather than extending `updateTodo`.

**Rationale:**
- Clearer intent and permissions model
- Can enforce "you can only assign TO yourself" without complex permission logic
- `updateTodo` remains for owner/admin edits only

**Alternatives considered:**
- Extend `updateTodo` with conditional logic: More complex permission checks

### 6. Customer aggregation via resolver, not denormalization

**Decision:** The `customerTodos` query will union direct customer todos with todos from the customer's contracts, computed at query time.

**Rationale:**
- No data duplication or sync issues
- Contracts already have customer FK, so the join is straightforward
- Keeps single source of truth for each todo

## Risks / Trade-offs

**[Performance] Large comment threads** → Paginate comments if count exceeds threshold (defer to v2 if needed)

**[UX] Board with many assignees** → Limit visible columns, add horizontal scroll, or collapse inactive users

**[Complexity] Permission checks on board** → Reuse existing `is_public`/`created_by` logic; board query filters server-side

**[Migration] None required** → New model (TodoComment) is additive; no existing data changes

## Open Questions

- Should completed todos be hidden by default on the board, or shown in a muted style?
- Should the board support filtering by entity type (contracts only, customers only)?
- Maximum comment length limit?
