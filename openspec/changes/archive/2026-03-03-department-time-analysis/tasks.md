## 1. Backend: Models & Migrations

- [x] 1.1 Add `Department` model to `contracts/models.py` — TenantModel, `name` CharField(100), `sort_order` IntegerField(default=0), unique_together (tenant, name)
- [x] 1.2 Add `DepartmentServiceMapping` model — TenantModel, `department` FK CASCADE, `external_service_id` CharField(50), `external_service_name` CharField(255), unique_together (tenant, external_service_id)
- [x] 1.3 Create single migration for both models
- [x] 1.4 Register both models in `contracts/admin.py`

## 2. Backend: Clockodo Provider

- [x] 2.1 Add `get_services()` method to `TimeTrackingProvider` abstract class — default raises `NotImplementedError`
- [x] 2.2 Add `get_department_time_data(date_from, date_to)` to abstract class — default raises `NotImplementedError`
- [x] 2.3 Implement `get_services()` in Clockodo provider — fetch from `/services` endpoint, return list of `{id, name}`
- [x] 2.4 Implement `get_department_time_data()` in Clockodo provider — use `entrygroups` with `grouping[]=users_id&grouping[]=services_id`, fetch `/users` for names, return flat list of `{user_id, user_name, service_id, service_name, hours}`

## 3. Backend: GraphQL Schema

- [x] 3.1 Add `DepartmentType` Strawberry type — id, name, sortOrder
- [x] 3.2 Add `DepartmentServiceMappingType` — id, externalServiceId, externalServiceName, departmentId
- [x] 3.3 Add `DepartmentTimeEntry`, `UserDepartmentRow`, `DepartmentTimeAnalysisType` types
- [x] 3.4 Add `departments` query — list of departments for tenant
- [x] 3.5 Add `clockodoServices` query — fetch services from provider
- [x] 3.6 Add `departmentTimeAnalysis(dateFrom, dateTo)` query — compute distribution + user matrix
- [x] 3.7 Add `createDepartment` mutation — name input, validate unique per tenant
- [x] 3.8 Add `updateDepartment` mutation — id + name, validate unique
- [x] 3.9 Add `deleteDepartment` mutation — cascade deletes service mappings
- [x] 3.10 Add `saveDepartmentServiceMappings` mutation — bulk replace all mappings for tenant

## 4. Backend: Tests

- [x] 4.1 Test Department CRUD mutations — create, rename, delete, reject duplicate
- [x] 4.2 Test `saveDepartmentServiceMappings` — bulk save, replace existing
- [x] 4.3 Test `clockodoServices` query — returns services from provider
- [x] 4.4 Test `departmentTimeAnalysis` query — correct distribution percentages, user matrix, unassigned services grouped, empty state
- [x] 4.5 Test Clockodo provider `get_services()` and `get_department_time_data()` — mock API responses

## 5. Frontend: Department Settings UI

- [x] 5.1 Add "Departments" section to Settings > Integrations > Time Tracking — only visible when provider configured
- [x] 5.2 Department list with inline add/rename/delete
- [x] 5.3 Service assignment table — all Clockodo services with department dropdown per row, bulk save button
- [x] 5.4 GraphQL queries/mutations for settings

## 6. Frontend: Analysis Page

- [x] 6.1 New route `/department-analysis` with `DepartmentAnalysis.tsx`
- [x] 6.2 Date range picker — defaults to Jan 1 current year to today
- [x] 6.3 Distribution section — department name, hours, percentage, visual bar
- [x] 6.4 User x Department matrix table — rows=users, columns=departments, cells=hours, total column
- [x] 6.5 Hours/percentage toggle for matrix
- [x] 6.6 Empty states — no data, no departments
- [x] 6.7 Add to sidebar navigation — conditionally visible when provider configured + departments exist

## 7. i18n

- [x] 7.1 Add translation keys to `en.json` and `de.json` — department settings, analysis page, all labels and empty states
