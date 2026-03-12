## Why

The existing liquidity forecast only projects future cash flows based on recurring banking patterns (detected from historical transactions). It does not account for expected income from contracts/invoices or distinguish actual vs. projected data. A proper liquidity analysis for the current year needs to combine actual banking data (past) with revenue-based income projections (future), giving a realistic view of cash position over time.

## What Changes

- New backend query `liquidityAnalysis(year)` that combines:
  - **Actual costs**: Past bank transactions with negative amounts (debits) grouped by month
  - **Projected costs**: Future months approximated from historical recurring patterns (existing `RecurringPattern` model, filtered to debits)
  - **Actual income**: Past bank transactions with positive amounts (credits) grouped by month
  - **Projected income**: Future months based on revenue forecast (contract billing schedule) minus already-paid invoices, with a configurable payment delay (default 60 days between invoice date and expected payment)
- Current balance and balance projection per month
- New dashboard section or page showing the liquidity analysis as a chart + table for the current year

## Capabilities

### New Capabilities
- `liquidity-analysis`: Backend query combining actual banking data with revenue-based income projections for current-year cash flow analysis, plus frontend visualization

### Modified Capabilities
_(none)_

## Impact

- **Backend**: New query in `apps/banking/schema.py` or `apps/contracts/schema.py`, new service function combining banking transactions, recurring patterns, and revenue forecast data
- **Frontend**: New dashboard section or dedicated page with chart (monthly bars for income/costs) and summary table
- **Data dependencies**: Requires banking transactions imported, contracts with billing schedules set up, and invoice records for payment matching
- **Existing code reuse**: Leverages `get_liquidity_forecast()` from banking forecast service, `revenue_forecast` query logic, `InvoicePaymentMatch` for paid invoice detection
