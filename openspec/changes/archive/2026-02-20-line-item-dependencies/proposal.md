## Why

Contracts often contain line items that depend on each other — a recurring SaaS license cannot start billing until a one-off custom development or workshop is completed. Today, there is no way to model this relationship: users must manually track which items are pending, remember to update billing dates after delivery, and have no overview of outstanding development work across contracts.

## What Changes

- Contract items can be linked via a dependency: a recurring item can depend on a one-off item (or another item), meaning its billing is blocked until the dependency is fulfilled
- One-off items gain a "delivery status" (pending / delivered) — billing only happens once marked as delivered
- Dependent recurring items have no billing_start_date initially; it is set automatically (or manually) when the dependency is fulfilled
- A new "Projects" page provides an overview of all pending deliverables (one-off items with delivery tracking) across contracts, with status, customer, and contract context
- Existing billing/invoice logic skips items whose dependencies are not yet fulfilled

## Capabilities

### New Capabilities
- `item-dependencies`: Core dependency model — linking items to each other, delivery status tracking on items, blocking billing until dependencies are fulfilled, and automatic date propagation when dependencies are completed
- `projects-overview`: Dedicated page listing all deliverable items (one-offs with delivery tracking) across contracts, with filtering by status, customer, and assignment

### Modified Capabilities
_(none — existing specs are not affected at the requirement level)_

## Impact

- **Backend models**: `ContractItem` gains dependency FK and delivery status fields; new migration
- **Billing logic**: `get_billing_schedule()` and invoice generation must skip blocked/undelivered items
- **GraphQL schema**: New fields on `ContractItemType`, new queries for projects overview
- **Frontend**: New "Projects" route/page, updates to ContractDetail item display (dependency indicators, delivery actions), ContractForm item editing (dependency picker)
- **Revenue forecast**: Must account for blocked items (excluded until delivered)
