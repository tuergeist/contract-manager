## 1. Backend — Recognition Schedule Accepts Pre-loaded Items

- [x] 1.1 Add optional `items=None` parameter to `Contract.get_recognition_schedule()` in `apps/contracts/models.py`; when provided, skip the internal `self.items.select_related().prefetch_related().all()` call and use the passed-in items
- [x] 1.2 Verify existing callers (billing schedule, forecast) still work without passing `items` (backward compatible)

## 2. Backend — Optimize `calculate_dashboard_kpis()`

- [x] 2.1 Update the prefetch in `calculate_dashboard_kpis()` to include `items__product` alongside `items` and `items__price_periods`
- [x] 2.2 In the TCV/ARR loop, replace `item.get_price_at(today)` with `item.get_price_at_cached(today, list(item.price_periods.all()))` using prefetched data
- [x] 2.3 Replace the 2-3 separate `get_recognition_schedule()` calls per contract with a single call spanning `current_year_start` to `next_year_end`, passing pre-loaded items
- [x] 2.4 Split the single schedule's events into YTD, current year, and next year buckets by comparing each event's date against the boundary dates
- [x] 2.5 Run existing `test_dashboard_kpis.py` tests to confirm identical KPI values

## 3. Frontend — Remove Team Todos from Dashboard

- [x] 3.1 Remove `TEAM_TODOS_QUERY`, `teamTodosData`/`teamTodosLoading`/`refetchTeamTodos` state, `teamClosedDays` state, and the Team Todos UI section from `Dashboard.tsx`
- [x] 3.2 Change my todos section from `lg:grid-cols-2` grid to full-width single column
- [x] 3.3 Run `npx tsc --noEmit` to verify no type errors
