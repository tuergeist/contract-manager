# audit-log-ui Specification

## Purpose
TBD - created by archiving change audit-log. Update Purpose after archive.
## Requirements
### Requirement: User can access global audit log page

The system SHALL provide a global audit log page accessible from the main navigation.

#### Scenario: Navigate to audit log
- **WHEN** user clicks "Audit Log" in navigation
- **THEN** system displays the global audit log page at `/audit-log`
- **AND** page shows all recent activity across the tenant

#### Scenario: Page requires authentication
- **WHEN** unauthenticated user accesses `/audit-log`
- **THEN** system redirects to login page

### Requirement: Audit log displays as a table

The system SHALL display audit log entries in a table format with relevant columns.

#### Scenario: Table shows entry details
- **WHEN** audit log table is displayed
- **THEN** each row shows: timestamp, user name, action, entity type, entity name, and summary of changes

#### Scenario: Timestamp formatted for locale
- **WHEN** audit log entry is displayed
- **THEN** timestamp is formatted according to user's locale settings

#### Scenario: Action displayed with visual indicator
- **WHEN** audit log entry is displayed
- **THEN** action type (create/update/delete) is shown with appropriate color coding
- **AND** create is green, update is blue, delete is red

### Requirement: Audit log entries link to affected entities

The system SHALL provide clickable links from audit log entries to the affected entities.

#### Scenario: Contract entry links to contract
- **WHEN** user clicks on a contract entity name in audit log
- **THEN** system navigates to that contract's detail page

#### Scenario: Customer entry links to customer
- **WHEN** user clicks on a customer entity name in audit log
- **THEN** system navigates to that customer's detail page

#### Scenario: Deleted entity shows name without link
- **WHEN** audit log entry is for a deleted entity
- **THEN** entity name is displayed but not clickable
- **AND** entry is visually indicated as deleted

### Requirement: Audit log shows change details

The system SHALL display detailed change information for each audit log entry.

#### Scenario: Expand to see field changes
- **WHEN** user clicks on an update entry
- **THEN** system expands to show the list of changed fields
- **AND** each field shows old value and new value

#### Scenario: Create shows all initial values
- **WHEN** user expands a create entry
- **THEN** system shows all fields that were set on creation

#### Scenario: Delete shows final values
- **WHEN** user expands a delete entry
- **THEN** system shows the values the entity had before deletion

#### Scenario: Field names are human-readable
- **WHEN** field changes are displayed
- **THEN** field names are shown in human-readable format (e.g., "Start Date" not "start_date")

### Requirement: Contract detail page shows activity tab

The system SHALL display an activity tab on the contract detail page showing that contract's audit history.

#### Scenario: Activity tab on contract detail
- **WHEN** user views a contract detail page
- **THEN** there is an "Activity" tab available

#### Scenario: Activity tab shows contract changes
- **WHEN** user clicks the Activity tab on contract detail
- **THEN** system displays audit log entries for that contract
- **AND** entries include changes to the contract and its items

#### Scenario: Activity sorted newest first
- **WHEN** activity tab is displayed
- **THEN** entries are sorted by timestamp descending

### Requirement: Customer detail page shows activity tab

The system SHALL display an activity tab on the customer detail page showing that customer's audit history.

#### Scenario: Activity tab on customer detail
- **WHEN** user views a customer detail page
- **THEN** there is an "Activity" tab available

#### Scenario: Activity tab shows customer changes
- **WHEN** user clicks the Activity tab on customer detail
- **THEN** system displays audit log entries for that customer

### Requirement: Audit log supports filtering

The system SHALL allow users to filter audit log entries on the global page.

#### Scenario: Filter by entity type
- **WHEN** user selects an entity type filter
- **THEN** table shows only entries for that entity type

#### Scenario: Filter by action type
- **WHEN** user selects an action type filter (create/update/delete)
- **THEN** table shows only entries with that action

#### Scenario: Filter by date range
- **WHEN** user selects a date range
- **THEN** table shows only entries within that range

#### Scenario: Clear filters
- **WHEN** user clears filters
- **THEN** table shows all entries again

### Requirement: Audit log supports pagination

The system SHALL paginate audit log results for performance.

#### Scenario: Initial page load
- **WHEN** audit log page loads
- **THEN** system shows the first page of results (e.g., 25 entries)

#### Scenario: Load more entries
- **WHEN** user scrolls or clicks "Load More"
- **THEN** system fetches and appends the next page of entries

#### Scenario: Total count displayed
- **WHEN** audit log is displayed
- **THEN** system shows the total count of matching entries

### Requirement: Audit log UI supports localization

The system SHALL display the audit log UI in German and English.

#### Scenario: German translations
- **WHEN** user language is German
- **THEN** all labels, buttons, and messages display in German

#### Scenario: English translations
- **WHEN** user language is English
- **THEN** all labels, buttons, and messages display in English

