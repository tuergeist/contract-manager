## Why

We have bank transaction data but no visibility into future cash position. Manually tracking recurring costs is tedious and error-prone. By auto-detecting repeating payments and projecting them forward, we can forecast liquidity and anticipate cash needs before they become problems.

## What Changes

- Add new "Liquidity Forecast" page accessible from main navigation
- Implement recurring payment detection algorithm that groups transactions by similarity (2+ of: same receiver, same amount, same timing pattern)
- Project detected recurring costs into future months
- Display forecast visualization showing expected cash-flow over time
- Allow manual confirmation/adjustment of detected recurring payments

## Capabilities

### New Capabilities
- `recurring-payment-detection`: Algorithm to identify recurring payments from bank transactions based on receiver, amount, and timing similarities (2+ matches required)
- `liquidity-forecast-ui`: New page showing projected cash-flow with detected recurring costs, manual adjustments, and time-based visualization

### Modified Capabilities
<!-- None - this builds on existing banking data without changing its requirements -->

## Impact

- **Frontend**: New route `/liquidity-forecast`, new sidebar menu item, new forecast visualization components
- **Backend**: New models for recurring payment patterns, new GraphQL queries for forecast data
- **Dependencies**: Uses existing `banking` app transaction data
- **Data**: Read-only access to bank transactions; new tables for detected patterns and user confirmations
