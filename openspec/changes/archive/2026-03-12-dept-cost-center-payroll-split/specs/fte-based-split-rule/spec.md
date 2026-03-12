## ADDED Requirements

### Requirement: FTE distribution split rule type

The system SHALL support a new split rule mode called "FTE distribution" that dynamically computes split percentages from the department FTE distribution instead of using statically defined allocations.

#### Scenario: FTE rule on counterparty
- **WHEN** user creates a split rule for counterparty "Payroll Provider" with mode "FTE distribution"
- **THEN** the rule SHALL have no manually defined allocations
- **AND** the split percentages SHALL be resolved at application time from the FTE distribution

#### Scenario: FTE rule resolves from snapshot
- **WHEN** an FTE-rule-based split is applied to a transaction dated 2026-02-20 and a snapshot exists for 2026-02
- **THEN** the system SHALL use the snapshot's department percentages to split the transaction across the corresponding cost centers

#### Scenario: FTE rule falls back to live data
- **WHEN** an FTE-rule-based split is applied to a transaction dated 2026-03-20 and no snapshot exists for 2026-03
- **THEN** the system SHALL compute the split from live Clockodo time data and UserCostProfile FTE percentages for March 2026

#### Scenario: Live data computation
- **WHEN** live FTE distribution is computed for a month
- **THEN** the system SHALL:
  1. Query Clockodo time entries for that month
  2. Group hours by department (via DepartmentServiceMapping)
  3. For each department with a linked cost center, compute its share as: (department hours / total hours) * 100
  4. Departments without linked cost centers are excluded; their hours are redistributed

#### Scenario: Zero hours in a department
- **WHEN** a department has a linked cost center but zero hours in the month
- **THEN** that department SHALL receive 0% of the split (only departments with actual hours get allocation)

#### Scenario: No time data available
- **WHEN** no Clockodo time data exists for the transaction's month (e.g., Clockodo not configured)
- **THEN** the system SHALL fall back to UserCostProfile FTE percentages as static weights
- **AND** distribute proportionally among departments with linked cost centers

#### Scenario: FTE rule coexists with other rule types
- **WHEN** a tenant has both FTE-based and percentage-based split rules
- **THEN** each rule type SHALL operate independently; rule matching priority is unchanged (counterparty rules before pattern rules, ordered by priority)
