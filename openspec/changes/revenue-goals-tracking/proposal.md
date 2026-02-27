## Why

We generate revenue from three distinct streams — Advanced Developments (project-based one-offs), Training + Implementation (delivery-based one-offs), and Recurring Revenue (subscriptions/maintenance). Today there is no way to set yearly targets per stream or measure progress against them. Leadership needs this to steer sales focus and track whether the business is on plan.

## What Changes

- **Product revenue classification**: Each product gets a `revenue_type` field classifying it as one of: `advanced_development`, `training_implementation`, or `recurring`. This determines which revenue stream it feeds.
- **Line-item revenue type override**: Contract line items without a linked product (free-text items) and discounts must have a `revenue_type` set explicitly by the user so they count toward the correct stream.
- **Revenue goals**: A new model to store yearly revenue targets per stream (e.g., "2026 Recurring Revenue goal: €500k").
- **Goals progress dashboard**: A new UI section (likely a tab on the Forecasts page) showing per-stream progress against yearly goals, combining recognized revenue YTD with forecast for the remainder of the year.

## Capabilities

### New Capabilities
- `revenue-type-classification`: Adds revenue type field to products and line items; enforces classification on unlinked items and discounts
- `revenue-goals`: Model, API, and settings UI for defining yearly revenue targets per stream
- `revenue-goals-dashboard`: Dashboard/forecasts view showing progress against goals per revenue stream, with YTD actuals and forecast

### Modified Capabilities
- `dashboard-kpis`: ARR and YTD KPIs may be broken down by revenue stream in addition to the existing totals

## Impact

- **Backend**: New `revenue_type` field on `Product` and `ContractItem` models; new `RevenueGoal` model; new GraphQL queries/mutations; migration for existing data (default classification for existing products)
- **Frontend**: Product form/list gets revenue type selector; contract item form enforces revenue type when no product selected; new goals settings UI; new goals progress view on forecasts page
- **Data migration**: Existing products and line items need a one-time classification (can default to `recurring` for subscriptions, require manual classification for one-offs)
