## Tasks

### 1. Backend: Model changes

- [x] 1.1 Add `delivery_status` CharField (nullable, choices: `pending`/`delivered`) to `ContractItem`
- [x] 1.2 Add `delivered_at` DateField (nullable) to `ContractItem`
- [x] 1.3 Add `depends_on` self-referencing FK (nullable, `SET_NULL`, `related_name='dependent_items'`) to `ContractItem`
- [x] 1.4 Create migration

### 2. Backend: Billing logic

- [x] 2.1 In `Contract.get_billing_schedule()`, skip items with `delivery_status = 'pending'`
- [x] 2.2 In `Contract.get_billing_schedule()`, skip items whose `depends_on` target has `delivery_status = 'pending'`
- [x] 2.3 In `Contract.get_recognition_schedule()`, apply same skip logic for pending/blocked items

### 3. Backend: GraphQL schema

- [x] 3.1 Add `delivery_status`, `delivered_at`, `depends_on`, `dependent_items` fields to `ContractItemType` — update all 3 construction sites (items resolver, add_contract_item, update_contract_item)
- [x] 3.2 Add `delivery_tracking` boolean input to `add_contract_item` and `update_contract_item` mutations — when enabled, sets `delivery_status = 'pending'`
- [x] 3.3 Add `depends_on_item_id` input to `add_contract_item` and `update_contract_item` mutations — validates same-contract, no self-reference
- [x] 3.4 Add `mark_item_delivered(item_id, delivered_at)` mutation — sets `delivery_status = 'delivered'`, `delivered_at`, returns list of dependent items needing `billing_start_date`
- [x] 3.5 Add `revert_item_delivery(item_id)` mutation — sets `delivery_status = 'pending'`, clears `delivered_at`
- [x] 3.6 Add `deliverable_items(status, customer_id)` query for the projects overview — returns items with `delivery_status IS NOT NULL`, annotated with `dependent_items` count

### 4. Backend: Tests

- [x] 4.1 Test: item with `delivery_status = 'pending'` excluded from billing schedule
- [x] 4.2 Test: item with `delivery_status = 'delivered'` included in billing schedule
- [x] 4.3 Test: item depending on pending item excluded from billing schedule
- [x] 4.4 Test: item depending on delivered item included in billing schedule
- [x] 4.5 Test: `mark_item_delivered` mutation sets status and date, returns dependents
- [x] 4.6 Test: `revert_item_delivery` mutation clears status and date
- [x] 4.7 Test: dependency must be in same contract (rejected otherwise)
- [x] 4.8 Test: self-dependency rejected
- [x] 4.9 Test: deleting dependency target sets `depends_on = NULL` on dependents
- [x] 4.10 Test: `deliverable_items` query returns correct items with filters

### 5. Frontend: ContractDetail — dependency display

- [x] 5.1 Update contract detail items query to fetch `deliveryStatus`, `deliveredAt`, `dependsOn { id name }`, `dependentItems { id name }`
- [x] 5.2 Show delivery status badge on items (pending = amber, delivered = green) in the items table
- [x] 5.3 Show dependency indicator on items (e.g., "Depends on: Workshop Setup") in the items table
- [x] 5.4 Add "Mark as Delivered" action button on pending items — opens dialog with date picker (default today), on confirm calls `mark_item_delivered` mutation
- [x] 5.5 After marking delivered, show prompt to set `billing_start_date` for dependent items that have `billing_start_date = NULL`
- [x] 5.6 Add "Revert to Pending" action on delivered items

### 6. Frontend: ContractForm — dependency editing

- [x] 6.1 Add "Delivery Tracking" toggle to add/edit item modal — when enabled, sets `delivery_tracking = true`
- [x] 6.2 Add "Depends on" dropdown to add/edit item modal — lists other items in the same contract, sets `depends_on_item_id`

### 7. Frontend: Projects page

- [x] 7.1 Create `ProjectList.tsx` component with table listing deliverable items (product/description, customer, contract, status, delivered date, dependent items count)
- [x] 7.2 Add `DELIVERABLE_ITEMS_QUERY` and wire up to the component
- [x] 7.3 Add status filter (pending / delivered / all, default: pending) and customer filter
- [x] 7.4 Add "Mark as Delivered" action with delivery dialog (same as ContractDetail)
- [x] 7.5 Add contract name link navigating to `/contracts/:id`
- [x] 7.6 Add route `/projects` in `App.tsx`
- [x] 7.7 Add "Projects" nav link between "Contracts" and "Invoices" in navigation

### 8. Translations

- [x] 8.1 Add German and English translations for delivery status labels, dependency labels, projects page, dialogs, and navigation

### 9. Verification

- [x] 9.1 Run `make test-back` — all tests pass (600 passed, 4 skipped)
- [x] 9.2 Run `npx tsc --noEmit` — no type errors
