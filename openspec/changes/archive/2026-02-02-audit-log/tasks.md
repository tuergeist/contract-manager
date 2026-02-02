## 1. Backend - Audit Log Model

- [x] 1.1 Create `apps/audit/` Django app with basic structure
- [x] 1.2 Create `AuditLog` model with fields: tenant, action, entity_type, entity_id, entity_repr, user, changes, timestamp
- [x] 1.3 Add database indexes for efficient querying (entity_type, entity_id, user, timestamp)
- [x] 1.4 Create and run migrations

## 2. Backend - Change Capture Service

- [x] 2.1 Create `AuditLogService` with methods for logging create/update/delete
- [x] 2.2 Implement `compute_diff()` to compare old and new field values
- [x] 2.3 Add `pre_save` signal handler to snapshot existing instance state
- [x] 2.4 Add `post_save` signal handler to compute diff and create log entry
- [x] 2.5 Add `post_delete` signal handler to log deletions
- [x] 2.6 Register signals for Contract, ContractItem, Customer, Product models
- [x] 2.7 Add thread-local storage to track current user from request context

## 3. Backend - GraphQL API

- [x] 3.1 Create `AuditLogType` and `AuditLogChangeType` Strawberry types
- [x] 3.2 Implement cursor-based pagination connection type
- [x] 3.3 Add `auditLogs` query with filters: entityType, entityId, userId, action
- [x] 3.4 Add includeRelated option to include child entity changes (e.g., contract items)
- [x] 3.5 Ensure tenant-scoping in all queries

## 4. Backend - Tests

- [x] 4.1 Add unit tests for AuditLogService diff computation
- [x] 4.2 Add tests for signal handlers (create, update, delete scenarios)
- [x] 4.3 Add tests for GraphQL query with various filters
- [x] 4.4 Add tests for tenant isolation
- [x] 4.5 Add tests for related entity queries

## 5. Frontend - Audit Log Components

- [x] 5.1 Create `AuditLogTable` component with columns: timestamp, user, action, entity, changes summary
- [x] 5.2 Add action type badges with color coding (green=create, blue=update, red=delete)
- [x] 5.3 Implement expandable row to show field-level changes
- [x] 5.4 Add entity name links that navigate to detail pages
- [x] 5.5 Create `AuditLogChanges` component to display old/new value pairs
- [x] 5.6 Add human-readable field name formatting

## 6. Frontend - Global Audit Log Page

- [x] 6.1 Create `/audit-log` route in React Router
- [x] 6.2 Add "Audit Log" link to main navigation
- [x] 6.3 Create `AuditLogPage` component using `AuditLogTable`
- [x] 6.4 Implement GraphQL query hook for `auditLogs`
- [x] 6.5 Add filter controls: entity type dropdown, action type dropdown, date range picker
- [x] 6.6 Implement cursor-based pagination with "Load More" button
- [x] 6.7 Show total count of matching entries

## 7. Frontend - Activity Tabs

- [x] 7.1 Add "Activity" tab to ContractDetail page
- [x] 7.2 Query audit logs filtered by contract ID (include contract items)
- [x] 7.3 Add "Activity" tab to CustomerDetail page
- [x] 7.4 Query audit logs filtered by customer ID

## 8. Localization

- [x] 8.1 Add German translations to `de.json` for audit log UI
- [x] 8.2 Add English translations to `en.json` for audit log UI
- [x] 8.3 Add field name translations for human-readable display
- [x] 8.4 Add action type translations (Erstellt/Created, Aktualisiert/Updated, Gelöscht/Deleted)

## 9. Testing

- [x] 9.1 Add E2E test for global audit log page
- [x] 9.2 Add E2E test for contract activity tab
- [x] 9.3 Test filtering and pagination functionality
