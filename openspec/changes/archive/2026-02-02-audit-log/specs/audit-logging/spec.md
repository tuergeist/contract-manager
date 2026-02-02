## ADDED Requirements

### Requirement: System automatically logs entity changes

The system SHALL automatically create an audit log entry whenever a tracked entity is created, updated, or deleted.

#### Scenario: Contract created
- **WHEN** a user creates a new contract
- **THEN** system creates an audit log entry with action "create"
- **AND** the entry includes all field values of the new contract

#### Scenario: Contract updated
- **WHEN** a user updates a contract's fields
- **THEN** system creates an audit log entry with action "update"
- **AND** the entry includes old and new values for each changed field

#### Scenario: Contract deleted
- **WHEN** a user deletes a contract
- **THEN** system creates an audit log entry with action "delete"
- **AND** the entry includes the final state of the deleted contract

#### Scenario: Customer changes logged
- **WHEN** a customer is created, updated, or deleted
- **THEN** system creates an audit log entry for the change

#### Scenario: Contract item changes logged
- **WHEN** a contract item is created, updated, or deleted
- **THEN** system creates an audit log entry for the change
- **AND** the entry references the parent contract

### Requirement: Audit log entries contain complete change information

Each audit log entry SHALL contain all information needed to understand what changed, who made the change, and when.

#### Scenario: Entry contains required fields
- **WHEN** an audit log entry is created
- **THEN** it SHALL include: tenant, action type, entity type, entity ID, entity display name, timestamp, and changes data

#### Scenario: Entry records the user
- **WHEN** an authenticated user makes a change
- **THEN** the audit log entry records which user made the change

#### Scenario: System changes have null user
- **WHEN** a change is made by the system (e.g., automated process)
- **THEN** the audit log entry has a null user reference

#### Scenario: Changes stored as field-level diff
- **WHEN** an entity is updated
- **THEN** the changes field contains a JSON object with field names as keys
- **AND** each field has "old" and "new" values showing what changed

### Requirement: Audit logs are tenant-scoped

The system SHALL ensure audit logs respect multi-tenant isolation.

#### Scenario: Audit logs belong to tenant
- **WHEN** an audit log entry is created
- **THEN** it is associated with the same tenant as the changed entity

#### Scenario: Users only see their tenant's logs
- **WHEN** a user queries audit logs
- **THEN** they only see entries for their own tenant
- **AND** entries from other tenants are never visible

### Requirement: Audit logs can be queried via GraphQL

The system SHALL provide a GraphQL query for retrieving audit logs with filtering and pagination.

#### Scenario: Query all audit logs
- **WHEN** user queries auditLogs without filters
- **THEN** system returns all audit logs for the user's tenant
- **AND** results are ordered by timestamp descending (newest first)

#### Scenario: Filter by entity type
- **WHEN** user queries auditLogs with entityType filter
- **THEN** system returns only entries for that entity type

#### Scenario: Filter by entity ID
- **WHEN** user queries auditLogs with entityType and entityId filters
- **THEN** system returns only entries for that specific entity

#### Scenario: Filter by user
- **WHEN** user queries auditLogs with userId filter
- **THEN** system returns only entries made by that user

#### Scenario: Paginated results
- **WHEN** user queries auditLogs with pagination parameters
- **THEN** system returns a connection with edges, pageInfo, and totalCount
- **AND** cursor-based pagination allows fetching subsequent pages

### Requirement: Related entity changes are queryable together

The system SHALL allow querying changes to an entity and its related entities together.

#### Scenario: Contract with item changes
- **WHEN** user queries audit logs for a contract
- **THEN** they can include changes to the contract's items
- **AND** entries are combined and sorted by timestamp
