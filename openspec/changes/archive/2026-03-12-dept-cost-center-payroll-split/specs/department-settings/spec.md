## ADDED Requirements

### Requirement: Cost center picker on department configuration

The department settings UI SHALL display a cost center selector for each department, allowing users to link a department to a cost center.

#### Scenario: Cost center dropdown shown per department
- **WHEN** user views the department list in Settings > Integrations > Time Tracking
- **THEN** each department row SHALL show a cost center dropdown populated with active cost centers

#### Scenario: Assign cost center via dropdown
- **WHEN** user selects cost center "100 — Engineering" for department "Development"
- **THEN** the system SHALL save the association and display the selected cost center

#### Scenario: Clear cost center assignment
- **WHEN** user clears the cost center dropdown for a department
- **THEN** the department's cost center link SHALL be removed

#### Scenario: No cost centers exist
- **WHEN** no cost centers have been created in the tenant
- **THEN** the dropdown SHALL be empty with a hint to create cost centers in Accounting settings
