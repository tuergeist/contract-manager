## Context

Deliverable contract items (one-offs with delivery tracking) are currently excluded from revenue forecasts and billing schedules while their `delivery_status` is `pending`. This creates blind spots in financial projections — a contract with a large pending deliverable shows no forecast revenue for that item until it's marked delivered and given a billing start date.

The existing delivery tracking system on `ContractItem` uses `delivery_status` (null/pending/delivered) and `delivered_at`. The billing and recognition schedule methods in `Contract.get_billing_schedule()` and `Contract.get_recognition_schedule()` skip items where `delivery_status == "pending"` or where a dependency has `delivery_status == "pending"`.

## Goals / Non-Goals

**Goals:**
- Add an optional `estimated_delivery_date` field to contract items with delivery tracking
- Include pending items with ETAs in revenue forecasts and dashboard KPI projections
- Display and allow editing ETAs on the Projects page and contract detail
- Keep actual billing/invoicing behavior unchanged (only forecasts are affected)

**Non-Goals:**
- Automatic notifications when ETA is approaching or overdue
- ETA history tracking or audit logging of ETA changes
- Changing actual billing schedule behavior — pending items still won't generate invoices
- Gantt charts or timeline visualizations

## Decisions

### 1. Single nullable DateField on ContractItem

Add `estimated_delivery_date = models.DateField(null=True, blank=True)` to `ContractItem`. The field is only meaningful when `delivery_status = "pending"`. It gets cleared automatically when the item is delivered.

**Alternative considered**: Separate ETA model with history tracking. Rejected — unnecessary complexity for a simple projection date. If ETA history becomes needed later, audit log already captures field changes.

### 2. Forecast-only inclusion (no billing schedule changes)

Pending items with ETAs appear in forecast/recognition schedules for projection purposes but NOT in the actual billing schedule used for invoice generation. This is achieved by adding a `forecast_mode` parameter to the schedule methods.

**Approach**: Add an optional `include_eta_items=False` parameter to `get_billing_schedule()` and `get_recognition_schedule()`. When `True`, pending items with an ETA are included using the ETA as their projected billing start date. The invoice generation code continues to call these methods with the default `False`, so actual invoicing is unaffected.

**Alternative considered**: Separate forecast calculation. Rejected — duplicating the schedule logic would create drift. A single parameter keeps everything in sync.

### 3. Dependent items use dependency's ETA as projected start

When a recurring item depends on a pending deliverable that has an ETA, the recurring item's projected start in forecast mode is `max(item.billing_start_date, dependency.estimated_delivery_date)`. If the dependency has no ETA, the dependent item remains excluded.

### 4. Dashboard KPIs use forecast mode

`calculate_dashboard_kpis()` calls the schedule methods with `include_eta_items=True` for forecast KPIs (current year, next year). ARR calculation remains unchanged — ARR only counts actively billing items, not projections.

### 5. Inline ETA editing on Projects page

The Projects page (`DeliverableItemType`) gains an `estimated_delivery_date` field. The frontend shows a date picker inline on the ETA column for pending items. A dedicated lightweight mutation `set_deliverable_eta(item_id, date)` handles updates without going through the full `update_contract_item` flow.

**Alternative considered**: Reuse the existing `update_contract_item` mutation. Rejected — that mutation is heavyweight (handles product changes, price periods, amendments) and the Projects page doesn't have the full item context. A focused mutation is simpler and safer.

### 6. ETA in item edit modal

The existing Add/Update item modals gain an "Estimated Delivery Date" date picker, shown only when delivery tracking is enabled and the item is pending. The `AddContractItemInput` and `UpdateContractItemInput` types gain an optional `estimated_delivery_date` field.

## Risks / Trade-offs

- **Forecast accuracy depends on ETA quality** → Users set ETAs manually; stale ETAs produce misleading forecasts. Mitigation: ETAs are optional, and the Projects page makes them visible for review.
- **Schedule method complexity increases** → Adding `include_eta_items` parameter to schedule methods adds a code path. Mitigation: The parameter is a simple boolean guard on the existing pending-item skip logic; no structural change to the schedule algorithm.
- **ETA cleared on delivery could surprise users** → When marking delivered, the ETA disappears. Mitigation: ETA is a projection tool; once delivered, `delivered_at` replaces it. The value served its purpose.

## Open Questions

_(none)_
