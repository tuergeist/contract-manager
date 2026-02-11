## ADDED Requirements

### Requirement: User can view all transactions for a specific counterparty
The system SHALL provide a counterparty detail view accessible at `/banking/counterparty/:name` that displays all transactions where `counterparty_name` matches the URL parameter exactly. The view SHALL reuse the existing transaction table layout with all existing filters (date range, amount range, direction, account, sorting, pagination).

#### Scenario: View counterparty transactions
- **WHEN** user navigates to `/banking/counterparty/BG%20Verkehr`
- **THEN** the system displays all transactions with counterparty_name "BG Verkehr" in a paginated table

#### Scenario: Counterparty with no transactions
- **WHEN** user navigates to a counterparty detail URL for a name that has no transactions
- **THEN** the system displays an empty state message

### Requirement: Detail view shows counterparty summary header
The system SHALL display a header section above the transaction table showing: counterparty name, total debit amount, total credit amount, transaction count, and date range (first to last transaction).

#### Scenario: Summary header content
- **WHEN** user views the detail page for "BG Verkehr" who has 12 transactions totaling -4,800.00 EUR between 2025-01-15 and 2025-12-15
- **THEN** the header shows "BG Verkehr", "12 transactions", total "-4,800.00 EUR", and date range "15.01.2025 - 15.12.2025"

### Requirement: Detail view supports back navigation
The system SHALL provide a back link/button that returns the user to the banking page's counterparty list.

#### Scenario: Navigate back
- **WHEN** user clicks the back button on the counterparty detail view
- **THEN** the browser navigates back to the banking page

### Requirement: Existing transaction query supports exact counterparty name filter
The `bankTransactions` GraphQL query SHALL accept an optional `counterpartyName` parameter that filters transactions by exact match on `counterparty_name` (case-sensitive). This is distinct from the existing `search` parameter which does partial matching.

#### Scenario: Filter by exact counterparty name
- **WHEN** query includes `counterpartyName: "BG Verkehr"`
- **THEN** only transactions with `counterparty_name` exactly equal to "BG Verkehr" are returned
