## Why

The contract manager currently has no visibility into who changed what and when. For compliance, troubleshooting, and accountability, users need to see a history of all modifications to contracts, customers, and other entities. This audit trail is essential for business operations where multiple users manage contracts and changes need to be traceable.

## What Changes

- Add automatic audit logging for all create, update, and delete operations
- Store detailed change information including old/new values for modified fields
- Provide a global audit log view showing all system activity
- Provide filtered audit views on contract and customer detail pages
- Link audit entries to the affected entities for easy navigation
- Record the user who made each change and when

## Capabilities

### New Capabilities
- `audit-logging`: Core audit log infrastructure - capturing changes, storing audit entries, and providing query APIs
- `audit-log-ui`: User interface for viewing audit logs - global view, entity-specific views, and filtering

### Modified Capabilities

None - this is additive functionality that doesn't change existing spec-level behavior.

## Impact

- **Backend**: New `audit` Django app with AuditLog model, signals/middleware to capture changes, GraphQL queries for retrieving logs
- **Frontend**: New audit log components, integration into contract and customer detail pages, new global audit log page
- **Database**: New audit_log table with indexes for efficient querying by entity, user, and date
- **Performance**: Minimal overhead - audit writes are append-only; reads are paginated
