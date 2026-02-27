## Context

The system already tracks contracts with line items, products, and recognition schedules. Dashboard KPIs compute ARR, YTD revenue, and year forecasts across all revenue. However, there's no way to categorize revenue into business streams or track it against goals.

Currently:
- Products have `type` (subscription/one_off) and `category` (free-form FK) but no revenue stream classification
- Contract line items optionally link to a product; items without a product default to "Discount" naming
- Discounts are represented as line items with negative `unit_price` and no product
- The `calculate_dashboard_kpis()` function already iterates all active contracts and their items
- Revenue forecast (`revenue_forecast` query) computes per-contract monthly recognition
- Settings has a tabbed layout with General > Contracts/Help Videos/Performance sub-tabs

## Goals / Non-Goals

**Goals:**
- Classify all revenue into three streams: Advanced Development, Training + Implementation, Recurring
- Products carry a `revenue_type` that auto-classifies their line items
- Line items without a product must have `revenue_type` set manually
- Define yearly targets per revenue stream
- Show progress (YTD actuals + forecast) against yearly goals

**Non-Goals:**
- Per-customer or per-contract goal tracking (goals are company-wide per stream)
- Historical goal editing / audit trail for goal changes
- Quarterly or monthly goal breakdowns (yearly only)
- Changing how the recognition schedule itself works

## Decisions

### D1: Revenue type as a TextChoices field on both Product and ContractItem

Add `revenue_type` to both `Product` and `ContractItem` models as a `CharField` with `TextChoices`:
- `advanced_development` — "Advanced Development"
- `training_implementation` — "Training + Implementation"
- `recurring` — "Recurring Revenue"

**On Product**: Required. Determines the default for line items using that product.
**On ContractItem**: Nullable. When null, inherits from the linked product. When no product is linked, it becomes required.

**Why not a separate model/table?** These three categories are fixed business concepts, not user-configurable. TextChoices keeps it simple and avoids join overhead in the hot KPI calculation path.

**Alternative considered**: Using the existing `ProductCategory` model — rejected because categories are tenant-configurable free-form names, not the fixed revenue classification we need.

### D2: Inheritance logic for ContractItem revenue type

Resolution order:
1. If `ContractItem.revenue_type` is set → use it (explicit override)
2. If `ContractItem.product` exists → use `product.revenue_type`
3. If neither → validation error (should not happen if form enforces it)

This is implemented as a `get_effective_revenue_type()` method on `ContractItem`. The frontend form enforces that items without a product must select a revenue type.

### D3: RevenueGoal model in the contracts app

```
RevenueGoal(TenantModel):
    year: IntegerField
    revenue_type: CharField(choices=RevenueType)
    target_amount: DecimalField(max_digits=12, decimal_places=2)
    unique_together: [tenant, year, revenue_type]
```

Placed in the `contracts` app since it's tightly coupled to contract revenue calculations.

**Why not a separate app?** It's a single model with 3 fields. Keeping it in contracts avoids app proliferation and keeps it near the KPI/forecast code.

### D4: Goals settings UI in General > Revenue Goals sub-tab

Add a "Revenue Goals" sub-tab to Settings > General (alongside Contracts, Help Videos, Performance).

The UI shows a year selector and a simple table/form:
| Revenue Stream | Target (EUR) |
|---|---|
| Advanced Development | [input] |
| Training + Implementation | [input] |
| Recurring Revenue | [input] |

Save creates/updates `RevenueGoal` records for the selected year.

**Why Settings > General?** Revenue goals are a company-wide configuration, not specific to invoices, integrations, or team management.

### D5: Goals progress as a new tab on the Forecasts page

Add a "Goals" tab to the existing Forecasts page (`/forecasts?tab=goals`), alongside Revenue and Liquidity.

The Goals tab shows per-stream:
- Yearly target (from `RevenueGoal`)
- YTD actuals (recognized revenue Jan 1 → today, classified by stream)
- Full-year forecast (recognized revenue Jan 1 → Dec 31, classified by stream)
- Progress bar (forecast / target as %)

This reuses the existing recognition schedule logic, splitting results by `get_effective_revenue_type()`.

**Why the Forecasts page?** It's the natural home for forward-looking revenue data. Goals vs. actuals is a forecast concern.

**Alternative considered**: A standalone Goals page — rejected because it duplicates forecast infrastructure and fragments the revenue analysis experience.

### D6: Data migration strategy

Migration for existing data:
- Products with `type=subscription` → `revenue_type=recurring`
- Products with `type=one_off` → `revenue_type=None` (leave blank, require manual classification)
- ContractItem.revenue_type defaults to `None` (inherits from product)

One-off products need manual classification because we can't distinguish Advanced Development from Training + Implementation automatically. A Django management command or admin page can help with bulk classification.

### D7: GraphQL API additions

New queries:
- `revenueGoals(year: Int!): [RevenueGoalType]` — get goals for a year
- Extend `dashboardKpis` or add `revenueByStream(year: Int!)` — YTD and forecast broken down by stream

New mutations:
- `setRevenueGoal(year: Int!, revenueType: String!, targetAmount: Decimal!): RevenueGoalResult` — upsert a goal

Product and ContractItem types gain a `revenue_type` field. ContractItem also gets `effective_revenue_type` (resolved).

## Risks / Trade-offs

**Performance of per-stream KPI calculation** → The existing `calculate_dashboard_kpis` already iterates all items. Grouping by revenue type adds minimal overhead (a dict accumulator per stream). No additional queries needed.

**One-off product classification burden** → Existing one-off products won't have a revenue type and need manual assignment. Mitigation: the product list can filter by "unclassified" to make this easy, and GraphQL validation can warn but not block.

**ContractItem without product and without revenue_type** → Historical items may lack both. Mitigation: migration sets these to null; the goals dashboard groups unclassified items under an "Unclassified" bucket and shows a warning. New items are validated.

**Revenue type on discounts** → Discounts (negative-price items without a product) must be attributed to a stream. The frontend enforces revenue_type selection when adding/editing such items. Existing discounts without classification appear as "Unclassified" until manually fixed.
