## 1. Backend: Revenue Type on Product and ContractItem

- [x] 1.1 Add RevenueType TextChoices to contracts app (shared between Product and ContractItem): `advanced_development`, `training_implementation`, `recurring`
- [x] 1.2 Add `revenue_type` CharField to Product model (nullable for migration, with choices)
- [x] 1.3 Add `revenue_type` CharField to ContractItem model (nullable, with choices)
- [x] 1.4 Add `get_effective_revenue_type()` method on ContractItem (item override → product → None)
- [x] 1.5 Create migration: add fields + data migration to set subscription products to `recurring`
- [x] 1.6 Write tests for `get_effective_revenue_type()` (product inheritance, explicit override, no-product cases)

## 2. Backend: GraphQL for Revenue Type

- [x] 2.1 Add `revenue_type` field to ProductType in products/schema.py
- [x] 2.2 Add `revenue_type` and `effective_revenue_type` fields to ContractItemType in contracts/schema.py (all 3 construction sites)
- [x] 2.3 Add `revenue_type` to product create/update mutations input
- [x] 2.4 Add `revenue_type` to add_contract_item and update_contract_item mutations input
- [x] 2.5 Add `revenue_type` filter parameter to products query
- [x] 2.6 Write tests for GraphQL revenue type on products and items

## 3. Frontend: Revenue Type on Products

- [x] 3.1 Update product GraphQL queries/mutations to include `revenueType`
- [x] 3.2 Add revenue type column to product list table
- [x] 3.3 Add revenue type filter dropdown to product list
- [x] 3.4 Add revenue type selector to product create/edit form
- [x] 3.5 Add i18n strings (de + en) for revenue type labels and filter

## 4. Frontend: Revenue Type on Contract Items

- [x] 4.1 Update contract item GraphQL fragments to include `revenueType` and `effectiveRevenueType`
- [x] 4.2 Add revenue type dropdown to AddItemModal (visible + required when no product selected, read-only when product selected)
- [x] 4.3 Add revenue type dropdown to EditItemModal (same conditional logic)
- [x] 4.4 Show inherited revenue type as read-only label when product is selected
- [x] 4.5 Add i18n strings (de + en) for contract item revenue type UI

## 5. Backend: RevenueGoal Model and API

- [x] 5.1 Create RevenueGoal model (TenantModel: year, revenue_type, target_amount; unique_together tenant+year+revenue_type)
- [x] 5.2 Create migration for RevenueGoal
- [x] 5.3 Register RevenueGoal in admin
- [x] 5.4 Add RevenueGoalType to GraphQL schema
- [x] 5.5 Add `revenueGoals(year: Int!)` query returning goals for a year + tenant
- [x] 5.6 Add `setRevenueGoal` mutation (upsert) and `deleteRevenueGoal` mutation
- [x] 5.7 Write tests for revenue goals CRUD via GraphQL

## 6. Frontend: Revenue Goals Settings

- [x] 6.1 Create RevenueGoalSettings component with year selector and 3 target amount inputs
- [x] 6.2 Add GraphQL queries/mutations for revenue goals (revenueGoals, setRevenueGoal, deleteRevenueGoal)
- [x] 6.3 Add "Revenue Goals" sub-tab to GeneralSettingsTabs (route: /settings/general/revenue-goals)
- [x] 6.4 Implement save logic: upsert filled goals, delete cleared goals
- [x] 6.5 Add i18n strings (de + en) for revenue goals settings

## 7. Backend: Revenue by Stream Query

- [x] 7.1 Implement `calculate_revenue_by_stream(tenant, year)` function that iterates active contracts, computes recognition schedule, and groups by effective_revenue_type
- [x] 7.2 Return per-stream: ytd_actual (Jan 1 → today), full_year_forecast (Jan 1 → Dec 31)
- [x] 7.3 Include "unclassified" bucket for items without effective revenue type
- [x] 7.4 Add `revenueByStream(year: Int!)` GraphQL query with RevenueStreamData type
- [x] 7.5 Write tests for revenue by stream calculation (recurring, one-off, mixed, unclassified)

## 8. Frontend: Goals Dashboard Tab

- [x] 8.1 Add "Goals" tab to Forecasts page tab bar (URL: /forecasts?tab=goals)
- [x] 8.2 Create RevenueGoalsDashboard component
- [x] 8.3 Add year selector to Goals tab
- [x] 8.4 Display per-stream rows: target, YTD actual, full-year forecast, progress %
- [x] 8.5 Add progress bar visualization per stream (with over-target coloring)
- [x] 8.6 Add total row summing all streams
- [x] 8.7 Handle missing goals (show actuals/forecast without progress bar, link to settings)
- [x] 8.8 Handle unclassified bucket (show warning with amount)
- [x] 8.9 Add i18n strings (de + en) for goals dashboard
