## ADDED Requirements

### Requirement: Department cost distribution
The system SHALL display a cost distribution across departments based on user cost profiles. Cost is computed from each user's hourly cost (monthly income / FTE-adjusted target hours) multiplied by their hours per department. Each department shows its share of total cost as a percentage and absolute amount.

#### Scenario: View cost distribution
- **WHEN** user opens the department analysis page and at least one user has a monthly income configured
- **THEN** a cost distribution section is displayed showing each department's cost amount and percentage of total cost

#### Scenario: Cost differs from hour share
- **WHEN** a user with high income works primarily in one department
- **THEN** that department's cost percentage is higher than its hour percentage

#### Scenario: No income data configured
- **WHEN** no users have monthly income configured (all zero or no profiles)
- **THEN** the cost distribution section is not displayed

#### Scenario: Users without cost profiles excluded
- **WHEN** some users have cost profiles and others do not
- **THEN** only users with cost profiles contribute to cost calculations; users without profiles are excluded from cost analysis

### Requirement: Hourly cost computation
The system SHALL compute each user's hourly cost as monthly income divided by FTE-adjusted target hours (168 * FTE% / 100). The target hours constant is 168h (21 working days * 8h), regardless of calendar month.

#### Scenario: Full-time employee cost
- **WHEN** a user has FTE 100% and monthly income 5000
- **THEN** their hourly cost is 5000 / 168 = 29.76

#### Scenario: Part-time employee cost
- **WHEN** a user has FTE 50% and monthly income 2500
- **THEN** their hourly cost is 2500 / 84 = 29.76

#### Scenario: Zero income
- **WHEN** a user has monthly income of 0
- **THEN** the user is excluded from cost calculations (hourly cost is 0, contributes no cost)

### Requirement: Cost distribution uses backfilled hours
The system SHALL compute cost distribution using hours after backfilling. This ensures that the cost model reflects full employment cost, including untracked time attributed to default departments.

#### Scenario: Cost includes backfilled hours
- **WHEN** a user logged 100h but has FTE 100% (target 168h) with a default department
- **THEN** cost is computed on the full 168h (100h logged + 68h backfilled), not just 100h

#### Scenario: Cost without backfill for users without default department
- **WHEN** a user has a cost profile but no default department
- **THEN** cost is computed only on their actually logged hours (no backfilling)
