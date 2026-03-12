## Why

The revenue goals dashboard currently tracks forecast vs target by revenue stream, but cannot distinguish between new business (won deals) and existing business (renewals). HubSpot-imported contracts represent won deals, but there's no dedicated `deal_won_date` field — the close date is only used as `start_date`. To enable goals like "won new ARR this year" or "won development revenue", we need to track when a deal was won and whether a contract is new business vs existing.

## What Changes

- Add `deal_won_date` field to Contract model, auto-populated from HubSpot `closedate` on import
- Add `is_new_business` derived property: contracts with a `hubspot_deal_id` are new business; contracts without are existing business (manually created)
- Extend the RevenueGoal model to support new goal types beyond per-stream targets (e.g., "new ARR won", "new development invoiced")
- Add a "New Business" section to the Goals dashboard showing won deals, won ARR, and won revenue by stream for the selected year
- Backfill `deal_won_date` from HubSpot for existing imported contracts

## Capabilities

### New Capabilities
- `deal-won-date`: Store and manage the deal won date on contracts, including HubSpot backfill and sync
- `new-business-goals`: New goal types for tracking won deals (new ARR, new development revenue, etc.) and dashboard section showing new business metrics

### Modified Capabilities
- `revenue-goals-dashboard`: Add new business metrics section to the existing Goals tab

## Impact

- **Backend**: Contract model gets `deal_won_date` field + migration; HubSpot sync updated to populate it; new goal types in RevenueGoal; new GraphQL queries for won deal metrics
- **Frontend**: Goals dashboard extended with new business section; possibly revenue goals settings extended for new goal types
- **Data migration**: Backfill `deal_won_date` from HubSpot API for existing contracts with `hubspot_deal_id`
