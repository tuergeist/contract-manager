## ADDED Requirements

### Requirement: Link department to cost center

The system SHALL allow each Department to optionally reference a CostCenter. This links the time tracking domain to the accounting domain.

#### Scenario: Assign cost center to department
- **WHEN** user selects a cost center for a department in department settings
- **THEN** the department's `cost_center` FK is set to the selected CostCenter

#### Scenario: Remove cost center from department
- **WHEN** user clears the cost center selection on a department
- **THEN** the department's `cost_center` FK is set to null

#### Scenario: Cost center deleted
- **WHEN** a cost center that is linked to a department is deactivated or deleted
- **THEN** the department's `cost_center` FK SHALL be set to null (SET_NULL)

#### Scenario: Multiple departments may share a cost center
- **WHEN** two departments are assigned the same cost center
- **THEN** the system SHALL allow this (no uniqueness constraint)

#### Scenario: Department without cost center excluded from FTE splits
- **WHEN** an FTE-based split is computed and a department has no linked cost center
- **THEN** that department's FTE share SHALL be excluded from the split and redistributed proportionally among departments that have cost centers
