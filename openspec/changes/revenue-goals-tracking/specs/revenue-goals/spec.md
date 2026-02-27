## ADDED Requirements

### Requirement: Revenue goals can be defined per year and stream
The system SHALL allow users to define yearly revenue targets for each of the three revenue streams.

#### Scenario: Create a revenue goal
- **WHEN** a user sets a target of €500,000 for "Recurring Revenue" in year 2026
- **THEN** the system SHALL store a RevenueGoal record with year=2026, revenue_type=recurring, target_amount=500000

#### Scenario: One goal per stream per year
- **WHEN** a user sets a target for a revenue stream that already has a goal for that year
- **THEN** the system SHALL update the existing goal rather than creating a duplicate

#### Scenario: Goals are tenant-scoped
- **WHEN** a user creates a revenue goal
- **THEN** the goal SHALL be associated with the user's tenant and not visible to other tenants

#### Scenario: Goal amount accepts decimals
- **WHEN** a user enters a target amount of €123,456.78
- **THEN** the system SHALL store the value with 2 decimal places

### Requirement: Revenue goals settings UI
The system SHALL provide a settings interface for managing revenue goals under Settings > General > Revenue Goals.

#### Scenario: Revenue Goals sub-tab in General settings
- **WHEN** user navigates to Settings > General
- **THEN** a "Revenue Goals" sub-tab SHALL be visible alongside Contracts, Help Videos, and Performance

#### Scenario: Year selector
- **WHEN** user opens the Revenue Goals settings
- **THEN** a year selector SHALL be displayed, defaulting to the current year

#### Scenario: Goal input form
- **WHEN** user selects a year
- **THEN** the form SHALL display one input row per revenue stream: Advanced Development, Training + Implementation, Recurring Revenue

#### Scenario: Save goals
- **WHEN** user enters target amounts and clicks Save
- **THEN** the system SHALL create or update RevenueGoal records for the selected year

#### Scenario: Load existing goals
- **WHEN** user selects a year that already has goals defined
- **THEN** the form SHALL pre-populate with the existing target amounts

#### Scenario: Empty goals display as blank
- **WHEN** user selects a year with no goals defined
- **THEN** the input fields SHALL be empty (not zero)

### Requirement: GraphQL API for revenue goals
The system SHALL expose GraphQL queries and mutations for managing revenue goals.

#### Scenario: Query goals for a year
- **WHEN** client executes `revenueGoals(year: 2026)`
- **THEN** the response SHALL include all revenue goals for that year and tenant

#### Scenario: Set a revenue goal mutation
- **WHEN** client executes `setRevenueGoal(year: 2026, revenueType: "recurring", targetAmount: 500000)`
- **THEN** the system SHALL create or update the goal and return the result

#### Scenario: Query requires authentication
- **WHEN** an unauthenticated request queries revenue goals
- **THEN** the request SHALL be rejected with an authentication error

#### Scenario: Delete a revenue goal
- **WHEN** user clears a target amount and saves
- **THEN** the system SHALL remove the RevenueGoal record for that stream and year
