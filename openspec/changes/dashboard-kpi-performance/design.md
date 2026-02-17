## Context

The dashboard's `calculate_dashboard_kpis()` in `apps/contracts/schema.py` (line 811) is the primary bottleneck. It iterates all active contracts and for each one computes 2-3 recognition schedules via `get_recognition_schedule()`. Each schedule call re-queries items from the DB, generates date-based billing events, and calls `get_price_at()` which issues additional queries despite prefetching. The frontend also fires 3 parallel GraphQL queries (KPIs, my todos, team todos).

## Goals / Non-Goals

**Goals:**
- Reduce dashboard KPI query time from ~2-5s to <500ms
- Eliminate N+1 queries in the KPI computation loop
- Remove team todos from the dashboard to reduce query count and simplify the UI

**Non-Goals:**
- Introducing Redis/Celery caching for KPIs (can be added later if needed)
- Changing the recognition schedule algorithm itself
- Modifying the `myTodos` query or todo rendering

## Decisions

### 1. Single-pass recognition schedule per contract

**Decision**: Compute one `get_recognition_schedule()` call per contract spanning the full date range (Jan 1 current year → Dec 31 next year), then split the resulting events into YTD, current year, and next year buckets in Python.

**Rationale**: Currently 2-3 calls per contract produce overlapping date ranges (YTD is a subset of current year). A single call avoids redundant item iteration and date arithmetic. Splitting events by date in a dict comprehension is trivial.

**Alternative**: Cache individual schedule results — rejected because the overlap waste is the core issue, and caching adds complexity.

### 2. Pass pre-loaded items into `get_recognition_schedule()`

**Decision**: Add an optional `items` parameter to `get_recognition_schedule()`. When provided, skip the internal `self.items.select_related().prefetch_related().all()` query and use the passed-in queryset.

**Rationale**: The outer `calculate_dashboard_kpis()` already does `prefetch_related("items", "items__price_periods")`. The schedule method then re-queries the same data. Passing the already-loaded items eliminates N extra DB roundtrips (one per contract).

**Alternative**: Use `all()` on the prefetched manager (which hits the cache) — but the schedule method also adds `select_related("product")` which wouldn't be in the prefetch. So we add `"items__product"` to the outer prefetch and pass items directly.

### 3. Use `get_price_at_cached()` in the KPI TCV/ARR loop

**Decision**: In the TCV/ARR computation (lines 848-863), use `get_price_at_cached(today, item_price_periods)` instead of `get_price_at(today)`.

**Rationale**: `get_price_at()` calls `self.price_periods.filter(...)` which issues a new query, bypassing the prefetch cache. `get_price_at_cached()` accepts a pre-fetched list and does in-memory filtering. Items and price_periods are already prefetched by the outer query.

### 4. Remove team todos from dashboard

**Decision**: Remove the `TEAM_TODOS_QUERY`, its state, and its UI section from `Dashboard.tsx`. Make the my todos section full-width.

**Rationale**: Team todos duplicate what's on the dedicated `/todos` page. Removing the query reduces dashboard from 3 to 2 parallel GraphQL requests. The my todos section becomes more prominent with full width.

## Risks / Trade-offs

- **Behavioral equivalence**: The single-pass schedule must produce identical totals to the current separate calls. The existing test suite (`test_dashboard_kpis.py`) validates the final KPI values, so any regression will be caught.
- **`get_recognition_schedule` signature change**: Adding an optional `items` parameter is backward-compatible. All existing callers (billing schedule view, forecast page) continue working without changes.
- **Team todos removal is a UX change**: Users who relied on seeing team todos on the dashboard will need to visit `/todos`. This is acceptable since the todos page already exists and is in the sidebar.
