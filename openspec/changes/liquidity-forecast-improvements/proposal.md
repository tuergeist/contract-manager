## Why

The liquidity forecast page needs usability improvements: the date range should align to calendar year boundaries, the patterns table lacks sorting and search capabilities making it hard to manage many patterns, and users need granular control to view only costs or only income projections.

## What Changes

- Change forecast period to start Jan 1 of current year and end Jan 1 of following year (calendar year alignment)
- Add sorting to patterns table (by amount, frequency, counterparty, confidence)
- Add search/filter to patterns table by counterparty name
- Add separate toggles for income and costs (can enable/disable each independently)
- Update chart and projection table to respect the income/cost toggles

## Capabilities

### New Capabilities
None

### Modified Capabilities
- `liquidity-forecast-ui`: Add calendar year alignment, table sorting/search, and independent income/cost toggles

## Impact

- Frontend only changes to `LiquidityForecast.tsx`
- No backend changes required (existing queries support filtering)
- No API changes
