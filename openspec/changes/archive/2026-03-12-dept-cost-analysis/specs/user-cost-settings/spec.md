## ADDED Requirements

### Requirement: Configure user cost profiles
The system SHALL allow users to configure cost profiles for Clockodo users. Each profile includes FTE percentage, monthly income, and an optional default department. The profile list is populated from the Clockodo user list.

#### Scenario: View Clockodo users in settings
- **WHEN** user opens the department settings section and a time tracking provider is configured
- **THEN** a "User Cost Settings" table is displayed below the service assignment table, listing all Clockodo users

#### Scenario: Set FTE percentage
- **WHEN** user enters an FTE percentage for a Clockodo user (e.g. 100 for full-time, 50 for half-time)
- **THEN** the value is stored and used for target hours calculation (168h * FTE% / 100)

#### Scenario: Set monthly income
- **WHEN** user enters a monthly income value for a Clockodo user
- **THEN** the value is stored as the cost factor for that user's hourly cost computation

#### Scenario: Set default department
- **WHEN** user selects a department from the dropdown for a Clockodo user
- **THEN** the department is stored as the user's default department for hour backfilling

#### Scenario: Leave default department empty
- **WHEN** user leaves the default department unset for a Clockodo user
- **THEN** no hour backfilling is applied for that user

#### Scenario: Default values
- **WHEN** a Clockodo user has no saved cost profile
- **THEN** the table row shows FTE 100%, income 0, and no default department

### Requirement: Bulk save user cost profiles
The system SHALL save all user cost profiles in a single bulk operation, replacing all existing profiles for the tenant.

#### Scenario: Save all profiles
- **WHEN** user clicks the save button in the user cost settings section
- **THEN** all profiles are saved atomically (delete existing + create new) and a success message is shown

#### Scenario: Save with partial data
- **WHEN** user saves profiles where some users have no income or no default department
- **THEN** the system saves all profiles as provided, including those with zero income or no default department

### Requirement: Fetch Clockodo user list
The system SHALL provide a query to fetch the list of users from the configured Clockodo account. Each user has an ID and display name.

#### Scenario: Query Clockodo users
- **WHEN** the system queries the Clockodo user list
- **THEN** the system returns all active users with their ID and name

#### Scenario: No time tracking provider configured
- **WHEN** no time tracking provider is configured
- **THEN** the user cost settings section is not displayed
