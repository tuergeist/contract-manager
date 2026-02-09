## ADDED Requirements

### Requirement: System provides an auto-generated counterparty list
The system SHALL provide a GraphQL query `bankCounterparties` that returns all unique counterparty names from bank transactions, aggregated with: total debit amount, total credit amount, transaction count, first transaction date, and last transaction date. Results SHALL be scoped to the requesting user's tenant.

#### Scenario: List counterparties
- **WHEN** user queries `bankCounterparties` with no filters
- **THEN** the system returns all unique counterparty names with aggregated totals, sorted by total absolute amount descending

#### Scenario: Empty state
- **WHEN** no transactions exist
- **THEN** the system returns an empty list

### Requirement: Counterparty list supports search
The system SHALL accept an optional `search` parameter that filters counterparties by partial, case-insensitive match on the counterparty name.

#### Scenario: Search by name
- **WHEN** user searches for "Software"
- **THEN** the system returns only counterparties whose name contains "Software" (e.g., "SoftwareOne Deutschland GmbH")

### Requirement: Counterparty list supports sorting
The system SHALL accept `sortBy` (name, totalAmount, transactionCount, lastDate) and `sortOrder` (asc, desc) parameters. Default sort SHALL be by absolute total amount descending.

#### Scenario: Sort by name ascending
- **WHEN** user sorts by "name" ascending
- **THEN** counterparties are returned alphabetically A-Z

#### Scenario: Sort by transaction count
- **WHEN** user sorts by "transactionCount" descending
- **THEN** counterparties with the most transactions appear first

### Requirement: Counterparty list supports pagination
The system SHALL accept `page` and `pageSize` parameters and return paginated results with `totalCount`, `page`, `pageSize`, and `hasNextPage`.

#### Scenario: Paginate counterparties
- **WHEN** there are 150 unique counterparties and user requests page 1 with pageSize 50
- **THEN** the system returns 50 counterparties and indicates hasNextPage is true

### Requirement: Counterparty list is displayed in a table
The frontend SHALL display the counterparty list in a table with columns: name, transaction count, total amount, last transaction date. Each row SHALL be clickable, navigating to the counterparty detail view.

#### Scenario: View counterparty table
- **WHEN** user navigates to the counterparties section of the banking page
- **THEN** the system displays a table of all counterparties with aggregated data

#### Scenario: Click navigates to detail
- **WHEN** user clicks on a counterparty row (e.g., "BG Verkehr")
- **THEN** the browser navigates to the counterparty detail view showing all transactions with "BG Verkehr"
