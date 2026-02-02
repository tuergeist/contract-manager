## Context

The contract manager has multiple users editing contracts, customers, and products. Currently there's no way to see who changed what or when. All tenant models inherit from `TenantModel` which provides `created_at` and `updated_at` timestamps, but no change history.

**Current state:**
- Models: Contract, ContractItem, Customer, Product (all TenantModel subclasses)
- No audit infrastructure exists
- GraphQL mutations handle creates/updates but don't log changes
- Multi-tenant architecture requires audit logs to be tenant-scoped

## Goals / Non-Goals

**Goals:**
- Automatically capture all create, update, and delete operations on auditable models
- Store field-level changes with old/new values
- Provide efficient querying by entity, user, and date range
- Display audit history in the UI with links to affected entities
- Keep the implementation simple and maintainable

**Non-Goals:**
- Audit log for read operations (too noisy, not typically required)
- Real-time notifications on changes (future feature)
- Audit log export/reporting (can be added later)
- Retention policies or automatic cleanup (manual for now)
- Auditing authentication events like login/logout (separate concern)

## Decisions

### 1. Use Django signals for change capture

**Decision:** Use Django's `post_save` and `post_delete` signals to capture changes automatically.

**Rationale:**
- Works at the model layer, catches all changes regardless of how they're made (GraphQL, admin, shell)
- No need to modify every mutation or view
- Well-understood Django pattern

**Alternative considered:** Middleware or GraphQL mutation wrappers - rejected because they wouldn't catch admin or shell changes.

### 2. Store changes as JSON in a single table

**Decision:** Single `AuditLog` model with a `changes` JSONField storing the diff.

```python
class AuditLog(TenantModel):
    action = CharField  # 'create', 'update', 'delete'
    entity_type = CharField  # 'contract', 'customer', etc.
    entity_id = IntegerField
    entity_repr = CharField  # Human-readable name at time of change
    user = ForeignKey(User, null=True)  # null for system changes
    changes = JSONField  # {"field": {"old": x, "new": y}, ...}
    timestamp = DateTimeField
```

**Rationale:**
- Simple schema, easy to query
- JSON allows flexible change storage without schema migrations
- Single table simplifies indexing and querying

**Alternative considered:** Separate tables per entity type - rejected as over-engineering for this use case.

### 3. Track changes via model instance comparison

**Decision:** On `pre_save`, snapshot the current DB state. On `post_save`, compare with the new state to compute the diff.

**Rationale:**
- Gives accurate old/new values for each field
- Works with Django's ORM without modifications

**Implementation:**
- Use a signal handler that queries the existing instance before save
- Compare field values to detect what changed
- Only log fields that actually changed (not all fields)

### 4. GraphQL query with cursor-based pagination

**Decision:** Expose audit logs via GraphQL with filtering and cursor pagination.

```graphql
type Query {
  auditLogs(
    entityType: String
    entityId: Int
    userId: Int
    after: String
    first: Int
  ): AuditLogConnection!
}
```

**Rationale:**
- Consistent with existing GraphQL patterns in the app
- Cursor pagination handles large log volumes efficiently
- Filtering by entity allows showing logs on detail pages

### 5. UI as tabs/sections on existing pages plus global view

**Decision:**
- Add "Activity" tab to Contract and Customer detail pages
- Add global "Audit Log" page accessible from navigation
- Both use the same `AuditLogTable` component with different filters

**Rationale:**
- Contextual: see activity where you're working
- Global: admin overview of all system activity
- Reusable component reduces duplication

## Risks / Trade-offs

**[Performance] High-write workloads** → Audit writes are append-only and async-friendly. If needed, can move to async task queue later. Monitor write latency.

**[Storage] Log growth over time** → Audit logs can grow large. Add created_at index for efficient date filtering. Plan for future retention policy.

**[Complexity] Tracking related entity changes** → When a ContractItem changes, do we show it on Contract's log? Decision: Yes, query by entity_type IN ('contract', 'contract_item') with parent lookup.

**[Data] Sensitive field exposure** → Some fields might be sensitive. Decision: Audit all fields initially, add field exclusion list if needed.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Django Models                           │
│  Contract, ContractItem, Customer, Product                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼ (signals: pre_save, post_save, post_delete)
┌─────────────────────────────────────────────────────────────┐
│                   AuditLogService                           │
│  - capture_pre_save(instance)                               │
│  - capture_post_save(instance, created)                     │
│  - capture_delete(instance)                                 │
│  - compute_diff(old, new)                                   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    AuditLog Model                           │
│  tenant, action, entity_type, entity_id, user, changes      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   GraphQL Schema                            │
│  auditLogs(entityType, entityId, ...) → AuditLogConnection  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      Frontend                               │
│  AuditLogTable component                                    │
│  - Global audit log page                                    │
│  - Contract detail Activity tab                             │
│  - Customer detail Activity tab                             │
└─────────────────────────────────────────────────────────────┘
```
