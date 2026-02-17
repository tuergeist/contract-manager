## Context

The contract manager currently displays contracts as a flat list per customer. As customers accumulate contracts (renewals, different product lines, projects), this becomes hard to navigate. Users need a lightweight way to organize contracts without complex hierarchies.

Current state:
- Contracts belong to a Customer (many-to-one)
- Customer detail page shows contracts in a table
- Contract edit page has an "Overview" section with basic metadata

## Goals / Non-Goals

**Goals:**
- Allow grouping contracts within a customer for organizational purposes
- Simple group model: just a name, scoped to customer
- Easy group assignment from both customer view and contract edit
- Non-destructive: ungrouped contracts continue to work normally

**Non-Goals:**
- Nested groups or hierarchies
- Cross-customer groups
- Group-level permissions or access control
- Group-level reporting or aggregations (future enhancement)
- Automatic grouping based on contract properties

## Decisions

### 1. Group scoped to Customer
**Decision**: ContractGroup belongs to a Customer, not Tenant-global.

**Rationale**: Groups are for organizing a specific customer's contracts. Different customers have different organizational needs. This matches the mental model of "this customer's contracts are organized into these groups."

**Alternative considered**: Tenant-wide groups - rejected because group names like "Maintenance" would collide across customers.

### 2. Optional group membership
**Decision**: Contract.group is a nullable ForeignKey.

**Rationale**: Existing contracts don't need groups. Users can gradually adopt grouping without migration hassle. A contract without a group is simply "ungrouped."

### 3. Inline editing in customer contracts list
**Decision**: Group assignment editable directly in the contracts table via dropdown/popover.

**Rationale**: Quick workflow - user sees contracts, can immediately organize them. No need to open each contract individually.

**Alternative considered**: Only edit via contract form - rejected as too slow for bulk organization.

### 4. Group CRUD via GraphQL mutations
**Decision**: Dedicated mutations for createContractGroup, updateContractGroup, deleteContractGroup.

**Rationale**: Standard pattern in codebase. Allows permission checks and audit logging.

### 5. Delete behavior
**Decision**: Deleting a group sets contract.group to null (SET_NULL), doesn't delete contracts.

**Rationale**: Groups are organizational metadata. Deleting a group shouldn't affect the contracts themselves.

## Risks / Trade-offs

- **[Risk] Orphaned groups** → Allow deletion only, no automatic cleanup. Users manage their own groups.
- **[Risk] Many groups per customer** → No limit for now. If needed, add pagination to group selectors.
- **[Trade-off] Inline editing complexity** → Adds UI complexity to customer detail page, but worth it for UX.

## Data Model

```
ContractGroup
├── id (PK)
├── tenant (FK → Tenant)
├── customer (FK → Customer)
├── name (CharField, max 100)
├── created_at, updated_at

Contract (existing)
├── group (FK → ContractGroup, nullable, on_delete=SET_NULL)
```
