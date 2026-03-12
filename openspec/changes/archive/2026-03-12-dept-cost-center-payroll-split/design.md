## Context

Payroll arrives as one or two bank transactions per month but needs to be allocated across cost centers by department. The department model exists in the contracts app with basic fields (name, sort_order). UserCostProfile already tracks FTE percentages and monthly incomes per user with a default department FK. The CostCenterSplitRule model in the banking app currently supports two implicit modes (percentage and fixed_amount) via CostCenterSplitAllocation entries. CostCenterSplitService handles rule matching and split application.

The missing pieces: departments have no link to cost centers, split rules have no FTE-based mode, and there's no mechanism to snapshot FTE distributions for month-end finalization.

## Goals / Non-Goals

**Goals:**
- Connect departments to cost centers via a simple FK
- Add an FTE-distribution split rule mode that resolves dynamically from time tracking data
- Capture immutable monthly snapshots that finalize preliminary splits
- Re-apply splits when a snapshot replaces live data with fixed values
- Provide snapshot history UI for audit/review

**Non-Goals:**
- Changing existing percentage or fixed-amount split modes
- Modifying the UserCostProfile or Clockodo integration models
- Per-employee cost center assignment (department-level only)
- Retroactive snapshot editing or deletion

## Decisions

### D1: Add `cost_center` FK to Department model (contracts app)

The Department model lives in the contracts app. Rather than moving it, add a nullable FK to `banking.CostCenter` with `SET_NULL` on delete. This creates a cross-app FK dependency (contracts → banking), but since banking already depends on contracts for nothing, this direction is clean.

**Alternative considered:** Separate mapping table. Rejected — a simple FK is sufficient since it's a 1:N relationship (many departments can share one cost center).

### D2: Add `mode` field to CostCenterSplitRule

Add a CharField with choices `percentage`, `fixed_amount`, `fte_distribution` (default: `percentage`). FTE distribution rules have no allocations — the service resolves them dynamically. Existing rules get `percentage` or `fixed_amount` based on whether their allocations use percentage or fixed_amount fields, set via data migration.

**Alternative considered:** Separate model for FTE rules. Rejected — the rule matching logic (counterparty → pattern → priority) is identical; only the resolution differs.

### D3: FTE distribution resolution: snapshot → live fallback

When applying an FTE-based rule:
1. Look for `FteDistributionSnapshot` for the transaction's month
2. If found, use snapshot entries' percentages
3. If not found, compute live from Clockodo time data for that month:
   - Query `DepartmentTimeAnalysis` service (already exists for the department analysis page)
   - Group hours by department, filter to departments with linked cost centers
   - Compute percentage shares from hours ratio
4. If no Clockodo data at all, fall back to UserCostProfile FTE percentages as static weights

This keeps live splits as "best estimate" until the snapshot finalizes them.

### D4: Snapshot models in the banking app

Two new models in `banking/models.py`:
- **FteDistributionSnapshot**: `tenant`, `year_month` (CharField "YYYY-MM"), `captured_at` (DateTimeField), `captured_by` (FK User, nullable for auto). Unique constraint on `(tenant, year_month)`.
- **FteDistributionEntry**: `snapshot` FK, `department` FK (nullable, SET_NULL), `department_name` (denormalized), `cost_center` FK (nullable, SET_NULL), `cost_center_code` (denormalized), `fte_percentage` (Decimal), `monthly_income_total` (Decimal), `hours_total` (Decimal).

Denormalized name/code fields ensure the snapshot remains readable even if departments or cost centers are renamed/deleted.

### D5: Snapshot capture service

New `FteSnapshotService` in `banking/services/fte_snapshot.py`:
- `capture_snapshot(tenant, year_month, user=None)`: Validates month is not future, checks no existing snapshot, computes FTE distribution, creates snapshot + entries, re-applies FTE-rule splits for all transactions in that month, optionally sends email notification.
- Reuse `DepartmentTimeAnalysisService` for computing hours/FTE data.

### D6: Celery periodic task for auto-capture

Add `capture_monthly_fte_snapshots` to `banking/tasks.py` as a daily periodic task. On each run:
1. For each tenant, check if today matches their configured capture day (default: 7)
2. If yes, attempt to capture last month's snapshot (skip if already exists)

Running daily with an idempotent check is simpler and more resilient than scheduling exactly on the Nth day.

### D7: Snapshot capture day in tenant settings

Add `fte_snapshot_capture_day` (IntegerField, default=7) and `fte_snapshot_notification_email` (EmailField, nullable) to the tenant settings JSON field or as model fields. Use the existing tenant settings pattern.

### D8: Re-apply splits on snapshot capture

When a snapshot is captured, find all `TransactionCostCenterSplit` entries for that month that were created by an FTE-based rule (`is_manual=False` and `rule.mode='fte_distribution'`). Delete them and re-create from snapshot percentages. Manual splits (`is_manual=True`) are never touched.

### D9: Frontend — department cost center picker

Add a cost center dropdown per department row in the existing department list (Settings > Integrations > Time Tracking). Use the Popover/Command pattern (Shadcn) consistent with other selectors. The `updateDepartment` mutation gets a `costCenterId` field.

### D10: Frontend — snapshot history in Accounting settings

Add a "FTE Snapshots" section under Accounting settings (new tab or section in CostCenterSettings). Show a table of snapshots (month, captured date, department count). Expandable rows show per-department breakdown. Manual capture button with month picker.

### D11: Frontend — FTE mode in split rule editor

Extend SplitRuleSettings to support mode selection. When "FTE distribution" is selected, hide the allocation editor (no manual percentages needed). Show a preview of current FTE distribution if available.

## Risks / Trade-offs

**[Cross-app FK]** Department (contracts) → CostCenter (banking) creates a cross-app dependency. → Acceptable since it's a leaf FK with SET_NULL. No circular dependencies introduced.

**[Live data accuracy]** Live FTE splits before snapshot capture are estimates based on hours-to-date. → Acceptable — the snapshot mechanism explicitly exists to finalize these. Users understand pre-snapshot splits are preliminary.

**[Clockodo dependency for live data]** If Clockodo integration is not configured, live FTE computation has no time data. → Fallback to UserCostProfile FTE percentages as static weights. Document this behavior.

**[Snapshot re-application performance]** Re-applying splits for a month could touch many transactions. → For typical payroll (1-2 transactions/month per rule), this is negligible. No bulk optimization needed.

**[Daily Celery task]** Running daily for a monthly event adds minor overhead. → Idempotent check is cheap. Simpler than cron-scheduling for specific days.
