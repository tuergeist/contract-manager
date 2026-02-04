## Context

The contract-manager application currently lacks integrated task tracking. Users need to remember follow-ups externally. The system already has:
- Multi-tenant architecture with `TenantModel` base class
- User model with tenant association
- Entities: Customer, Contract, ContractItem
- GraphQL API via Strawberry-Django
- React frontend with modal patterns (Shadcn/ui)
- Dashboard page showing KPI cards

## Goals / Non-Goals

**Goals:**
- Allow users to create and manage todo items linked to contracts, line items, or customers
- Support private (creator-only) and public (tenant-wide) visibility
- Display todos on dashboard in two sections: "My Todos" and "Team Todos"
- Provide quick "Add Todo" action from entity detail pages with pre-filled context
- Include reminder dates for time-sensitive follow-ups

**Non-Goals:**
- Email/push notifications for reminders (future enhancement)
- Recurring todos or task templates
- Due date enforcement or overdue tracking
- Assigning todos to other users
- Comments or attachments on todos

## Decisions

### 1. New Django app `apps/todos/`
**Decision**: Create a dedicated `todos` app rather than adding to `contracts`.
**Rationale**: Todos are a cross-cutting concern touching contracts, items, and customers. Separate app keeps concerns clean and avoids bloating the contracts app further.

### 2. Single `TodoItem` model with polymorphic entity reference
**Decision**: Use nullable foreign keys to Contract, ContractItem, and Customer (exactly one must be set).
**Rationale**: Simpler than GenericForeignKey, allows proper FK constraints, and these are the only three entity types. Validation ensures exactly one is set.

```python
class TodoItem(TenantModel):
    text = models.TextField()
    reminder_date = models.DateField(null=True, blank=True)
    is_public = models.BooleanField(default=False)
    is_completed = models.BooleanField(default=False)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)

    # Exactly one of these must be set
    contract = models.ForeignKey(Contract, null=True, blank=True, on_delete=models.CASCADE)
    contract_item = models.ForeignKey(ContractItem, null=True, blank=True, on_delete=models.CASCADE)
    customer = models.ForeignKey(Customer, null=True, blank=True, on_delete=models.CASCADE)
```

### 3. Visibility logic in GraphQL resolver
**Decision**: Filter todos at the resolver level based on visibility rules.
**Rationale**:
- Private todos: `created_by = current_user`
- Public todos: `is_public = True AND tenant = current_user.tenant`
- This keeps the model simple and centralizes access control in the API layer.

### 4. Dashboard integration via separate GraphQL query
**Decision**: Add `myTodos` and `teamTodos` queries rather than modifying `dashboardKpis`.
**Rationale**: Keeps concerns separated, allows independent caching, and the dashboard can fetch them in parallel.

### 5. Modal component for todo creation
**Decision**: Reusable `TodoModal` component that accepts optional pre-filled context.
**Rationale**: Single component used from dashboard (manual context selection) and from detail pages (pre-filled context). Uses existing Shadcn Dialog pattern.

## Risks / Trade-offs

**Risk**: Orphaned todos when linked entity is deleted.
→ **Mitigation**: Use `on_delete=CASCADE` - todos are deleted with their parent entity. This matches user expectation (todo about deleted contract is meaningless).

**Risk**: Performance with many todos on dashboard.
→ **Mitigation**: Limit queries to most recent N todos (e.g., 20), sorted by reminder_date. Add pagination later if needed.

**Risk**: Confusion about what "public" means.
→ **Mitigation**: Clear UI labels: "My Todos" (private) vs "Team Todos" (shared with team). Tooltip explanation on the checkbox.
