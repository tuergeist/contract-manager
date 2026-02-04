## ADDED Requirements

### Requirement: Dashboard displays Total Active Contracts
The dashboard SHALL display a KPI card showing the count of contracts with status "active" for the current tenant.

#### Scenario: Active contracts counted correctly
- **WHEN** user views the dashboard
- **THEN** the "Total Active Contracts" KPI displays the count of contracts where status=active

#### Scenario: Only tenant's contracts are counted
- **WHEN** user views the dashboard
- **THEN** only contracts belonging to the user's tenant are included in the count

### Requirement: Dashboard displays Total Contract Value (TCV)
The dashboard SHALL display the Total Contract Value, calculated as the sum of all active contract values over their committed duration.

#### Scenario: TCV calculation for fixed-term contracts
- **WHEN** a contract has start_date and end_date defined
- **THEN** TCV includes (monthly_value × months_between_dates) for that contract

#### Scenario: TCV calculation for open-ended contracts
- **WHEN** a contract has no end_date but has min_duration_months
- **THEN** TCV includes value through the minimum duration end date

#### Scenario: TCV excludes cancelled/ended contracts
- **WHEN** a contract has status "cancelled" or "ended"
- **THEN** that contract is excluded from TCV calculation

### Requirement: Dashboard displays Annual Recurring Revenue (ARR)
The dashboard SHALL display ARR, calculated as the annualized value of all recurring contract items from active contracts.

#### Scenario: ARR normalizes monthly prices to annual
- **WHEN** a contract item has monthly unit_price of €100 and quantity of 2
- **THEN** that item contributes €2,400 (100 × 2 × 12) to ARR

#### Scenario: ARR excludes one-off items
- **WHEN** a contract item has is_one_off=True
- **THEN** that item is excluded from ARR calculation

#### Scenario: ARR only includes active contracts
- **WHEN** calculating ARR
- **THEN** only items from contracts with status "active" are included

### Requirement: Dashboard displays Year-to-Date Revenue (YTD)
The dashboard SHALL display YTD revenue, calculated as the sum of recognized revenue from January 1st of the current year to today.

#### Scenario: YTD uses recognition schedule
- **WHEN** calculating YTD revenue
- **THEN** the system uses the contract recognition schedule (not billing schedule) to determine recognized amounts

#### Scenario: YTD includes partial year for new contracts
- **WHEN** a contract started mid-year
- **THEN** YTD includes only the recognized revenue from that contract's start date

### Requirement: Dashboard displays Current Year Forecast
The dashboard SHALL display the forecasted total revenue for the current calendar year.

#### Scenario: Current year forecast includes past and future
- **WHEN** calculating current year forecast
- **THEN** the sum includes recognized revenue from Jan 1 to Dec 31 of the current year

#### Scenario: Forecast respects contract end dates
- **WHEN** a contract ends mid-year
- **THEN** forecast only includes revenue up to the contract's end_date

### Requirement: Dashboard displays Next Year Forecast
The dashboard SHALL display the forecasted total revenue for the next calendar year.

#### Scenario: Next year forecast calculation
- **WHEN** calculating next year forecast
- **THEN** the sum includes projected recognized revenue from Jan 1 to Dec 31 of next year

#### Scenario: Next year excludes ending contracts
- **WHEN** a contract's end_date is before next year
- **THEN** that contract contributes nothing to next year forecast

### Requirement: KPIs include calculation explanations
Each KPI card SHALL include an info icon that, when hovered or clicked, displays a tooltip explaining what is included in the calculation.

#### Scenario: Info tooltip displays explanation
- **WHEN** user hovers over the info icon on a KPI card
- **THEN** a tooltip appears with the calculation methodology

#### Scenario: Explanations are localized
- **WHEN** the app language is German
- **THEN** KPI explanations display in German

### Requirement: GraphQL query returns all KPIs
The backend SHALL expose a `dashboardKpis` GraphQL query that returns all KPI values in a single request.

#### Scenario: Query returns complete KPI data
- **WHEN** client executes the dashboardKpis query
- **THEN** response includes: totalActiveContracts, totalContractValue, annualRecurringRevenue, yearToDateRevenue, currentYearForecast, nextYearForecast

#### Scenario: Query is tenant-scoped
- **WHEN** an authenticated user executes the dashboardKpis query
- **THEN** results are automatically filtered to the user's tenant

#### Scenario: Query requires authentication
- **WHEN** an unauthenticated request executes the dashboardKpis query
- **THEN** the request is rejected with an authentication error
