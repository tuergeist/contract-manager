## Why

Contracts often run for multiple years and prices need periodic adjustments (e.g., annual inflation, cost increases). Currently, raising prices across all items of a contract requires manually editing each item one by one — tedious and error-prone, especially for contracts with many line items. A bulk "raise by X%" action is needed so users can apply a percentage increase to all recurring items in one step, with a chosen effective date.

## What Changes

- New "Price Increase" button on the contract detail page (works on any status including active contracts)
- Modal dialog with:
  - Percentage input (float, e.g. 3.5%)
  - Effective date picker (defaults to next January 1)
  - Mode choice: **direct increase** (update `unit_price` on each item) vs. **period-specific price** (create a `ContractItemPrice` entry per item with the raised amount and `valid_from` = effective date)
- Backend mutation that applies the increase to all recurring items of the contract
- Amendment tracking: for non-draft contracts, the change is recorded as an amendment

## Capabilities

### New Capabilities
- `bulk-price-increase`: Bulk percentage-based price increase across all recurring items of a contract, with direct vs. period-specific mode

### Modified Capabilities

## Impact

- **Backend**: New mutation in `contracts/schema.py`, operates on `ContractItem` and `ContractItemPrice` models
- **Frontend**: New modal + button in `ContractDetail.tsx`, new GraphQL mutation
- **Translations**: New strings for modal labels, mode descriptions, success/error messages (de + en)
- **Audit**: Amendment auto-tracked for non-draft contracts via existing mechanism
