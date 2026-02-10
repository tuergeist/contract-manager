## 1. Backend Models

- [x] 1.1 Create `RecurringPattern` model in `apps/banking/models.py` with fields: tenant FK, counterparty_name, counterparty_iban, average_amount, frequency (choices: monthly/quarterly/semi_annual/annual/irregular), day_of_month, confidence_score, is_confirmed, is_ignored, is_paused, last_occurrence, created_at, updated_at
- [x] 1.2 Add M2M relationship `source_transactions` from RecurringPattern to BankTransaction
- [x] 1.3 Create and run migrations for RecurringPattern model

## 2. Pattern Detection Service

- [x] 2.1 Create `apps/banking/services/pattern_detection.py` with similarity scoring function: counterparty match (+1), amount match within 5% (+1), timing pattern match (+1)
- [x] 2.2 Implement `detect_recurring_patterns(tenant)` function that analyzes last 18 months of transactions and groups by similarity score ≥ 2
- [x] 2.3 Implement frequency detection logic: calculate intervals between grouped transactions, classify as monthly/quarterly/annual
- [x] 2.4 Implement confidence scoring: higher score for more occurrences, consistent timing, exact amount matches
- [x] 2.5 Write tests for pattern detection with various transaction scenarios

## 3. Forecast Projection Service

- [x] 3.1 Create `apps/banking/services/forecast.py` with `project_pattern(pattern, months=12)` function that generates future occurrence dates
- [x] 3.2 Implement `get_liquidity_forecast(tenant, months=12)` that aggregates current balance + projected patterns
- [x] 3.3 Implement `get_current_balance(tenant)` to sum closing balances across all accounts
- [x] 3.4 Write tests for forecast projection logic

## 4. GraphQL Schema

- [x] 4.1 Add `RecurringPatternType` to `apps/banking/schema.py` with all fields including computed `projected_next_date`
- [x] 4.2 Add `recurringPatterns` query returning patterns for tenant (filterable by is_confirmed, is_ignored)
- [x] 4.3 Add `liquidityForecast` query returning monthly projections with balance, costs, income for next N months
- [x] 4.4 Add `confirmPattern(patternId)` mutation setting is_confirmed=true
- [x] 4.5 Add `ignorePattern(patternId)` mutation setting is_ignored=true
- [x] 4.6 Add `restorePattern(patternId)` mutation setting is_ignored=false
- [x] 4.7 Add `updatePattern(patternId, amount, frequency, dayOfMonth)` mutation for manual adjustments
- [x] 4.8 Add `pausePattern(patternId)` / `resumePattern(patternId)` mutations
- [x] 4.9 Add `detectPatterns` mutation to trigger pattern detection manually

## 5. Frontend Page Structure

- [x] 5.1 Create `frontend/src/features/liquidity/LiquidityForecast.tsx` page component
- [x] 5.2 Add route `/liquidity-forecast` in App.tsx
- [x] 5.3 Add "Liquidity Forecast" menu item to Sidebar.tsx with chart icon
- [x] 5.4 Add translations for liquidity forecast in en.json and de.json

## 6. Frontend Forecast Chart

- [x] 6.1 Install recharts library if not present (or use existing charting solution)
- [x] 6.2 Create `ForecastChart` component showing 12-month projected balance line
- [x] 6.3 Add visual distinction for confirmed (solid) vs auto-detected (dashed) projections
- [x] 6.4 Display current balance as starting point with "as of" date

## 7. Frontend Patterns List

- [x] 7.1 Create `PatternsList` component displaying detected recurring patterns
- [x] 7.2 Add Confirm/Ignore action buttons for each pattern
- [x] 7.3 Add filter toggles for Costs/Income/All
- [x] 7.4 Add expandable row to show source transactions for each pattern
- [x] 7.5 Create `EditPatternModal` for manual amount/frequency adjustments

## 8. Frontend Projection Table

- [x] 8.1 Create `ProjectionTable` component showing month-by-month breakdown
- [x] 8.2 Add expandable rows to show individual projected transactions per month
- [x] 8.3 Display monthly subtotals for costs, income, and net

## 9. Integration & Polish

- [x] 9.1 Add permission check for liquidity forecast page (require banking read permission)
- [x] 9.2 Add loading states and error handling throughout
- [x] 9.3 Add empty state when no patterns detected with helpful message
- [x] 9.4 Test end-to-end flow: import transactions → detect patterns → view forecast
