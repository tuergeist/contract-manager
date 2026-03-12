## 1. Backend: deal_won_date Field and Migration

- [x] 1.1 Add `deal_won_date = DateField(null=True, blank=True)` to Contract model
- [x] 1.2 Create schema migration for the new field
- [x] 1.3 Create data migration: set `deal_won_date = start_date` for all contracts where `hubspot_deal_id IS NOT NULL AND deal_won_date IS NULL`
- [x] 1.4 Add `is_new_business` property to Contract model (returns `bool(self.hubspot_deal_id)`)
- [x] 1.5 Update HubSpot sync `_sync_deal` to set `deal_won_date=closedate` when creating the contract

## 2. Backend: deal_won_date GraphQL

- [x] 2.1 Add `deal_won_date` and `is_new_business` fields to ContractType
- [x] 2.2 Add `deal_won_date` to UpdateContractInput and update_contract mutation
- [x] 2.3 Write tests: deal_won_date exposed on query, updatable via mutation, is_new_business derived correctly

## 3. Backend: NewBusinessGoal Model

- [x] 3.1 Add NewBusinessGoalType TextChoices: `new_arr`, `new_development`, `new_deal_count`
- [x] 3.2 Add NewBusinessGoal model (tenant, year, goal_type, target_amount) with unique_together
- [x] 3.3 Create migration for NewBusinessGoal
- [x] 3.4 Register NewBusinessGoal in admin

## 4. Backend: New Business Metrics Calculation

- [x] 4.1 Add `calculate_new_business_metrics(tenant, year)` function — queries contracts where hubspot_deal_id is not null, deal_won_date in year, status active/ended; returns won_new_arr, won_development_revenue, won_deal_count
- [x] 4.2 Write tests for calculate_new_business_metrics: recurring ARR, development revenue, deal count, excluded statuses

## 5. Backend: New Business GraphQL Queries and Mutations

- [x] 5.1 Add NewBusinessGoalType and NewBusinessGoalResult GraphQL types
- [x] 5.2 Add `new_business_goals(year)` query
- [x] 5.3 Add `new_business_metrics(year)` query (returns NewBusinessMetricsType with wonNewArr, wonDevelopmentRevenue, wonDealCount)
- [x] 5.4 Add `won_deals(year)` query (returns list of WonDealType with contractId, contractName, customerName, dealWonDate, annualRecurringRevenue)
- [x] 5.5 Add `set_new_business_goal(year, goal_type, target_amount)` mutation (upsert)
- [x] 5.6 Add `delete_new_business_goal(year, goal_type)` mutation
- [x] 5.7 Write tests for new business goals CRUD, metrics query, won deals query

## 6. Frontend: Contract Form — deal_won_date Field

- [x] 6.1 Add `dealWonDate` to contract GraphQL fragments (query and mutation)
- [x] 6.2 Add deal won date input field to ContractForm (date picker, optional, shown when contract has hubspot_deal_id or user wants to set it)
- [x] 6.3 Add i18n keys for deal won date label (en/de)

## 7. Frontend: Revenue Goals Settings — New Business Goals Section

- [x] 7.1 Add NEW_BUSINESS_GOALS_QUERY, SET_NEW_BUSINESS_GOAL, DELETE_NEW_BUSINESS_GOAL GraphQL operations
- [x] 7.2 Add "New Business Goals" section to RevenueGoalSettings below existing per-stream goals
- [x] 7.3 Add input fields for Won New ARR, Won Development Revenue, Won Deal Count with save/load logic
- [x] 7.4 Add i18n keys for new business goal labels (en/de)

## 8. Frontend: Goals Dashboard — New Business Section

- [x] 8.1 Add NEW_BUSINESS_METRICS_QUERY and WON_DEALS_QUERY GraphQL operations to RevenueGoalsDashboard
- [x] 8.2 Add "New Business" section below the per-stream goals table with 3 summary cards (Won ARR, Won Development, Won Deal Count) showing actual, target, difference, progress
- [x] 8.3 Add expandable "Won Deals" list (collapsed by default, lazy-loaded) with customer, contract name, won date, ARR, link to contract
- [x] 8.4 Wire year selector to new business queries
- [x] 8.5 Add i18n keys for new business dashboard section (en/de)
