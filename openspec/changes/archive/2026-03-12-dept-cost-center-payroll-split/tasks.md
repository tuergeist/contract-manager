## 1. Department → Cost Center FK

- [x] 1.1 Add `cost_center` FK (nullable, SET_NULL) to `Department` model in `contracts/models.py`, pointing to `banking.CostCenter`
- [x] 1.2 Create migration for the new FK
- [x] 1.3 Add `cost_center_id` field to `updateDepartment` GraphQL mutation (contracts schema)
- [x] 1.4 Expose `costCenter` on `DepartmentType` in GraphQL

## 2. Split rule FTE mode

- [x] 2.1 Add `mode` CharField to `CostCenterSplitRule` with choices `percentage`, `fixed_amount`, `fte_distribution` (default `percentage`)
- [x] 2.2 Create data migration: set `mode` based on existing allocation fields (percentage → `percentage`, fixed_amount → `fixed_amount`)
- [x] 2.3 Update `createCostCenterSplitRule` mutation to accept `mode` parameter; skip allocation validation for `fte_distribution` mode
- [x] 2.4 Update `updateCostCenterSplitRule` mutation to handle mode changes
- [x] 2.5 Expose `mode` on `CostCenterSplitRuleType`

## 3. FTE distribution snapshot models

- [x] 3.1 Create `FteDistributionSnapshot` model: tenant FK, `year_month` (CharField, "YYYY-MM"), `captured_at` (DateTimeField), `captured_by` (FK User, nullable). Unique constraint on `(tenant, year_month)`
- [x] 3.2 Create `FteDistributionEntry` model: snapshot FK (cascade), department FK (nullable, SET_NULL), `department_name` (CharField), cost_center FK (nullable, SET_NULL), `cost_center_code` (CharField), `fte_percentage` (Decimal), `monthly_income_total` (Decimal), `hours_total` (Decimal)
- [x] 3.3 Create migration for snapshot models

## 4. Tenant settings for snapshot

- [x] 4.1 Add `fte_snapshot_capture_day` (IntegerField, default 7) to tenant settings
- [x] 4.2 Add `fte_snapshot_notification_email` (EmailField, nullable) to tenant settings
- [x] 4.3 Expose both fields in tenant settings GraphQL query and update mutation

## 5. FTE snapshot service

- [x] 5.1 Create `FteSnapshotService` in `banking/services/fte_snapshot.py` with `capture_snapshot(tenant, year_month, user=None)` method
- [x] 5.2 Implement FTE distribution computation: query Clockodo time data via `DepartmentTimeAnalysisService`, group by department, compute percentage shares for departments with linked cost centers
- [x] 5.3 Implement fallback: if no Clockodo data, use UserCostProfile FTE percentages as static weights
- [x] 5.4 Create snapshot + entries, enforce uniqueness (reject if snapshot exists)
- [x] 5.5 Implement re-apply logic: find all FTE-rule-based non-manual splits for the month, delete and recreate from snapshot percentages
- [x] 5.6 Implement optional email notification on capture (use existing M365 Graph API integration)

## 6. FTE-based split resolution in CostCenterSplitService

- [x] 6.1 Extend `CostCenterSplitService.apply_rule()` to handle `fte_distribution` mode
- [x] 6.2 Implement snapshot lookup: find snapshot for transaction's month, use entry percentages
- [x] 6.3 Implement live fallback: compute from Clockodo data when no snapshot exists
- [x] 6.4 Implement static fallback: use UserCostProfile FTE percentages when no Clockodo data

## 7. Celery periodic task

- [x] 7.1 Add `capture_monthly_fte_snapshots` task in `banking/tasks.py` — daily check: for each tenant, if today matches capture day and no snapshot for last month, capture it
- [x] 7.2 Register task in Celery beat schedule

## 8. Snapshot GraphQL API

- [x] 8.1 Add `FteDistributionSnapshotType` and `FteDistributionEntryType` Strawberry types
- [x] 8.2 Add `fteDistributionSnapshots(year: Int)` query returning snapshots with entries
- [x] 8.3 Add `captureFteDistributionSnapshot(yearMonth: String!)` mutation (requires `cost_centers.config`)

## 9. Frontend: Department cost center picker

- [x] 9.1 Add cost center dropdown (Popover/Command) per department row in Settings > Integrations > Time Tracking department list
- [x] 9.2 Wire to `updateDepartment` mutation with `costCenterId` field
- [x] 9.3 Show hint when no cost centers exist

## 10. Frontend: FTE mode in split rule editor

- [x] 10.1 Add mode selector (percentage / fixed amount / FTE distribution) to SplitRuleSettings create/edit form
- [x] 10.2 Hide allocation editor when FTE distribution mode is selected
- [x] 10.3 Show "FTE distribution" label in rule list for FTE-mode rules
- [x] 10.4 Show warning when creating FTE rule and no departments have linked cost centers

## 11. Frontend: Snapshot history view

- [x] 11.1 Add "FTE Snapshots" tab/section in Accounting settings (AccountingSettingsTabs)
- [x] 11.2 Snapshot list table: month, captured date, department count, expandable detail rows
- [x] 11.3 Detail rows: department name, cost center code, FTE %, monthly income, hours
- [x] 11.4 Manual capture button with month picker, calls `captureFteDistributionSnapshot` mutation

## 12. Frontend: Snapshot settings

- [x] 12.1 Add snapshot capture day setting (number input, 1-28) in Accounting settings
- [x] 12.2 Add notification email field in Accounting settings
- [x] 12.3 Wire to tenant settings update mutation

## 13. i18n

- [x] 13.1 Add translation keys for department cost center picker (en + de)
- [x] 13.2 Add translation keys for FTE split rule mode (en + de)
- [x] 13.3 Add translation keys for snapshot history, manual capture, settings (en + de)

## 14. Tests

- [x] 14.1 Test department cost center FK: assign, clear, SET_NULL on cost center delete
- [x] 14.2 Test split rule mode field: create FTE rule without allocations, create percentage rule with allocations
- [x] 14.3 Test FTE snapshot capture: create snapshot, reject duplicate, reject future month
- [x] 14.4 Test FTE distribution computation: from Clockodo data, fallback to UserCostProfile
- [x] 14.5 Test re-apply splits on snapshot capture: auto splits replaced, manual splits preserved
- [x] 14.6 Test FTE-based split application: with snapshot, with live data, with static fallback
- [x] 14.7 Test Celery task: captures on correct day, skips if snapshot exists
- [x] 14.8 Test permissions: `cost_centers.config` required for snapshot capture
- [x] 14.9 Test tenant isolation for snapshots
