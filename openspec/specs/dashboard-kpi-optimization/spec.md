## Requirements

### Requirement: Single-pass recognition schedule for KPI computation
The `calculate_dashboard_kpis()` function SHALL compute at most one recognition schedule per contract, covering the full date range needed (current year start through next year end), and split results into YTD, current year, and next year buckets in memory.

#### Scenario: KPI totals match previous behavior
- **WHEN** the dashboard KPIs are computed for a tenant with active contracts
- **THEN** the returned values for `yearToDateRevenue`, `currentYearForecast`, and `nextYearForecast` SHALL be identical to the values produced by the previous multi-call approach

#### Scenario: Contracts without next-year applicability excluded from next year forecast
- **WHEN** a contract's end date is before January 1 of the next year
- **THEN** recognition events from that contract SHALL NOT be included in the `nextYearForecast` total

### Requirement: Pre-loaded items passed to recognition schedule
The `get_recognition_schedule()` method SHALL accept an optional `items` parameter. When provided, the method SHALL use the passed-in items instead of querying the database.

#### Scenario: Items parameter provided
- **WHEN** `get_recognition_schedule()` is called with a pre-loaded items queryset
- **THEN** the method SHALL NOT issue any additional database queries for items or their related objects

#### Scenario: Items parameter omitted
- **WHEN** `get_recognition_schedule()` is called without the `items` parameter
- **THEN** the method SHALL query items from the database as before (backward compatible)

### Requirement: Cached price lookups in KPI computation
The KPI computation loop SHALL use `get_price_at_cached()` with pre-fetched price period lists instead of `get_price_at()` to avoid per-item database queries.

#### Scenario: Price periods prefetched and reused
- **WHEN** the KPI loop iterates over contract items for TCV and ARR calculations
- **THEN** price lookups SHALL use in-memory price period data from the prefetch, issuing zero additional queries per item

### Requirement: Prefetch includes product relation
The outer contract query in `calculate_dashboard_kpis()` SHALL include `items__product` in its prefetch to ensure recognition schedule generation does not trigger additional product queries.

#### Scenario: No N+1 product queries
- **WHEN** the KPI function iterates contracts and computes schedules
- **THEN** no additional database queries SHALL be issued for `ContractItem.product` lookups
