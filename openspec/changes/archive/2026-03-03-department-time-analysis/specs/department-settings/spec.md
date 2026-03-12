## ADDED Requirements

### Requirement: Manage departments
The system SHALL allow users to create, rename, and delete departments per tenant. Each department has a unique name within the tenant.

#### Scenario: Create a department
- **WHEN** user enters a department name (e.g. "Sales & Marketing") and saves
- **THEN** the department is created and appears in the department list

#### Scenario: Rename a department
- **WHEN** user changes the name of an existing department
- **THEN** the department name is updated everywhere

#### Scenario: Delete a department
- **WHEN** user deletes a department
- **THEN** the department and all its service assignments are removed

#### Scenario: Reject duplicate name
- **WHEN** user creates a department with a name that already exists
- **THEN** the system SHALL reject the creation with an error message

### Requirement: Assign Clockodo services to departments
The system SHALL allow users to assign Clockodo Leistungen (services) to departments. Each service can be assigned to exactly one department. Unassigned services SHALL be grouped under an "Unassigned" category in analysis views.

#### Scenario: View available services
- **WHEN** user opens the department settings
- **THEN** the system fetches all Leistungen from Clockodo and displays them alongside their current department assignment

#### Scenario: Assign a service to a department
- **WHEN** user assigns a Clockodo service to a department
- **THEN** the mapping is saved and the service appears under that department

#### Scenario: Reassign a service to a different department
- **WHEN** user changes a service's department assignment
- **THEN** the mapping is updated to the new department

#### Scenario: Unassign a service
- **WHEN** user removes a service's department assignment
- **THEN** the service appears as unassigned and is grouped under "Unassigned" in analysis

### Requirement: Department settings location
The department settings SHALL be accessible under Settings > Integrations > Time Tracking, below the existing connection settings. The section SHALL only be visible when a time tracking provider is configured.

#### Scenario: Settings visible when provider configured
- **WHEN** user navigates to Settings > Integrations > Time Tracking and a provider is configured
- **THEN** the department management section is displayed below connection settings

#### Scenario: Settings hidden when no provider
- **WHEN** no time tracking provider is configured
- **THEN** the department management section is not displayed
