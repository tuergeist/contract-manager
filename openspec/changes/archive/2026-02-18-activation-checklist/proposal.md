## Why

Contracts can be activated with incomplete data — missing PO numbers, NetSuite links, or Sales Order numbers. This causes downstream issues in invoicing and accounting. A configurable checklist that blocks activation until required fields are filled ensures data quality before a contract enters the billing pipeline.

## What Changes

- New tenant-level setting to configure which contract fields are required before activation (e.g., `po_number`, `netsuite_sales_order_number`, `netsuite_url`, `order_confirmation_number`)
- Settings UI to toggle which fields are mandatory for activation
- Backend validation in the `update_contract_status` mutation: when transitioning to `active`, check all configured required fields are non-empty
- Frontend: the activate confirmation dialog shows which fields are missing and prevents activation until they're filled
- Existing contracts already active are unaffected — the check only applies at activation time

## Capabilities

### New Capabilities
- `activation-checklist`: Configurable per-tenant checklist of required contract fields that must be filled before a contract can be activated

### Modified Capabilities

## Impact

- **Backend**: `contracts/schema.py` (status transition validation), `tenants/schema.py` (settings query/mutation)
- **Frontend**: `ContractDetail.tsx` or `ContractForm.tsx` (activate action), `Settings.tsx` (checklist configuration)
- **Model**: Uses existing `Tenant.settings` JSONField — no migration needed
- **Translations**: New strings for settings UI and validation messages (de + en)
