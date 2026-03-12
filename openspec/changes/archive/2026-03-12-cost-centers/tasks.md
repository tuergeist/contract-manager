## Tasks

### 0. Backend: Permissions
- [x] 0.1 Add `cost_centers` to `PERMISSION_REGISTRY` with actions `["read", "write", "config"]`
- [x]0.2 Add `cost_centers.read` and `cost_centers.write` to Manager default role
- [x]0.3 Add `cost_centers.read` to Viewer default role
- [x]0.4 Use `require_perm(info, "cost_centers", "config")` for cost center CRUD mutations
- [x]0.5 Use `require_perm(info, "cost_centers", "read")` for list queries
- [x]0.6 Use `require_perm(info, "cost_centers", "write")` for assignment mutations

### 1. Backend: Cost center model
- [x]1.1 Create `CostCenter` model: tenant FK, code (CharField, max 20), name (CharField), is_active (bool, default True)
- [x]1.2 Add migration for `CostCenter`
- [x]1.3 Add unique constraint on (tenant, code)

### 2. Backend: Counterparty default cost center
- [x]2.1 Add `default_cost_center` FK (nullable) to `Counterparty` model
- [x]2.2 Add migration

### 3. Backend: Cost center on transactions and incoming invoices
- [x]3.1 Add `cost_center` FK (nullable) to `BankTransaction` model
- [x]3.2 Add `cost_center` FK (nullable) to `IncomingInvoice` model (if not already added in incoming-invoice-import)
- [x]3.3 Add migrations
- [x]3.4 When creating/importing transactions: auto-assign counterparty's default cost center if set

### 4. Backend: Cost center CRUD API
- [x]4.1 Add `CostCenterType` Strawberry type
- [x]4.2 Add `costCenters` query (list all for tenant, with optional is_active filter)
- [x]4.3 Add `createCostCenter` mutation (requires `settings.write`)
- [x]4.4 Add `updateCostCenter` mutation
- [x]4.5 Add `deleteCostCenter` mutation (warn if in use, clear assignments on confirm)

### 5. Backend: Assign cost center mutations
- [x]5.1 Add `cost_center_id` field to `updateCounterparty` mutation (set default KSt)
- [x]5.2 Add `assignTransactionCostCenter(transaction_id, cost_center_id)` mutation
- [x]5.3 Add `cost_center` field to `updateIncomingInvoice` mutation
- [x]5.4 Expose `costCenter` on `BankTransactionType` and `CounterpartySummaryType`

### 6. Frontend: Cost center settings page
- [x]6.1 Add "Cost Centers" section to Settings page (or dedicated sub-page)
- [x]6.2 Table with code, name, active status
- [x]6.3 Create/edit/delete cost center forms
- [x]6.4 Show usage count (how many counterparties/transactions use this KSt)

### 7. Frontend: Default cost center on counterparty
- [x]7.1 Add cost center dropdown to counterparty edit form/detail page
- [x]7.2 Show default cost center in counterparty list (optional column)

### 8. Frontend: Cost center on transactions
- [x]8.1 Show cost center column in bank transactions list
- [x]8.2 Add cost center selector on transaction detail/match sheet
- [x]8.3 Add cost center filter to transactions list

### 9. i18n
- [x]9.1 Add translation keys for cost center CRUD, assignment, filters to `en.json` and `de.json`

### 10. Tests
- [x]10.1 Test cost center CRUD: create, duplicate code rejected, edit, delete, delete-with-assignments
- [x]10.2 Test default cost center on counterparty: set, change, clear
- [x]10.3 Test auto-assignment on transaction import
- [x]10.4 Test manual assignment on transaction and incoming invoice
- [x]10.5 Test tenant isolation
- [x]10.6 Test permissions: read-only sees KSt but can't assign, write can assign, config required for CRUD
