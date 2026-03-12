## ADDED Requirements

### Requirement: FTE distribution snapshot model

The system SHALL persist monthly FTE distribution snapshots as immutable records. Each snapshot captures the department-level FTE percentages and monthly incomes for a specific month.

#### Scenario: Snapshot structure
- **WHEN** a snapshot is created for month 2026-02
- **THEN** the system SHALL create one `FteDistributionSnapshot` with `year_month=2026-02` and `captured_at` timestamp
- **AND** one `FteDistributionEntry` per department containing: department FK, cost_center FK (denormalized at capture time), fte_percentage, monthly_income_total, and hours_total

#### Scenario: Snapshot immutability
- **WHEN** a snapshot exists for month 2026-02
- **THEN** the system SHALL reject any attempt to create another snapshot for the same month and tenant
- **AND** the system SHALL NOT allow modification of existing snapshot entries

#### Scenario: Snapshot unique per tenant per month
- **WHEN** a snapshot is captured for 2026-02
- **THEN** a unique constraint on `(tenant, year_month)` SHALL prevent duplicates

### Requirement: Auto-capture snapshots on schedule

The system SHALL automatically capture FTE distribution snapshots on a configurable day of the following month.

#### Scenario: Default auto-capture on 7th
- **WHEN** no custom capture day is configured for a tenant
- **THEN** the system SHALL capture the previous month's snapshot on the 7th of the current month (e.g., February snapshot captured on March 7th)

#### Scenario: Configurable capture day
- **WHEN** tenant configures snapshot capture day to 10
- **THEN** the system SHALL capture on the 10th of the following month instead

#### Scenario: Snapshot already exists
- **WHEN** the auto-capture task runs but a snapshot already exists for that month
- **THEN** the task SHALL skip capture silently (idempotent)

#### Scenario: No departments with cost centers
- **WHEN** auto-capture runs but no departments have linked cost centers
- **THEN** the task SHALL skip capture (nothing meaningful to snapshot)

### Requirement: Email notification on snapshot capture

The system SHALL optionally send an email notification when a snapshot is captured.

#### Scenario: Notification sent
- **WHEN** a snapshot is captured and a notification email is configured in tenant settings
- **THEN** the system SHALL send an email summarizing the captured distribution (month, departments, percentages, incomes)

#### Scenario: No notification configured
- **WHEN** no notification email is configured
- **THEN** the system SHALL capture the snapshot without sending any email

### Requirement: Manual snapshot trigger

The system SHALL allow users to manually trigger snapshot capture for any past month.

#### Scenario: Manual capture for past month
- **WHEN** user triggers snapshot capture for 2026-01
- **THEN** the system SHALL compute the FTE distribution for January 2026 and persist it

#### Scenario: Manual capture blocked if snapshot exists
- **WHEN** user triggers snapshot capture for a month that already has a snapshot
- **THEN** the system SHALL reject the request with an error "Snapshot already exists for this month"

#### Scenario: Manual capture for future month rejected
- **WHEN** user triggers snapshot capture for a future month
- **THEN** the system SHALL reject the request with an error "Cannot capture snapshot for a future month"

### Requirement: Re-apply splits on snapshot capture

The system SHALL re-apply FTE-based splits for all transactions in the snapshotted month when a snapshot is captured.

#### Scenario: Preliminary splits replaced by snapshot
- **WHEN** a snapshot is captured for 2026-02
- **THEN** the system SHALL find all transactions in February 2026 that have FTE-rule-based splits (non-manual)
- **AND** re-compute their splits using the snapshot percentages
- **AND** replace the existing auto-applied splits with the new snapshot-based values

#### Scenario: Manual splits preserved
- **WHEN** a transaction in the snapshotted month has manual splits (`is_manual=True`)
- **THEN** the system SHALL NOT modify those splits

### Requirement: Snapshot history view

The system SHALL provide a read-only view of all captured FTE distribution snapshots.

#### Scenario: View snapshot list
- **WHEN** user navigates to the snapshot history in Accounting settings
- **THEN** the system SHALL display a list of all snapshots ordered by month (newest first), showing month, capture date, and number of departments

#### Scenario: View snapshot detail
- **WHEN** user expands or clicks a snapshot
- **THEN** the system SHALL display per-department: name, cost center code, FTE percentage, monthly income total, and hours total

### Requirement: GraphQL API for snapshots

The system SHALL expose snapshot operations via GraphQL.

#### Scenario: Query snapshots
- **WHEN** user queries `fteDistributionSnapshots(year: Int)`
- **THEN** the system SHALL return all snapshots for the given year with their entries

#### Scenario: Capture snapshot mutation
- **WHEN** user calls `captureFteDistributionSnapshot(yearMonth: String!)`
- **THEN** the system SHALL capture the snapshot and return it
- **AND** require `cost_centers.config` permission
