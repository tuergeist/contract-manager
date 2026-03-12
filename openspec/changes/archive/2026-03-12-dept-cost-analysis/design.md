## Technical Decisions

### New model: UserCostProfile

**`UserCostProfile`** (TenantModel):
- `external_user_id` CharField(50) — Clockodo user ID
- `external_user_name` CharField(255) — cached display name
- `fte_percentage` IntegerField(default=100) — 100 = full-time, 50 = half-time
- `monthly_income` DecimalField(max_digits=10, decimal_places=2, default=0) — cost factor (salary or arbitrary value)
- `default_department` FK to Department, SET_NULL, null=True, blank=True
- unique_together: (tenant, external_user_id)

Placed in `contracts/models.py` alongside Department and DepartmentServiceMapping. Single migration.

### Clockodo provider: expose get_users()

Add `get_users()` to `TimeTrackingProvider` abstract class (default raises `NotImplementedError`). Implement in ClockodoProvider — reuse existing `_get_all_pages("users", "users")` call, return `[{id, name}]`. Also expose as a `clockodoUsers` GraphQL query mirroring the existing `clockodoServices` pattern.

### Target hours calculation

Monthly FTE target hours: `168 * (fte_percentage / 100)`. 168h = 21 working days * 8h. This is a fixed constant — no calendar-based working day computation. Simple and predictable.

### Hour backfilling logic

In the `departmentTimeAnalysis` resolver, after aggregating raw Clockodo data per user:

1. Load all `UserCostProfile` records for the tenant
2. For each user with a cost profile and a default department:
   - Calculate FTE target: `168 * fte_percentage / 100`
   - If logged hours < target → add `(target - logged)` to their default department
   - If logged hours >= target → no backfill (no capping, keep actual hours)
3. Users without a cost profile: no backfill, shown as-is (backwards compatible)

Backfilling happens at the resolver level, not in the Clockodo provider. The raw API data stays clean; backfill is an analysis-layer concern.

### Cost computation

After backfilling hours, compute cost data in the same resolver:

1. For each user with a cost profile:
   - `hourly_cost = monthly_income / target_hours` (target_hours = 168 * fte / 100)
   - `user_total_cost = hourly_cost * user_total_hours` (after backfill)
   - Per department: `dept_cost = hourly_cost * dept_hours`
2. Users without a cost profile: excluded from cost analysis (they have no income data)
3. Aggregate: `total_cost = sum of all dept costs`
4. Cost distribution: per department `cost_percentage = dept_cost / total_cost * 100`

### Extended GraphQL response type

Add cost fields to the existing `DepartmentTimeAnalysisType`:

```
DepartmentTimeAnalysisType:
  distribution: [DepartmentTimeEntry]      # existing (now with backfilled hours)
  userMatrix: [UserDepartmentRow]           # existing (now with backfilled hours)
  totalHours: Float                          # existing (now with backfilled hours)
  costDistribution: [DepartmentCostEntry]   # NEW
  totalCost: Float                           # NEW
```

New types:
- `DepartmentCostEntry`: departmentName, cost (Float), percentage (Float)
- `UserCostProfileType`: id, externalUserId, externalUserName, ftePercentage, monthlyIncome, defaultDepartmentId
- `ClockodoUserType`: id, name (like ClockodoServiceType)
- `UserCostProfileInput`: externalUserId, externalUserName, ftePercentage, monthlyIncome, defaultDepartmentId (nullable)

New queries:
- `clockodoUsers` → list of ClockodoUserType
- `userCostProfiles` → list of UserCostProfileType

New mutations:
- `saveUserCostProfiles(profiles: [UserCostProfileInput!]!)` → DeleteResult — bulk replace all profiles for tenant (same pattern as saveDepartmentServiceMappings)

### Frontend: Settings — User cost table

Add a "User Cost Settings" section below the service assignment table in Settings.tsx (still under the time tracking section, only visible when configured).

Table structure:
- Rows: all Clockodo users (fetched via `clockodoUsers` query)
- Columns: User Name | FTE % | Monthly Income | Default Department (dropdown)
- Pre-populate with saved UserCostProfile values
- Bulk save button (same pattern as service assignments)

### Frontend: Analysis page — Cost distribution

Add a new section below the existing distribution on `DepartmentAnalysis.tsx`:

- **Cost Distribution**: Same visual pattern as hour distribution — department name, cost amount, percentage bar
- Only shown when `totalCost > 0` (i.e., at least one user has income configured)
- Uses same COLORS array for consistent department coloring

The existing hour distribution and user matrix now reflect backfilled hours automatically (no UI toggle needed — backfill is always applied when profiles exist).

### Caching

The existing 1h cache on Clockodo API data (`dept_time_{tenant}_{from}_{to}`) remains unchanged. Backfill and cost computation happen after cache retrieval, so changing FTE/income/default-department takes effect immediately without cache invalidation.

### i18n

Add keys under `settings.departments` (for user cost table) and `departmentAnalysis` (for cost distribution section) in both `en.json` and `de.json`.
