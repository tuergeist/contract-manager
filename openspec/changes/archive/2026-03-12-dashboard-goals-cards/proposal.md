## Why

Revenue stream goals (Recurring, Advanced Development, Training/Implementation) are only visible on the Forecasts > Goals tab. Users check the dashboard frequently but have to navigate to forecasts to see goal progress. Showing these goals as cards on the dashboard gives immediate visibility into revenue target tracking alongside existing KPIs and new business goals.

## What Changes

- Add a "Revenue Goals" section to the dashboard below the existing "New Business" section
- Show one card per revenue stream (Recurring, Advanced Development, Training/Implementation) with target, YTD actual, forecast, difference, and a progress bar
- Reuse the same GraphQL queries already available (`revenueGoals`, `revenueByStream`)
- Cards link to the forecasts goals tab on click

## Capabilities

### New Capabilities

_None — this is a frontend-only change reusing existing backend queries._

### Modified Capabilities

- `revenue-goals-dashboard`: Adding revenue stream goal cards to the main dashboard (currently only shown on forecasts page)

## Impact

- `frontend/src/features/dashboard/Dashboard.tsx` — add revenue goals section with cards
- `frontend/src/locales/en.json`, `de.json` — add any missing i18n keys for dashboard context
- No backend changes needed — `revenueGoals` and `revenueByStream` queries already exist
