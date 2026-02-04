## Context

The dashboard is currently a placeholder showing only a title and welcome message. Users need visibility into key business metrics at a glance. The Contract model already has rich infrastructure including `get_recognition_schedule()` for calculating revenue over time, `get_duration_months()`, and `get_effective_end_date()` methods that can be leveraged for KPI calculations.

## Goals / Non-Goals

**Goals:**
- Display 6 KPI cards on the dashboard: Active Contracts, TCV, ARR, YTD Revenue, Current Year Forecast, Next Year Forecast
- Each KPI has an info tooltip explaining the calculation
- Single GraphQL query fetches all KPIs efficiently
- Support both English and German translations

**Non-Goals:**
- Caching layer (can be added later if performance becomes an issue)
- Historical trend charts or graphs
- Drill-down into individual metrics
- KPI customization or filtering

## Decisions

### 1. Backend KPI Calculation Location
**Decision**: Calculate all KPIs in a dedicated service function, exposed via a single `dashboardKpis` GraphQL query.

**Rationale**: Centralizing calculation logic in one place makes testing easier and ensures consistency. A single query reduces frontend complexity and network round-trips.

**Alternatives considered**:
- Separate queries per KPI: More flexible but adds latency and complexity
- Frontend calculation: Would require fetching all contract data, inefficient

### 2. Use Recognition Schedule for Revenue Metrics
**Decision**: Use `Contract.get_recognition_schedule()` for YTD and forecast calculations.

**Rationale**: The recognition schedule already handles complex scenarios (pro-ration, alignment dates, one-off items). Reusing it ensures consistency with other parts of the application.

### 3. ARR Calculation Approach
**Decision**: Sum `item.total_price × 12` for all recurring items in active contracts, where `total_price` uses the normalized monthly price.

**Rationale**: ContractItem already has `monthly_unit_price` property that normalizes different price periods to monthly. ARR represents current annualized run rate, so we use current prices, not historical.

### 4. TCV Calculation Approach
**Decision**: For each active contract, calculate `monthly_value × duration_months` using `get_duration_months()` which handles end dates and minimum durations.

**Rationale**: Leverages existing contract methods that already handle edge cases (open-ended contracts, minimum durations).

### 5. Frontend Component Structure
**Decision**: Create a `KPICard` component used 6 times in a responsive grid layout.

**Rationale**: Consistent styling and behavior across all KPIs. Grid layout adapts to screen sizes.

### 6. Info Tooltip Implementation
**Decision**: Use Shadcn Tooltip component with localized explanation text.

**Rationale**: Consistent with existing UI patterns. Translations stored in standard locale files.

## Risks / Trade-offs

**[Performance with large portfolios]** → For tenants with hundreds of contracts, the KPI query may be slow. Mitigation: Monitor query times; add caching layer if needed in future iteration.

**[Recognition schedule complexity]** → Edge cases in recognition scheduling could lead to unexpected KPI values. Mitigation: Comprehensive test coverage for KPI calculations; rely on existing well-tested recognition schedule methods.

**[TCV for indefinite contracts]** → Contracts without end dates use minimum duration for TCV, which may understate true value. Mitigation: Document this in the tooltip explanation so users understand the methodology.

## Files to Modify

| File | Change |
|------|--------|
| `backend/apps/contracts/schema.py` | Add `DashboardKPIsType` and `dashboardKpis` query |
| `frontend/src/features/dashboard/Dashboard.tsx` | Replace placeholder with KPI grid |
| `frontend/src/features/dashboard/KPICard.tsx` | New component for individual KPI display |
| `frontend/src/locales/en.json` | Add KPI labels and explanations |
| `frontend/src/locales/de.json` | Add German KPI labels and explanations |
| `backend/tests/test_dashboard_kpis.py` | New test file for KPI calculations |
