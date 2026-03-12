## Tasks

### 1. Backend: Split rule model
- [x]1.1 Create `CostCenterSplitRule` model: tenant FK, counterparty FK (nullable), booking_text_pattern (CharField, nullable), priority (int, default 0), is_active (bool)
- [x]1.2 Create `CostCenterSplitAllocation` model: rule FK, cost_center FK, percentage (Decimal, nullable), fixed_amount (Decimal, nullable)
- [x]1.3 Add migrations
- [x]1.4 Add constraint: either counterparty or booking_text_pattern must be set (not both null)
- [x]1.5 Add validation: allocations for a rule must total 100% (for percentage rules) or have exactly one "remainder" entry (for fixed-amount rules)

### 2. Backend: Split execution model
- [x]2.1 Create `TransactionCostCenterSplit` model: transaction FK, cost_center FK, amount (Decimal), is_manual (bool, default False), rule FK (nullable)
- [x]2.2 Create `IncomingInvoiceCostCenterSplit` model: incoming_invoice FK, cost_center FK, amount (Decimal), is_manual (bool), rule FK (nullable)
- [x]2.3 Add migrations

### 3. Backend: Split rule CRUD API
- [x]3.1 Add `CostCenterSplitRuleType` and `CostCenterSplitAllocationType` Strawberry types
- [x]3.2 Add `costCenterSplitRules` query (list, filter by counterparty)
- [x]3.3 Add `createCostCenterSplitRule` mutation — validate allocations total 100%
- [x]3.4 Add `updateCostCenterSplitRule` mutation
- [x]3.5 Add `deleteCostCenterSplitRule` mutation

### 4. Backend: Auto-apply split rules
- [x]4.1 Create `CostCenterSplitService.apply_rule(transaction)` — find matching rule (counterparty first, then pattern), create split allocations
- [x]4.2 Hook into transaction import: after cost center assignment, check for split rules
- [x]4.3 Hook into incoming invoice import: same logic
- [x]4.4 Rule priority: counterparty-specific > booking text pattern > default cost center (no split)

### 5. Backend: Manual split API
- [x]5.1 Add `splitTransactionCostCenters(transaction_id, splits: [{cost_center_id, amount}])` mutation
- [x]5.2 Validate: split amounts must equal transaction amount
- [x]5.3 Mark splits as `is_manual=True`, remove any auto-applied splits
- [x]5.4 Add same mutation for incoming invoices

### 6. Backend: Cost center report query
- [x]6.1 Add `costCenterReport(date_from, date_to)` query — aggregate splits by cost center
- [x]6.2 Include "Unassigned" bucket for transactions/invoices without any cost center or split
- [x]6.3 Return per cost center: total amount, transaction count, split count

### 7. Frontend: Split rule editor
- [x]7.1 Add "Split Rules" page/section (under Settings or Banking)
- [x]7.2 List rules grouped by counterparty / pattern
- [x]7.3 Create rule form: select counterparty or enter pattern, add cost center allocations with percentage/amount
- [x]7.4 Edit/delete rules
- [x]7.5 Validation feedback (must total 100%)

### 8. Frontend: Manual split on transaction
- [x]8.1 Add "Split" action on transaction detail/match sheet
- [x]8.2 Split editor: add rows with cost center + amount, show remaining
- [x]8.3 Show existing splits on transaction detail (auto or manual)

### 9. Frontend: Cost center report
- [x]9.1 Add report page with date range selector
- [x]9.2 Table/chart showing costs per cost center
- [x]9.3 Drill-down: click cost center to see individual transactions

### 10. i18n
- [x]10.1 Add translation keys for split rules, manual split, report to `en.json` and `de.json`

### 11. Tests
- [x]11.1 Test split rule CRUD: create, validation (must total 100%), edit, delete
- [x]11.2 Test auto-apply: counterparty rule, pattern rule, priority order
- [x]11.3 Test manual split: valid split, amount mismatch rejected, overrides auto
- [x]11.4 Test cost center report: aggregation, unassigned bucket, date range filter
- [x]11.5 Test tenant isolation
