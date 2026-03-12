## Technical Decisions

### Models in contracts app

**`Department`** (TenantModel):
- `name` CharField(100), unique_together with tenant
- `sort_order` IntegerField(default=0) for display ordering

**`DepartmentServiceMapping`** (TenantModel):
- `department` FK to Department, CASCADE
- `external_service_id` CharField(50) — Clockodo service ID
- `external_service_name` CharField(255) — cached service name for display
- unique_together: (tenant, external_service_id) — one department per service

No separate migration for these — single migration file for both models.

### Clockodo provider: new methods

**`get_services() -> list[dict]`**: Fetch all services from `/services` endpoint. Returns list of `{id, name}`. This already happens inside `get_time_summary()` but isn't exposed as a standalone method.

**`get_department_time_data(date_from, date_to) -> list[dict]`**: Fetch time entries grouped by user AND service using a single `entrygroups` call with `grouping[]=users_id&grouping[]=services_id`. Also fetches `/users` for user name lookup. Returns flat list of `{user_id, user_name, service_id, service_name, hours}`.

Key API detail: Clockodo's `entrygroups` with double grouping returns nested groups — outer group is users_id, inner subgroups are services_id. This gives us user × service in one API call. No need for per-project filtering since we want tenant-wide data.

### Abstract provider interface

Add `get_services()` and `get_department_time_data()` to `TimeTrackingProvider` abstract class. Default implementations raise `NotImplementedError` for backwards compatibility.

### GraphQL schema

**New types:**
- `DepartmentType`: id, name, sortOrder
- `DepartmentServiceMappingType`: id, externalServiceId, externalServiceName, departmentId
- `DepartmentTimeEntry`: departmentName, hours, percentage
- `UserDepartmentRow`: userName, departments (list of {departmentName, hours, percentage}), totalHours
- `DepartmentTimeAnalysisType`: distribution (list of DepartmentTimeEntry), userMatrix (list of UserDepartmentRow), totalHours

**New queries (in contracts schema):**
- `departments` → list of DepartmentType
- `clockodoServices` → list of available services from provider (for assignment UI)
- `departmentTimeAnalysis(dateFrom: Date, dateTo: Date)` → DepartmentTimeAnalysisType

**New mutations (in contracts schema):**
- `createDepartment(name: String!)` → DeleteResult (success/error pattern)
- `updateDepartment(id: ID!, name: String!)` → DeleteResult
- `deleteDepartment(id: ID!)` → DeleteResult
- `saveDepartmentServiceMappings(mappings: [DepartmentServiceMappingInput!]!)` → DeleteResult
  - Bulk save: accepts full list of {externalServiceId, externalServiceName, departmentId}. Replaces all existing mappings for tenant. Simpler than individual add/remove.

### Analysis computation (backend)

The `departmentTimeAnalysis` resolver:
1. Fetch raw user × service data from provider via `get_department_time_data()`
2. Load department service mappings from DB
3. Map each (user, service) entry to a department (or "Unassigned")
4. Aggregate into department distribution + user matrix
5. Compute percentages

No caching via Celery — data is fetched live from Clockodo on each request. The `entrygroups` endpoint is fast (single aggregated call). Django's cache framework can be used for short-term caching (5 minutes) to avoid redundant API calls during page interaction.

### Frontend: Settings

Add "Departments" section to Settings > Integrations > Time Tracking (in `Settings.tsx`), below existing provider config. Two parts:

1. **Department list**: Simple inline list with add/rename/delete. No separate page.
2. **Service assignment table**: Table of all Clockodo services with a department dropdown per row. Bulk save button. Uses `clockodoServices` query to fetch fresh service list.

### Frontend: Analysis page

New route `/department-analysis` with component `DepartmentAnalysis.tsx` in `features/contracts/`.

Layout:
- Date range picker (two date inputs, defaults to Jan 1 current year – today)
- **Distribution section**: Horizontal stacked bar or simple table with department name, hours, percentage, visual bar
- **User matrix section**: Table with toggle (hours/percentage). Columns: User name | Dept 1 | Dept 2 | ... | Total

Navigation: Add to sidebar under "Time Tracking" or as a sub-item. Conditionally visible when provider configured + departments exist. Use a new `departmentAnalysisVisible` field on `timeTrackingSettings` query, or check client-side by querying departments.

### i18n

Add keys under `departmentAnalysis` namespace in both `en.json` and `de.json`.
