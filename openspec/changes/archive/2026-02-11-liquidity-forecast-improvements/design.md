## Context

The liquidity forecast page (`LiquidityForecast.tsx`) was recently implemented with basic functionality. Users have requested improvements for better usability: calendar year alignment, table management features, and granular filtering.

Current state:
- Forecast uses a rolling 12-month window from current date
- Patterns table has no sorting or search
- Single "Costs/Income/All" filter toggle (mutually exclusive)

## Goals / Non-Goals

**Goals:**
- Align forecast period to calendar year (Jan 1 - Jan 1)
- Add column sorting to patterns table
- Add search/filter by counterparty name
- Allow independent toggling of income and costs display

**Non-Goals:**
- Custom date range selection (calendar year is sufficient)
- Backend changes (frontend-only improvements)
- Persisting filter preferences across sessions

## Decisions

### 1. Calendar Year Date Range
Use `new Date(currentYear, 0, 1)` for start and `new Date(currentYear + 1, 0, 1)` for end. The backend `liquidityForecast` query already accepts a `months` parameter - calculate months from Jan 1 to cover full year.

### 2. Table Sorting
Use local state for sort column and direction. Sort options:
- Counterparty name (alphabetical)
- Amount (numeric, absolute value)
- Frequency (custom order: monthly > quarterly > semi-annual > annual > irregular)
- Confidence score (numeric)

Implement with `useMemo` to avoid re-sorting on every render.

### 3. Search/Filter
Add search input above patterns table. Filter by `counterparty_name` using case-insensitive includes. Debounce input (300ms) to avoid excessive re-renders.

### 4. Independent Income/Costs Toggles
Replace single "type" filter with two boolean states: `showIncome` and `showCosts`. Both default to true. UI uses two toggle buttons (can both be on, both off, or one of each).

Filter patterns client-side: `amount > 0` for income, `amount < 0` for costs.

## Risks / Trade-offs

**Large pattern lists may slow sorting** → Use `useMemo` with proper dependencies; patterns list is typically <100 items so acceptable.

**Both toggles off shows empty chart** → Acceptable UX; user can re-enable. Consider showing a hint message.
