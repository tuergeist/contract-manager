## ADDED Requirements

### Requirement: New Business section on Goals dashboard
The Goals tab SHALL display a "New Business" section below the existing per-stream revenue goals table.

#### Scenario: Section shows summary cards
- **WHEN** user views the Goals tab
- **THEN** a "New Business" section SHALL display cards for: Won New ARR, Won Development Revenue, Won Deal Count

#### Scenario: Each card shows actual vs target
- **WHEN** a new business goal is set for the selected year
- **THEN** the card SHALL show the actual value, target, difference, and progress percentage

#### Scenario: Card without target
- **WHEN** no target is set for a metric (e.g., new_deal_count has no goal)
- **THEN** the card SHALL show only the actual value with a prompt to set a goal

#### Scenario: Year selector applies to new business section
- **WHEN** user changes the year in the Goals tab
- **THEN** the new business section SHALL update to show metrics and goals for the selected year

### Requirement: Won deals list on Goals dashboard
The Goals tab SHALL include an expandable list of deals won in the selected year.

#### Scenario: Won deals list is collapsible
- **WHEN** user views the New Business section
- **THEN** a "Won Deals" list SHALL be available, collapsed by default

#### Scenario: Won deals list shows deal details
- **WHEN** user expands the won deals list
- **THEN** each deal SHALL display: customer name, contract name, deal won date, and ARR value

#### Scenario: Won deals are sorted by date
- **WHEN** viewing the won deals list
- **THEN** deals SHALL be sorted by deal_won_date descending (most recent first)

#### Scenario: Won deals link to contract
- **WHEN** user clicks a deal in the won deals list
- **THEN** the system SHALL navigate to the contract detail page

### Requirement: GraphQL query for won deals list
The system SHALL expose a query returning won deals for display on the dashboard.

#### Scenario: Query returns won contracts
- **WHEN** client executes `wonDeals(year: 2026)`
- **THEN** the response SHALL include contracts with hubspot_deal_id not null and deal_won_date in 2026

#### Scenario: Response includes contract and customer details
- **WHEN** querying won deals
- **THEN** each entry SHALL include: contractId, contractName, customerName, dealWonDate, annualRecurringRevenue

#### Scenario: Query is tenant-scoped
- **WHEN** querying won deals
- **THEN** results SHALL be filtered to the authenticated user's tenant
