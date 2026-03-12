# Tasks: Liquidity Analysis

## Backend

- [x] Add `get_liquidity_analysis(tenant, year, payment_delay_days=60)` function in `apps/banking/services/forecast.py`: query actual bank transactions (costs/income) grouped by month, project future costs from recurring patterns (debits only), project future income from contract billing schedule with payment delay minus paid invoices, compute cumulative balance from current balance
- [x] Add `LiquidityMonthType` and `LiquidityAnalysisType` strawberry types in `apps/banking/schema.py`
- [x] Add `liquidity_analysis(year: Int!)` query to `BankingQuery` in `apps/banking/schema.py` (requires `banking.read` permission)
- [x] Write tests for `get_liquidity_analysis`: past months use actual transactions, future months use projections, payment delay shifts income, paid invoices are subtracted, current month splits actual/projected

## Frontend

- [x] Add `LIQUIDITY_ANALYSIS` GraphQL query and `LiquidityMonthType` in `ForecastsPage.tsx`
- [x] Add tab navigation to `ForecastsPage.tsx` with "Revenue" (existing content) and "Liquidity" tabs
- [x] Create liquidity chart component: stacked bar chart (Recharts) with income (green) / costs (red) bars and cumulative balance line overlay, visual distinction between actual (solid) and projected (lighter) fills
- [x] Create liquidity summary table: monthly rows with actual/projected/total columns for costs and income, net, cumulative balance; footer with year totals; negative values in red; current month highlighted
- [x] Add i18n keys under `forecasts.liquidity` in `en.json` and `de.json`
- [x] Add "Liquidity" tab to `searchablePages` in `Sidebar.tsx`
