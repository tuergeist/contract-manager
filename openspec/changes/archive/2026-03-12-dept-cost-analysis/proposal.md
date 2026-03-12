## Why

The department time analysis currently shows hour distribution only. To understand actual cost allocation across departments, we need to factor in employee compensation and normalize for FTE. An employee working 50% FTE but earning a high salary has a different cost impact than their hour share suggests. Backfilling untracked hours to a default department ensures the cost model reflects full employment cost, not just logged time.

## What Changes

- Add per-user settings in the department settings UI: FTE percentage (default 100%), monthly income (cost factor), and default department
- Fetch user list from Clockodo for the settings table
- Backfill untracked hours: if a user logged fewer hours than their FTE-adjusted monthly target (e.g. 168h for 100% FTE), allocate the remaining hours to their default department
- Add cost analysis section to the department analysis page: compute hourly cost per user (income / FTE-adjusted target hours), then derive total cost per department
- Show cost distribution alongside the existing hour distribution — percentage of total cost per department

## Capabilities

### New Capabilities
- `user-cost-settings`: Per-user FTE, income, and default department configuration in settings
- `department-cost-analysis`: Cost-based department analysis with hour backfilling and cost distribution

### Modified Capabilities
- `department-time-analysis`: Hour backfilling changes the user matrix — untracked hours are filled to the default department based on FTE target

## Impact

- **Backend models**: New `UserCostProfile` model (tenant, external_user_id, fte_percentage, monthly_income, default_department FK)
- **Backend schema**: New query for Clockodo users, new mutation to save user cost profiles, extended analysis resolver with backfill + cost computation
- **Frontend settings**: New user cost table in department settings section
- **Frontend analysis**: New cost distribution section on the analysis page
- **Clockodo provider**: Already has user fetching via `_get_all_pages("users", "users")` — needs to be exposed as a query
