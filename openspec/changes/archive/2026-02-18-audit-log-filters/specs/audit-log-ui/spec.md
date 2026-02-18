## MODIFIED Requirements

### Requirement: Audit log supports filtering

The system SHALL allow users to filter audit log entries on the global page by entity type, action type, user, date range, and entity name text search.

#### Scenario: Filter by entity type
- **WHEN** user selects an entity type filter
- **THEN** table shows only entries for that entity type

#### Scenario: Filter by action type
- **WHEN** user selects an action type filter (create/update/delete)
- **THEN** table shows only entries with that action

#### Scenario: Filter by user
- **WHEN** user selects a user from the user filter dropdown
- **THEN** table shows only entries made by that user

#### Scenario: Filter by date range
- **WHEN** user sets a "from" date
- **THEN** table shows only entries with timestamp on or after that date

#### Scenario: Filter by date range end
- **WHEN** user sets a "to" date
- **THEN** table shows only entries with timestamp on or before that date

#### Scenario: Search by entity name
- **WHEN** user types text into the search input
- **THEN** table shows only entries whose entity name contains the search text (case-insensitive)
- **AND** the query SHALL be debounced (300ms) to avoid excessive requests

#### Scenario: Combine multiple filters
- **WHEN** user sets multiple filters simultaneously
- **THEN** table shows only entries matching all active filters (AND logic)

#### Scenario: Clear filters
- **WHEN** user clears filters
- **THEN** table shows all entries again

#### Scenario: Filters reset pagination
- **WHEN** user changes any filter value
- **THEN** pagination SHALL reset to the first page
