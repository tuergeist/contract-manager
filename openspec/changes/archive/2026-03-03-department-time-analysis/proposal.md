## Why

We need visibility into how staff time is distributed across business functions (Sales & Marketing, G&A, R&D, etc.). Clockodo tracks time by "Leistungen" (services), but there's no way to group these services into departments for high-level analysis. This makes it hard to answer questions like "What percentage of our time goes to Sales vs. Engineering?"

## What Changes

- New `Department` model to define departments (e.g. "Sales & Marketing", "G&A", "R&D") per tenant
- New `DepartmentServiceMapping` to assign Clockodo Leistungen (services) to departments
- Settings UI to manage departments and assign services to them
- New standalone analysis page showing:
  - Department time distribution as percentage breakdown (100% = total tracked hours)
  - User × Department matrix table (rows = users, columns = departments, cells = hours/percentage)
- New Clockodo provider method to fetch time entries grouped by user and service
- New GraphQL query for department time analysis with date range filtering

## Capabilities

### New Capabilities
- `department-settings`: Manage departments and assign Clockodo services to them in settings
- `department-time-analysis`: Analyze time distribution across departments, including per-user breakdown matrix

### Modified Capabilities

## Impact

- **Backend models**: New `Department` and `DepartmentServiceMapping` models in contracts app
- **Clockodo provider**: New method using `entrygroups` with `users_id` + `services_id` grouping, plus `/users` endpoint for user names
- **GraphQL schema**: New query for department analysis data, new mutations for department CRUD and service assignment
- **Frontend**: New settings section under Integrations > Time Tracking, new analysis page/tab
- **Celery**: No new tasks needed — analysis is computed on-demand from Clockodo API (cached briefly)
