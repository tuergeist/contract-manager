## MODIFIED Requirements

### Requirement: Department time distribution overview
The system SHALL display a percentage breakdown of total tracked hours across departments. 100% represents the total hours across all departments. Each department shows its percentage share and absolute hours. When user cost profiles with default departments exist, untracked hours are backfilled to default departments before computing the distribution.

#### Scenario: View department distribution
- **WHEN** user opens the department time analysis page with a date range
- **THEN** the system displays each department with its percentage of total hours (e.g. "Sales & Marketing: 14%, G&A: 26%, R&D: 60%")

#### Scenario: Unassigned services grouped
- **WHEN** some Clockodo services are not assigned to any department
- **THEN** their hours appear under an "Unassigned" category in the distribution

#### Scenario: No time data
- **WHEN** there are no time entries in the selected date range
- **THEN** the system displays an empty state message

#### Scenario: Distribution with backfilled hours
- **WHEN** user cost profiles exist with default departments and some users logged fewer hours than their FTE target
- **THEN** the distribution includes backfilled hours in the respective default departments

### Requirement: User-department time matrix
The system SHALL display a matrix table with users as rows and departments as columns. Each cell shows the hours worked by that user in that department. A total column shows each user's total hours. When user cost profiles exist, untracked hours are backfilled to default departments.

#### Scenario: View user-department matrix
- **WHEN** user opens the department time analysis page
- **THEN** a table is displayed with one row per Clockodo user and one column per department, plus a total column

#### Scenario: Cell values
- **WHEN** a user has logged time to services belonging to a department
- **THEN** the cell shows the summed hours for that user in that department

#### Scenario: Zero hours
- **WHEN** a user has no time in a particular department
- **THEN** the cell shows "–" or 0

#### Scenario: Percentage mode
- **WHEN** user toggles to percentage view
- **THEN** each cell shows the percentage of that user's total hours spent in the department (each row sums to 100%)

#### Scenario: Backfilled hours in matrix
- **WHEN** a user has a cost profile with FTE 100% and default department "G&A", and logged only 100h total
- **THEN** the matrix shows 68h added to the "G&A" column for that user, and their total is 168h

#### Scenario: No backfill without cost profile
- **WHEN** a user has no cost profile configured
- **THEN** the matrix shows only their actually logged hours (no backfilling, backwards compatible)

#### Scenario: No backfill when hours exceed target
- **WHEN** a user has a cost profile with FTE 100% and logged 180h total
- **THEN** no backfilling occurs; the matrix shows the actual 180h (no capping)

### Requirement: Hour backfilling logic
The system SHALL backfill untracked hours for users who have a cost profile with a default department. The FTE-adjusted monthly target is 168h * (FTE% / 100). If a user's logged hours are below the target, the difference is added to their default department.

#### Scenario: Backfill partial month
- **WHEN** a user with FTE 100% logged 120h in a month
- **THEN** 48h (168 - 120) are added to their default department

#### Scenario: Backfill part-time user
- **WHEN** a user with FTE 50% logged 60h in a month
- **THEN** 24h (84 - 60) are added to their default department

#### Scenario: No backfill when fully tracked
- **WHEN** a user with FTE 100% logged 170h in a month
- **THEN** no backfilling occurs; all 170h are shown as logged

#### Scenario: No backfill without default department
- **WHEN** a user has a cost profile with FTE and income but no default department set
- **THEN** no backfilling occurs for that user
