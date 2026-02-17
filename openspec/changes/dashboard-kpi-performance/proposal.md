## Why

The dashboard loads slowly because `calculate_dashboard_kpis()` computes recognition schedules 2-3 times per active contract, each schedule iterates all items with date arithmetic, and `get_price_at()` bypasses prefetched data causing N+1 queries. Additionally, the team todos section adds a third GraphQL query and is not useful on the dashboard — it duplicates content already available on the dedicated Todos page.

## What Changes

- Optimize `calculate_dashboard_kpis()` to compute one recognition schedule per contract (full date range) and split totals in Python, instead of 2-3 separate schedule calls
- Use `get_price_at_cached()` instead of `get_price_at()` in the KPI loop to avoid N+1 price_period queries
- Remove the redundant `select_related`/`prefetch_related` inside `get_recognition_schedule()` when items are already prefetched (accept optional pre-loaded items)
- Remove the team todos section and its `TEAM_TODOS_QUERY` from the dashboard, reducing frontend queries from 3 to 2

## Capabilities

### New Capabilities
- `dashboard-kpi-optimization`: Backend KPI computation performance improvements — fewer DB queries, single-pass schedule computation, cached price lookups
- `dashboard-layout-cleanup`: Remove team todos section from the dashboard and make my todos full-width

### Modified Capabilities
_(none)_

## Impact

- **Backend**: `apps/contracts/schema.py` (`calculate_dashboard_kpis`), `apps/contracts/models.py` (`get_recognition_schedule` signature change to accept pre-loaded items)
- **Frontend**: `features/dashboard/Dashboard.tsx` — remove team todos query, state, and UI section; make my todos full-width
- **No API changes**: The `dashboardKpis` GraphQL query returns the same shape, just faster
- **No migration needed**
