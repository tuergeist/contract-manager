## Why

Deliverable line items (one-offs with delivery tracking) are currently excluded from revenue forecasts and billing schedules while pending. This means contracts with large pending deliverables show artificially low forecasts. An estimated delivery date (ETA) per item would let the system project when pending items will be delivered and include them in revenue forecasts at the expected date, giving a more accurate financial picture.

## What Changes

- Contract items with delivery tracking gain an optional `estimated_delivery_date` (ETA) field
- Revenue forecasts include pending deliverables at their ETA when set, instead of excluding them entirely
- The Projects overview page displays the ETA for each pending item
- Users can set/update the ETA when editing items or from the Projects page
- Dashboard KPIs account for pending items with ETAs in their forecast calculations

## Capabilities

### New Capabilities
- `deliverable-eta`: ETA date field on deliverable contract items, integration into revenue forecasts, display on Projects page and contract detail

### Modified Capabilities
_(none — this extends existing delivery tracking behavior without changing existing spec requirements)_

## Impact

- **Backend models**: `ContractItem` gains `estimated_delivery_date` DateField; new migration
- **Billing/recognition logic**: `get_recognition_schedule()` and `get_billing_schedule()` need to consider pending items with ETAs for forecast purposes
- **Dashboard KPIs**: `calculate_dashboard_kpis()` must include pending items with ETAs in forecast totals
- **GraphQL schema**: New field on `ContractItemType` and item input types
- **Frontend**: ETA date picker in item edit modal, ETA column on Projects page, ETA display on contract detail items
