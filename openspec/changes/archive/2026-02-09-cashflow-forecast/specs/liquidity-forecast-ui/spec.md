## ADDED Requirements

### Requirement: Liquidity forecast page accessible from navigation
The system SHALL provide a "Liquidity Forecast" menu item in the main sidebar navigation that opens the forecast page at `/liquidity-forecast`.

#### Scenario: Navigate to liquidity forecast
- **WHEN** user clicks "Liquidity Forecast" in sidebar
- **THEN** browser navigates to `/liquidity-forecast` and displays the forecast page

#### Scenario: Page requires authentication
- **WHEN** unauthenticated user accesses `/liquidity-forecast`
- **THEN** user is redirected to login page

### Requirement: Display cash-flow forecast chart
The system SHALL display a chart showing projected account balance over the next 12 months, including current balance, expected recurring costs, and expected recurring income.

#### Scenario: Show forecast chart with detected patterns
- **WHEN** user views forecast page with confirmed recurring patterns
- **THEN** chart displays month-by-month projected balance line with recurring costs and income overlaid

#### Scenario: Show forecast chart with no patterns
- **WHEN** user views forecast page with no detected patterns
- **THEN** chart displays flat line at current balance with message "No recurring patterns detected"

#### Scenario: Distinguish confirmed vs auto-detected patterns
- **WHEN** chart displays projections
- **THEN** confirmed pattern projections appear solid; auto-detected (unconfirmed) projections appear dashed/faded

### Requirement: Display recurring patterns list
The system SHALL display a list of detected recurring patterns showing counterparty, amount, frequency, confidence score, and last occurrence date, with actions to confirm or ignore.

#### Scenario: List detected patterns
- **WHEN** user views patterns section
- **THEN** all non-ignored patterns are listed with counterparty name, average amount, frequency, confidence score, and last seen date

#### Scenario: Sort patterns by confidence
- **WHEN** patterns are displayed
- **THEN** patterns are sorted by confidence score descending (highest confidence first)

#### Scenario: Filter patterns by type
- **WHEN** user selects "Costs only" or "Income only" filter
- **THEN** list shows only patterns with negative amounts (costs) or positive amounts (income)

### Requirement: Display monthly projection table
The system SHALL display a table showing projected transactions for each future month, grouped by month with subtotals.

#### Scenario: Show projection table
- **WHEN** user views projection table
- **THEN** table shows next 12 months with projected recurring transactions, amounts, and monthly subtotals

#### Scenario: Expand month to see details
- **WHEN** user clicks on a month row
- **THEN** row expands to show individual projected transactions for that month

### Requirement: Manual pattern adjustment
The system SHALL allow users to manually adjust pattern details: amount, frequency, and next expected date.

#### Scenario: Edit pattern amount
- **WHEN** user edits the amount on a pattern
- **THEN** pattern's projected amount updates and forecast recalculates

#### Scenario: Edit pattern frequency
- **WHEN** user changes frequency from "monthly" to "quarterly"
- **THEN** pattern projects at new interval and forecast chart updates

#### Scenario: Pause pattern temporarily
- **WHEN** user clicks "Pause" on a pattern
- **THEN** pattern is excluded from projections until user resumes it

### Requirement: Show current account balance
The system SHALL display the current total balance across all bank accounts as the starting point for the forecast.

#### Scenario: Display current balance
- **WHEN** user views forecast page
- **THEN** current total balance is displayed prominently with "as of" date from most recent transaction

#### Scenario: Handle multiple accounts
- **WHEN** user has multiple bank accounts
- **THEN** current balance shows sum of all accounts with option to view per-account breakdown
