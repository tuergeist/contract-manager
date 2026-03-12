## ADDED Requirements

### Requirement: Department time distribution overview
The system SHALL display a percentage breakdown of total tracked hours across departments. 100% represents the total hours across all departments. Each department shows its percentage share and absolute hours.

#### Scenario: View department distribution
- **WHEN** user opens the department time analysis page with a date range
- **THEN** the system displays each department with its percentage of total hours (e.g. "Sales & Marketing: 14%, G&A: 26%, R&D: 60%")

#### Scenario: Unassigned services grouped
- **WHEN** some Clockodo services are not assigned to any department
- **THEN** their hours appear under an "Unassigned" category in the distribution

#### Scenario: No time data
- **WHEN** there are no time entries in the selected date range
- **THEN** the system displays an empty state message

### Requirement: User-department time matrix
The system SHALL display a matrix table with users as rows and departments as columns. Each cell shows the hours worked by that user in that department. A total column shows each user's total hours.

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

### Requirement: Date range filtering
The system SHALL allow filtering the analysis by date range. The default range is the current calendar year (Jan 1 to today).

#### Scenario: Filter by date range
- **WHEN** user selects a custom date range
- **THEN** the department distribution and user matrix update to reflect only hours within that range

#### Scenario: Default date range
- **WHEN** user opens the analysis page without selecting a date range
- **THEN** the system uses January 1 of the current year through today

### Requirement: Analysis page location
The department time analysis SHALL be accessible as a page in the application. It SHALL only be visible when a time tracking provider is configured and at least one department exists.

#### Scenario: Page accessible
- **WHEN** a time tracking provider is configured and departments exist
- **THEN** the analysis page is accessible from the navigation

#### Scenario: Page hidden without departments
- **WHEN** no departments have been created
- **THEN** the analysis page is not visible in the navigation
