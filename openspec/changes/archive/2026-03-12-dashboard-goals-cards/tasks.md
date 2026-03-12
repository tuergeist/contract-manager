## Tasks

### 1. Extend Dashboard GQL query
- [x] 1.1 Add `revenueGoals(year: $year) { id year revenueType targetAmount }` and `revenueByStream(year: $year) { revenueType ytdActual fullYearForecast }` to `DASHBOARD_KPIS_QUERY`
- [x] 1.2 Add TypeScript interfaces for the new response fields

### 2. Build Revenue Goals section
- [x] 2.1 Build goal/stream maps from query data (same pattern as `RevenueGoalsDashboard.tsx`)
- [x] 2.2 Add "Revenue Goals" section after "New Business" section with 3-column card grid
- [x] 2.3 Each card: stream name, forecast as primary value, target + difference + progress bar
- [x] 2.4 Cards without target show forecast only with "Set goals" link
- [x] 2.5 Section hidden when no goals and no forecast data
- [x] 2.6 Clicking cards navigates to `/forecasts?tab=goals`

### 3. i18n
- [x] 3.1 Add section title key (`dashboard.revenueGoals.title`) to en.json and de.json
