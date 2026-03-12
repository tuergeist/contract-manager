## 1. Backend Model & Migration

- [x] 1.1 Add `estimated_delivery_date = DateField(null=True, blank=True)` to `ContractItem` model
- [x] 1.2 Create and run migration
- [x] 1.3 Clear `estimated_delivery_date` in `deliver_item` mutation when marking item as delivered
- [x] 1.4 Clear `estimated_delivery_date` when delivery tracking is disabled on an item

## 2. GraphQL Schema

- [x] 2.1 Add `estimated_delivery_date` field to `ContractItemType` (and all 3 manual construction sites)
- [x] 2.2 Add `estimated_delivery_date` to `AddContractItemInput` and wire into `add_contract_item` mutation
- [x] 2.3 Add `estimated_delivery_date` to `UpdateContractItemInput` and wire into `update_contract_item` mutation
- [x] 2.4 Add `estimated_delivery_date` to `DeliverableItemType` for Projects page query
- [x] 2.5 Add `set_deliverable_eta(item_id, date)` mutation for lightweight ETA updates from Projects page

## 3. Forecast Logic

- [x] 3.1 Add `include_eta_items=False` parameter to `Contract.get_billing_schedule()`; when True, include pending items with ETA using ETA as projected billing date
- [x] 3.2 Add `include_eta_items=False` parameter to `Contract.get_recognition_schedule()`; same logic
- [x] 3.3 Handle dependent items in forecast mode: use `max(billing_start_date, dependency.estimated_delivery_date)` as projected start
- [x] 3.4 Update `calculate_dashboard_kpis()` to call schedule methods with `include_eta_items=True` for forecast KPIs (current year, next year); leave ARR unchanged

## 4. Frontend — Item Modals

- [x] 4.1 Add ETA date picker to AddItemModal (visible when delivery tracking is checked)
- [x] 4.2 Add ETA date picker to EditItemModal (visible when item is pending deliverable)
- [x] 4.3 Add `estimatedDeliveryDate` to item GraphQL fragments/queries

## 5. Frontend — Contract Detail

- [x] 5.1 Display ETA on pending deliverable item rows (e.g. "ETA: 2026-05-01" near delivery status badge)

## 6. Frontend — Projects Page

- [x] 6.1 Add ETA column to Projects table
- [x] 6.2 Implement inline date picker for setting/clearing ETA on pending items
- [x] 6.3 Wire inline editor to `set_deliverable_eta` mutation
- [x] 6.4 Show `delivered_at` in the ETA column for delivered items

## 7. Translations

- [x] 7.1 Add EN/DE translations for ETA-related labels (field label, column header, placeholder)

## 8. Tests

- [x] 8.1 Test: ETA field saved/cleared on ContractItem model
- [x] 8.2 Test: ETA cleared automatically on delivery
- [x] 8.3 Test: Forecast includes pending item with ETA, excludes without
- [x] 8.4 Test: Dependent item included in forecast when dependency has ETA
- [x] 8.5 Test: Dashboard KPIs include ETA items in forecast, exclude from ARR
- [x] 8.6 Test: `set_deliverable_eta` mutation validates item has delivery tracking
