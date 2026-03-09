## ADDED Requirements

### Requirement: User can filter counterparty statistics by date range
The system SHALL allow users to filter the counterparties list by a date range. When a date range is applied, all aggregated statistics (total debit, total credit, transaction count, first/last transaction date, absolute total) SHALL reflect only transactions within that range.

#### Scenario: Filter counterparties by date range
- **WHEN** user sets date-from to "2025-01-01" and date-to "2025-06-30" on the counterparties tab
- **THEN** the system displays counterparties with all statistics computed only from transactions within that date range

#### Scenario: No date filter applied
- **WHEN** user views the counterparties tab without setting any date filters
- **THEN** the system displays counterparties with statistics computed from all transactions (existing behavior)

#### Scenario: Partial date range
- **WHEN** user sets only date-from to "2025-01-01" without a date-to
- **THEN** the system filters transactions from that date onwards with no upper bound

#### Scenario: Date filter resets pagination
- **WHEN** user is on page 3 of counterparties and changes the date-from filter
- **THEN** the system resets to page 1 and re-fetches with the new filter

### Requirement: Date range carries over to counterparty detail
The system SHALL pass the selected date range to the counterparty detail view so that the detail statistics are consistent with the list view.

#### Scenario: Navigate to detail with date filter active
- **WHEN** user has date-from "2025-01-01" and date-to "2025-06-30" set and clicks on a counterparty
- **THEN** the counterparty detail page opens with the same date range applied, and its statistics reflect only transactions within that range

#### Scenario: Navigate to detail without date filter
- **WHEN** user clicks on a counterparty without any date filter set
- **THEN** the counterparty detail page shows statistics for all transactions
