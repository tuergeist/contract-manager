## Design: Dashboard Revenue Goal Cards

### Approach

Add a "Revenue Goals" section to Dashboard.tsx, positioned after the existing "New Business" section. Reuse the same card style already used for new business goals (inline progress bar, target/difference display). No new backend queries needed — extend the existing `DASHBOARD_KPIS_QUERY` to include `revenueGoals` and `revenueByStream`.

### Data Flow

1. Extend `DASHBOARD_KPIS_QUERY` in `Dashboard.tsx` to also fetch:
   - `revenueGoals(year: $year)` → `{ revenueType, targetAmount }`
   - `revenueByStream(year: $year)` → `{ revenueType, ytdActual, fullYearForecast }`
2. Build goal/stream maps identical to `RevenueGoalsDashboard.tsx`
3. Render cards using the same pattern as the new business cards (not KPICard — the goal cards with progress bars)

### Card Design

Each revenue stream card shows:
- **Title**: Stream name (e.g., "Recurring", "Advanced Development", "Training & Implementation")
- **Primary value**: Full-year forecast (the most actionable number)
- **Below value**: Target amount, difference (green/red), progress bar with percentage
- **No target set**: Show forecast only with a "Set goals" link to settings

Use the same 3-column grid as new business cards. Clicking a card navigates to `/forecasts?tab=goals`.

### Streams

Use the same `STANDARD_STREAMS` constant from `RevenueGoalsDashboard.tsx`:
- `recurring` → "Recurring"
- `advanced_development` → "Advanced Development"
- `training_implementation` → "Training & Implementation"

Also show a total card (4th card spanning full width or as last in grid) if any targets are set.

### Visibility

Only show the section when revenue goals exist for the current year OR there is forecast data. Hide entirely if both are empty (same pattern as new business section).

### Files Changed

| File | Change |
|------|--------|
| `Dashboard.tsx` | Add GQL fields, revenue goals section with cards |
| `en.json` / `de.json` | Add section title i18n key if needed |
