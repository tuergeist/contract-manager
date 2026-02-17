## Why

Customers with multiple contracts need a way to organize them logically. Currently, contracts are displayed as a flat list which becomes unwieldy when a customer has many contracts across different projects, departments, or product lines. Contract groups allow bundling related contracts together for better organization and overview.

## What Changes

- Add a new `ContractGroup` model scoped to a customer with a name field
- Contracts can optionally belong to one group (many-to-one relationship)
- Customer detail page contract list shows group membership for each contract
- Group assignment is editable inline from the customer contracts list
- Contract edit page (`/contracts/:id/edit`) overview section includes group selection dropdown
- Groups are managed per-customer (no global groups)

## Capabilities

### New Capabilities
- `contract-groups`: Contract grouping model and CRUD operations (create, rename, delete groups within a customer). Assignment of contracts to groups. GraphQL queries and mutations for group management.

### Modified Capabilities
<!-- No existing spec-level requirements are changing -->

## Impact

- **Backend**: New `ContractGroup` model in `apps/contracts/models.py`, new GraphQL types and mutations in `apps/contracts/schema.py`
- **Frontend**:
  - `CustomerDetail.tsx` - Add group column/badge to contracts table, inline group editing
  - `ContractForm.tsx` - Add group selector in overview section
- **Database**: New table `contracts_contractgroup`, new foreign key on `contracts_contract`
- **Permissions**: Uses existing `contracts.write` permission for group management
