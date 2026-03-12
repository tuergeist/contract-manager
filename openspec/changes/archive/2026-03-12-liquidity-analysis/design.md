## Key Decisions

### 1. New service function, not modifying existing forecast

Create a new `get_liquidity_analysis(tenant, year)` function in `apps/banking/services/forecast.py` rather than modifying `get_liquidity_forecast()`. The existing function projects based on recurring patterns only and is used by the existing `liquidity_forecast` query. The new analysis combines four distinct data sources and has different semantics.

### 2. Four data sources, one monthly output

The analysis produces monthly buckets (Jan–Dec of the given year) with these sources:

| Source | Past months | Future months |
|--------|------------|---------------|
| **Costs** | Actual bank debits (`amount < 0`) | Recurring pattern projections (debits only) |
| **Income** | Actual bank credits (`amount > 0`) | Revenue forecast minus paid invoices, delayed by 60 days |

For the current month: use actuals up to today, projections for remaining days.

### 3. Revenue-based income projection with payment delay

Future income uses the contract billing schedule (same logic as `revenue_forecast` query with `pro_rata=False`):

1. Get recognition/billing schedule for all active contracts for the year
2. Each billing event produces an expected payment 60 days later (configurable via `payment_delay_days` parameter, default 60)
3. Subtract invoices already matched to bank transactions (via `InvoicePaymentMatch`) to avoid double-counting
4. Only count the payment in the month it's expected (invoice_date + 60 days), not the invoice month

This means a January invoice shows as expected income in March.

### 4. Cost projection from recurring patterns

For future months, reuse `RecurringPattern` objects but filter to `average_amount < 0` (debits only). Use the existing `project_pattern()` function. This keeps cost projection simple and based on observed patterns.

### 5. Single GraphQL query returning monthly data

New query `liquidity_analysis(year: Int!)` in banking schema returning:

```
LiquidityAnalysisType:
  year: Int
  current_balance: Decimal
  balance_as_of: Date
  months: [LiquidityMonthType]

LiquidityMonthType:
  month: Date           # First day of month
  actual_costs: Decimal  # Sum of actual bank debits (negative value)
  actual_income: Decimal # Sum of actual bank credits
  projected_costs: Decimal  # From recurring patterns (negative)
  projected_income: Decimal # From revenue forecast with delay
  total_costs: Decimal     # actual + projected
  total_income: Decimal    # actual + projected
  net: Decimal             # total_income + total_costs (costs are negative)
  cumulative_balance: Decimal # Running from current_balance + net per month
  is_past: Boolean         # True if month is fully in the past
```

### 6. Frontend: chart on the Forecasts page

Add a new tab or section on the existing Forecasts page (`/forecasts`) rather than creating a new page. Use a stacked bar chart (Recharts) showing income (green) and costs (red) per month, with a line overlay for cumulative balance. Below the chart, a summary table with the monthly breakdown.

## Risks / Trade-offs

- **Payment delay is an approximation**: Real payment timing varies per customer. The 60-day default is a simplification. Making it configurable per query allows tuning.
- **Recurring pattern quality**: Cost projections are only as good as the detected patterns. If patterns haven't been confirmed, projections may be unreliable. We filter to confirmed + high-confidence (≥0.7) patterns, same as existing forecast.
- **Double-counting risk**: If a bank credit is both matched to an invoice AND appears in revenue forecast, we must subtract matched invoices from projected income. The `InvoicePaymentMatch` join handles this.
- **Current month split**: For the current month, we show actuals for past days and projections for remaining days. This could lead to a slight discontinuity mid-month but gives the most accurate picture.

## File Changes

| File | Change |
|------|--------|
| `backend/apps/banking/services/forecast.py` | New `get_liquidity_analysis()` function |
| `backend/apps/banking/schema.py` | New types + `liquidity_analysis` query |
| `frontend/src/features/forecasts/ForecastsPage.tsx` | New liquidity analysis tab/section with chart + table |
| `frontend/src/locales/en.json` | i18n keys for liquidity analysis |
| `frontend/src/locales/de.json` | i18n keys for liquidity analysis |
