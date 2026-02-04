## Why

The dashboard is currently a placeholder with no actionable information. Users need visibility into key business metrics to understand their contract portfolio health, revenue performance, and future forecasts at a glance.

## What Changes

- Add KPI cards to dashboard showing:
  - **Total Active Contracts**: Count of contracts with status=active
  - **Total Contract Value (TCV)**: Sum of all contract values over their duration
  - **Annual Recurring Revenue (ARR)**: Annualized value of recurring contract items
  - **Year-to-Date Revenue (YTD)**: Revenue recognized from Jan 1 to today
  - **Current Year Forecast**: Projected total revenue for the current calendar year
  - **Next Year Forecast**: Projected total revenue for the next calendar year
- Each KPI includes an info tooltip explaining what's included in the calculation
- Backend GraphQL query to compute KPIs efficiently

## Capabilities

### New Capabilities
- `dashboard-kpis`: GraphQL query and React components for displaying contract portfolio KPIs with calculation explanations

### Modified Capabilities
<!-- None - this is additive functionality -->

## Impact

- **Backend**: New `DashboardKPIs` GraphQL type and `dashboardKpis` query in contracts schema
- **Frontend**: Replace placeholder Dashboard component with KPI card grid
- **Translations**: Add KPI labels and tooltip explanations in en/de
- **Performance**: KPI query aggregates data - consider caching for large portfolios
