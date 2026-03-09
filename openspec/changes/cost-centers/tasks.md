## Tasks

### 1. Backend: Cost center model
- [ ] 1.1 Create `CostCenter` model: tenant FK, code (CharField, max 20), name (CharField), is_active (bool, default True)
- [ ] 1.2 Add migration for `CostCenter`
- [ ] 1.3 Add unique constraint on (tenant, code)

### 2. Backend: Counterparty default cost center
- [ ] 2.1 Add `default_cost_center` FK (nullable) to `Counterparty` model
- [ ] 2.2 Add migration

### 3. Backend: Cost center on transactions and incoming invoices
- [ ] 3.1 Add `cost_center` FK (nullable) to `BankTransaction` model
- [ ] 3.2 Add `cost_center` FK (nullable) to `IncomingInvoice` model (if not already added in incoming-invoice-import)
- [ ] 3.3 Add migrations
- [ ] 3.4 When creating/importing transactions: auto-assign counterparty's default cost center if set

### 4. Backend: Cost center CRUD API
- [ ] 4.1 Add `CostCenterType` Strawberry type
- [ ] 4.2 Add `costCenters` query (list all for tenant, with optional is_active filter)
- [ ] 4.3 Add `createCostCenter` mutation (requires `settings.write`)
- [ ] 4.4 Add `updateCostCenter` mutation
- [ ] 4.5 Add `deleteCostCenter` mutation (warn if in use, clear assignments on confirm)

### 5. Backend: Assign cost center mutations
- [ ] 5.1 Add `cost_center_id` field to `updateCounterparty` mutation (set default KSt)
- [ ] 5.2 Add `assignTransactionCostCenter(transaction_id, cost_center_id)` mutation
- [ ] 5.3 Add `cost_center` field to `updateIncomingInvoice` mutation
- [ ] 5.4 Expose `costCenter` on `BankTransactionType` and `CounterpartySummaryType`

### 6. Frontend: Cost center settings page
- [ ] 6.1 Add "Cost Centers" section to Settings page (or dedicated sub-page)
- [ ] 6.2 Table with code, name, active status
- [ ] 6.3 Create/edit/delete cost center forms
- [ ] 6.4 Show usage count (how many counterparties/transactions use this KSt)

### 7. Frontend: Default cost center on counterparty
- [ ] 7.1 Add cost center dropdown to counterparty edit form/detail page
- [ ] 7.2 Show default cost center in counterparty list (optional column)

### 8. Frontend: Cost center on transactions
- [ ] 8.1 Show cost center column in bank transactions list
- [ ] 8.2 Add cost center selector on transaction detail/match sheet
- [ ] 8.3 Add cost center filter to transactions list

### 9. i18n
- [ ] 9.1 Add translation keys for cost center CRUD, assignment, filters to `en.json` and `de.json`

### 10. Tests
- [ ] 10.1 Test cost center CRUD: create, duplicate code rejected, edit, delete, delete-with-assignments
- [ ] 10.2 Test default cost center on counterparty: set, change, clear
- [ ] 10.3 Test auto-assignment on transaction import
- [ ] 10.4 Test manual assignment on transaction and incoming invoice
- [ ] 10.5 Test tenant isolation
