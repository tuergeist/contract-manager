## Why

Contracts sometimes need to be reverted to draft after activation — for example when terms were entered incorrectly or activation was premature. Currently there is no way to undo an activation. Additionally, customers synced from HubSpot may appear multiple times (once per city/location), so contracts in draft need the ability to switch to the correct customer entity.

## What Changes

- Add a "Reset to Draft" action on active contracts that have no generated invoices. This reverts the status to `draft` and deletes all amendments created since activation.
- Add a "Change Customer" action on draft contracts, allowing the user to pick a different customer.
- Both actions are exposed as GraphQL mutations and as UI buttons on the contract detail page.

## Capabilities

### New Capabilities
- `contract-reset-to-draft`: Revert an active contract back to draft status, clearing amendments, when no invoices exist
- `contract-change-customer`: Reassign a draft contract to a different customer

### Modified Capabilities

## Impact

- Backend: new mutations in `apps/contracts/schema.py`, new service logic
- Models: no schema changes (uses existing `status`, `amendments`, `customer` fields)
- Frontend: new action buttons on contract detail page (Detail View 2), customer selector for change-customer
- Audit log: both actions should be logged
- Permissions: both actions require contract-edit permission
