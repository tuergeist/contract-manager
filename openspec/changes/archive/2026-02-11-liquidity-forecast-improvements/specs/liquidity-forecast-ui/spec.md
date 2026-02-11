## MODIFIED Requirements

### Requirement: Display cash-flow forecast chart
**CHANGED**: The forecast period is now calendar-year aligned instead of rolling 12 months.

The system SHALL display a chart showing projected account balance from January 1 of the current year through January 1 of the following year.

#### Scenario: Calendar year date range
- **WHEN** user views forecast page
- **THEN** chart x-axis spans from Jan 1 current year to Jan 1 next year (full calendar year)

#### Scenario: Respect income/cost toggles on chart
- **WHEN** user disables "Show Income" toggle
- **THEN** chart projections exclude all income patterns (positive amounts)
- **WHEN** user disables "Show Costs" toggle
- **THEN** chart projections exclude all cost patterns (negative amounts)

### Requirement: Display recurring patterns list
**CHANGED**: Added sorting, search, and independent income/cost toggles.

The system SHALL display a list of detected recurring patterns with sorting, search, and filtering capabilities.

#### Scenario: Sort patterns by column
- **WHEN** user clicks a column header (counterparty, amount, frequency, confidence)
- **THEN** patterns are sorted by that column ascending; clicking again toggles to descending

#### Scenario: Search patterns by counterparty
- **WHEN** user types in the search input above the patterns table
- **THEN** list filters to show only patterns where counterparty name contains the search text (case-insensitive)

#### Scenario: Independent income/cost toggles
- **WHEN** user toggles "Show Income" off and "Show Costs" on
- **THEN** list shows only cost patterns (negative amounts)
- **WHEN** user toggles both "Show Income" and "Show Costs" on
- **THEN** list shows all patterns
- **WHEN** user toggles both off
- **THEN** list shows no patterns and displays a hint to enable at least one filter

### Requirement: Display monthly projection table
**CHANGED**: Projection table also respects the income/cost toggles.

#### Scenario: Projection table respects filters
- **WHEN** user disables "Show Income" toggle
- **THEN** projection table excludes income projections from all months
- **WHEN** user disables "Show Costs" toggle
- **THEN** projection table excludes cost projections from all months
