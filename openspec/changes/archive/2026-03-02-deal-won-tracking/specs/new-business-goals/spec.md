## ADDED Requirements

### Requirement: NewBusinessGoal model for tracking won deal targets
The system SHALL have a NewBusinessGoal model for setting yearly targets on new business metrics.

#### Scenario: Goal types
- **WHEN** creating a new business goal
- **THEN** the goal_type SHALL be one of: `new_arr` (won new ARR), `new_development` (won development/training revenue), `new_deal_count` (number of won deals)

#### Scenario: One goal per type per year
- **WHEN** a user sets a target for new_arr in 2026 and one already exists
- **THEN** the system SHALL update the existing goal rather than creating a duplicate

#### Scenario: Goals are tenant-scoped
- **WHEN** a user creates a new business goal
- **THEN** the goal SHALL be associated with the user's tenant

### Requirement: Calculate new business metrics for a year
The system SHALL calculate actual new business metrics from contracts with `deal_won_date` in the selected year.

#### Scenario: Won new ARR
- **WHEN** calculating new_arr for year 2026
- **THEN** the system SHALL sum the annualized recurring item values from all contracts where `deal_won_date` is in 2026 and `hubspot_deal_id` is not null

#### Scenario: Won development revenue
- **WHEN** calculating new_development for year 2026
- **THEN** the system SHALL sum the value of items with effective_revenue_type in (`advanced_development`, `training_implementation`) from contracts where `deal_won_date` is in 2026 and `hubspot_deal_id` is not null

#### Scenario: Won deal count
- **WHEN** calculating new_deal_count for year 2026
- **THEN** the system SHALL count distinct contracts where `deal_won_date` is in 2026 and `hubspot_deal_id` is not null

#### Scenario: Only effectively active or ended contracts count
- **WHEN** calculating new business metrics
- **THEN** the system SHALL include contracts with status active or ended (not draft, cancelled, or deleted)

### Requirement: GraphQL API for new business goals
The system SHALL expose queries and mutations for managing new business goals.

#### Scenario: Query goals for a year
- **WHEN** client executes `newBusinessGoals(year: 2026)`
- **THEN** the response SHALL include all new business goals for that year and tenant

#### Scenario: Set a new business goal
- **WHEN** client executes `setNewBusinessGoal(year: 2026, goalType: "new_arr", targetAmount: 200000)`
- **THEN** the system SHALL create or update the goal and return the result

#### Scenario: Delete a new business goal
- **WHEN** client executes `deleteNewBusinessGoal(year: 2026, goalType: "new_arr")`
- **THEN** the system SHALL remove the goal for that type and year

### Requirement: GraphQL query for new business actuals
The system SHALL expose a query returning actual new business metrics for a year.

#### Scenario: Query returns metrics
- **WHEN** client executes `newBusinessMetrics(year: 2026)`
- **THEN** the response SHALL include: wonNewArr, wonDevelopmentRevenue, wonDealCount

#### Scenario: Query is tenant-scoped
- **WHEN** querying new business metrics
- **THEN** results SHALL be filtered to the authenticated user's tenant

### Requirement: New business goals settings UI
The system SHALL provide a settings section for managing new business goals alongside existing revenue goals.

#### Scenario: New business goals section in settings
- **WHEN** user navigates to Settings > General > Revenue Goals
- **THEN** a "New Business Goals" section SHALL be visible below the existing per-stream goals

#### Scenario: Input fields for each goal type
- **WHEN** viewing the new business goals section
- **THEN** there SHALL be input fields for: Won New ARR, Won Development Revenue, Won Deal Count

#### Scenario: Save and load
- **WHEN** user enters targets and saves
- **THEN** the system SHALL persist the goals and reload them when the page is revisited
