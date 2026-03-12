## Why

Payroll arrives as one or two bank transactions per month, but needs to be split across cost centers by department. The FTE distribution across departments already exists in the department time analysis (from Clockodo data + UserCostProfile). Today there's no way to connect departments to cost centers, and no way to use the FTE distribution as a dynamic split rule. Users must manually split payroll transactions each month — tedious and error-prone.

## What Changes

- **Link departments to cost centers**: Each Department can optionally map to a CostCenter. This connects the time tracking world to the accounting world.
- **Rolling live FTE splits**: Transactions with an FTE-based split rule always use live Clockodo time data + UserCostProfile FTE% to compute the split. This means the split is dynamic until it gets "fixed" by a snapshot.
- **Monthly FTE distribution snapshot**: On a configurable day of the following month (default: 7th), the system captures the FTE distribution and monthly incomes per department as an immutable snapshot. Once a snapshot exists for a month, all transactions in that month use the fixed snapshot percentages instead of live data. Snapshots cannot be modified after creation.
- **Snapshot fixes existing splits**: When a snapshot is captured, the system re-applies splits to all FTE-rule-based transactions in that month, replacing the preliminary live-data splits with the now-fixed snapshot values. An optional email notification is sent to a configurable recipient when this happens.
- **"Split by FTE distribution" split rule type**: A new split rule mode on counterparties that, instead of using fixed percentages, resolves the split dynamically from the FTE distribution (snapshot if available, live data otherwise).
- **Manual snapshot trigger**: Users can manually trigger snapshot capture for any past month (e.g., to backfill). Existing snapshots for that month cannot be overwritten.
- **Snapshot history view**: A read-only view of all persisted FTE distribution snapshots, showing per-department percentages and monthly incomes for each month.

## Capabilities

### New Capabilities
- `dept-cost-center-link`: Link departments to cost centers via an optional FK on Department, managed in department settings.
- `fte-distribution-snapshot`: Capture and persist monthly FTE distribution (percentages + incomes) as immutable snapshots, with auto-capture scheduling, email notification, and manual trigger.
- `fte-based-split-rule`: A split rule type that uses FTE distribution (snapshot or live) to dynamically split transactions by department cost center proportions.

### Modified Capabilities
- `department-settings`: Add cost center selection to department configuration UI.
- `cost-center-splitting`: Support a new "FTE distribution" split mode alongside fixed percentage and fixed amount. Re-apply splits when snapshot is captured.

## Impact

- **Backend models**: New `FteDistributionSnapshot` and `FteDistributionEntry` models (banking app). New `cost_center` FK on Department (contracts app). New split rule mode on `CostCenterSplitRule`.
- **Backend services**: Extend `CostCenterSplitService` to resolve FTE-based rules (snapshot lookup → fallback to live). New service for snapshot capture (queries Clockodo time data + UserCostProfile FTE%/income, persists snapshot, re-applies splits, sends notification).
- **Celery tasks**: Periodic task for auto-capturing snapshots on configured day of the following month.
- **Frontend**: Department settings gets cost center picker. New snapshot history view under Accounting settings. Split rule UI gains "FTE distribution" option.
- **Migrations**: New models, new FK on Department, new fields on CostCenterSplitRule.
- **No breaking changes**: Existing split rules and manual splits are unaffected.
