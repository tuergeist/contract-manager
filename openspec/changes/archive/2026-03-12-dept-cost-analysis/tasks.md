## 1. Backend Model & Migration

- [x] 1.1 Add UserCostProfile model to contracts/models.py (TenantModel, fields: external_user_id, external_user_name, fte_percentage, monthly_income, default_department FK, unique_together on tenant+external_user_id)
- [x] 1.2 Create and run migration

## 2. Clockodo Provider

- [x] 2.1 Add get_users() to TimeTrackingProvider abstract class (default raises NotImplementedError)
- [x] 2.2 Implement get_users() in ClockodoProvider — reuse _get_all_pages("users", "users"), return [{id, name}]

## 3. GraphQL Schema — Types & Queries

- [x] 3.1 Add ClockodoUserType (id, name) and clockodoUsers query (mirrors clockodoServices pattern)
- [x] 3.2 Add UserCostProfileType (id, externalUserId, externalUserName, ftePercentage, monthlyIncome, defaultDepartmentId) and userCostProfiles query
- [x] 3.3 Add UserCostProfileInput and saveUserCostProfiles mutation (bulk replace pattern like saveDepartmentServiceMappings)
- [x] 3.4 Add DepartmentCostEntry type (departmentName, cost, percentage) and extend DepartmentTimeAnalysisType with costDistribution and totalCost fields

## 4. Backend — Backfill & Cost Logic

- [x] 4.1 Add hour backfilling logic in departmentTimeAnalysis resolver: load UserCostProfile records, compute FTE target (168 * fte/100), add (target - logged) to default department when logged < target
- [x] 4.2 Add cost computation after backfill: hourly_cost = monthly_income / target_hours, aggregate dept_cost and cost_percentage, populate costDistribution and totalCost

## 5. Backend Tests

- [x] 5.1 Test UserCostProfile model CRUD and unique constraint
- [x] 5.2 Test clockodoUsers query and saveUserCostProfiles mutation
- [x] 5.3 Test hour backfilling: partial hours backfilled, full hours not capped, no backfill without profile or without default department
- [x] 5.4 Test cost computation: hourly cost calculation, department cost aggregation, zero-income users excluded

## 6. Frontend — i18n

- [x] 6.1 Add i18n keys to en.json and de.json for user cost settings (settings.departments.*) and cost distribution (departmentAnalysis.*)

## 7. Frontend — Settings: User Cost Table

- [x] 7.1 Add clockodoUsers and userCostProfiles GraphQL queries and saveUserCostProfiles mutation to Settings.tsx
- [x] 7.2 Add user cost table UI: rows from clockodoUsers, columns for User Name / FTE % / Monthly Income / Default Department dropdown, pre-populated from saved profiles
- [x] 7.3 Add bulk save button for user cost profiles (same pattern as service assignments)

## 8. Frontend — Analysis: Cost Distribution

- [x] 8.1 Update departmentTimeAnalysis query to include costDistribution and totalCost fields
- [x] 8.2 Add cost distribution section to DepartmentAnalysis.tsx: department name, cost amount, percentage bar (same visual pattern as hour distribution, only shown when totalCost > 0)
