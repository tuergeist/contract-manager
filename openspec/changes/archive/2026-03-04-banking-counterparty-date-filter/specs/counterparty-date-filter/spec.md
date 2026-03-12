## ADDED Requirements

### Requirement: Counterparty list supports date range filtering
The Banking page counterparties tab SHALL allow users to filter the date range used for balance summation.

#### Scenario: Date pickers shown on counterparties tab
- **WHEN** user views the counterparties tab on the Banking page
- **THEN** the system SHALL display date-from and date-to input fields above the counterparty table

#### Scenario: Filtering by date range
- **WHEN** user sets a date-from and/or date-to value
- **THEN** the counterparty list SHALL only include transactions within the specified range for all aggregated values (total debit, total credit, transaction count, first date, last date)
- **AND** the list SHALL reset to page 1

#### Scenario: No date filter applied
- **WHEN** no date range is specified (both fields empty)
- **THEN** the counterparty list SHALL aggregate across all transactions (existing behavior)

#### Scenario: Partial date range
- **WHEN** only date-from is set (date-to empty)
- **THEN** the system SHALL include all transactions from that date onward
- **WHEN** only date-to is set (date-from empty)
- **THEN** the system SHALL include all transactions up to and including that date

### Requirement: Date range passed to counterparty detail page
The system SHALL pass the active date filter to the counterparty detail page when navigating from the filtered list.

#### Scenario: Navigating to detail with date range
- **WHEN** user clicks a counterparty row while a date range filter is active
- **THEN** the system SHALL navigate to the counterparty detail page with dateFrom and dateTo as URL search parameters

#### Scenario: Detail page uses date range from URL
- **WHEN** the counterparty detail page is loaded with dateFrom/dateTo URL parameters
- **THEN** the detail page summary (total debit, total credit, transaction count) SHALL be computed using only transactions within that date range
