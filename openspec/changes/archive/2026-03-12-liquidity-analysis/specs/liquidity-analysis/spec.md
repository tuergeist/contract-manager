## ADDED Requirements

### Backend: Liquidity Analysis Service

**`get_liquidity_analysis(tenant, year, payment_delay_days=60)`** in `apps/banking/services/forecast.py`:

- Returns monthly data for all 12 months of the given year
- Each month contains:
  - `actual_costs`: Sum of bank transactions with `amount < 0` for that month (only for past/current months, up to today)
  - `actual_income`: Sum of bank transactions with `amount > 0` for that month (only for past/current months, up to today)
  - `projected_costs`: Sum of recurring pattern projections (debit patterns, `average_amount < 0`) for future days in that month
  - `projected_income`: Expected payments from revenue forecast, calculated as:
    1. Get billing schedule for all active/paused contracts for the year
    2. For each billing event, the expected payment date = billing_date + `payment_delay_days`
    3. Assign the billing amount to the month of the expected payment date
    4. Subtract amounts from invoices already matched to bank transactions (via `InvoicePaymentMatch` on `InvoiceRecord`) to avoid double-counting
    5. Only include projected income for future dates (not past months that already have actuals)
  - `total_costs`: `actual_costs + projected_costs`
  - `total_income`: `actual_income + projected_income`
  - `net`: `total_income + total_costs` (costs are negative, so this is income minus |costs|)
  - `cumulative_balance`: Running balance starting from current bank balance, adding `net` per month
  - `is_past`: `True` if the entire month is before today

- Current month handling: for the month containing today, actual data covers transactions up to today; projected data covers the remaining days of the month

- Current balance: obtained via existing `get_current_balance(tenant)`, used as the starting point for cumulative balance. Months before the balance date backfill from actual transaction sums.

### Backend: GraphQL Query

**Query**: `liquidity_analysis(year: Int!) -> LiquidityAnalysisType`

- Requires `banking.read` permission
- Returns:
  - `year: Int`
  - `current_balance: Decimal`
  - `balance_as_of: Date | None`
  - `months: [LiquidityMonthType]` — 12 entries, one per month

**`LiquidityMonthType`**:
  - `month: Date` — first day of month
  - `actual_costs: Decimal`
  - `actual_income: Decimal`
  - `projected_costs: Decimal`
  - `projected_income: Decimal`
  - `total_costs: Decimal`
  - `total_income: Decimal`
  - `net: Decimal`
  - `cumulative_balance: Decimal`
  - `is_past: Boolean`

### Frontend: Liquidity Analysis View

- New tab "Liquidity" on the Forecasts page (`/forecasts`)
- Default tab selection: existing forecast tab remains default

**Chart** (Recharts):
- Stacked bar chart with 12 monthly bars
- Each bar shows income (green, positive) and costs (red, negative) — use `total_income` and `total_costs`
- Line overlay showing `cumulative_balance` across months
- X-axis: month labels (Jan, Feb, ... Dec)
- Y-axis: EUR amounts formatted with thousand separators
- Visual distinction between actual (solid fill) and projected (striped/lighter fill) portions

**Summary table** below the chart:
- Columns: Month, Actual Costs, Projected Costs, Total Costs, Actual Income, Projected Income, Total Income, Net, Balance
- One row per month
- Footer row with totals for the year
- Negative values shown in red
- Current month row highlighted

**Controls**:
- Year selector (though spec says current year only, allow selecting the year for the query)
- No other filters needed

### i18n

Keys under `forecasts.liquidity`:
- `tab`: "Liquidity" / "Liquidität"
- `actualCosts`: "Actual Costs" / "Tatsächliche Kosten"
- `projectedCosts`: "Projected Costs" / "Prognostizierte Kosten"
- `actualIncome`: "Actual Income" / "Tatsächliche Einnahmen"
- `projectedIncome`: "Projected Income" / "Prognostizierte Einnahmen"
- `totalCosts`: "Total Costs" / "Gesamtkosten"
- `totalIncome`: "Total Income" / "Gesamteinnahmen"
- `net`: "Net" / "Netto"
- `balance`: "Balance" / "Kontostand"
- `cumulative`: "Cumulative Balance" / "Kumulierter Kontostand"
- `total`: "Total" / "Gesamt"
- `income`: "Income" / "Einnahmen"
- `costs`: "Costs" / "Kosten"
