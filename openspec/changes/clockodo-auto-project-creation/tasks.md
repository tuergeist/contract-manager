## 1. Backend: Clockodo Write API

- [ ] 1.1 Add `_post(endpoint, data)` method to `ClockodoProvider` with retry/rate-limit pattern
- [ ] 1.2 Add `create_customer(name: str) -> str` — POST /customers, returns Clockodo customer ID
- [ ] 1.3 Add `create_project(customer_id: str, name: str) -> str` — POST /projects, returns Clockodo project ID
- [ ] 1.4 Add `get_customer_projects(customer_id: str) -> list[TimeTrackingProject]` — GET /projects filtered by customer

## 2. Backend: Customer Linking Model

- [ ] 2.1 Add `clockodo_customer_id` CharField (nullable) to `Customer` model
- [ ] 2.2 Create migration
- [ ] 2.3 Add `linkCustomerToClockodo(customerId, clockodoCustomerId)` mutation
- [ ] 2.4 Add `unlinkCustomerFromClockodo(customerId)` mutation
- [ ] 2.5 Add `createClockodoCustomer(customerId)` mutation — creates Clockodo customer from CM customer name, stores mapping
- [ ] 2.6 Add `clockodoCustomerId` and `clockodoCustomerName` fields to `CustomerType`

## 3. Backend: Naming Templates

- [ ] 3.1 Add `maintenance_project_template` and `oneoff_project_template` to tenant time_tracking_config defaults
- [ ] 3.2 Add `saveTimeTrackingProjectTemplates(maintenanceTemplate, oneoffTemplate)` mutation
- [ ] 3.3 Add template rendering helper with placeholder substitution (`{customer_name}`, `{contract_name}`, `{item_name}`, `{year}`)

## 4. Backend: Activation Preview & Provisioning

- [ ] 4.1 Add `previewContractActivation(contractId)` query — returns: `customerLinked`, `maintenanceProjectExists`, `maintenanceProjectName`, `oneOffItems[]`, `clockodoConfigured`
- [ ] 4.2 Add `provisionClockodoProjects(contractId, createMaintenance, oneOffStrategy, selectedOneOffItemIds)` mutation — creates projects, mappings
- [ ] 4.3 Implement maintenance project lookup: find existing Clockodo project matching template pattern for linked customer
- [ ] 4.4 Implement one-off project creation: combined (one project for all one-offs) or per-item
- [ ] 4.5 Auto-create `TimeTrackingProjectMapping` records with `link_source="auto"` for each created/linked project

## 5. Backend: Bulk Customer Linking

- [ ] 5.1 Add `autoMatchClockodoCustomers` query — fetches all Clockodo customers, matches against CM customers by name, returns proposed pairs with match confidence
- [ ] 5.2 Add `bulkLinkClockodoCustomers(mappings: [{customerId, clockodoCustomerId}])` mutation

## 6. Backend: Tests

- [ ] 6.1 Test create_customer and create_project API calls (mocked)
- [ ] 6.2 Test customer linking/unlinking mutations
- [ ] 6.3 Test previewContractActivation with various contract configurations
- [ ] 6.4 Test provisionClockodoProjects — maintenance project creation, one-off strategies
- [ ] 6.5 Test auto-match algorithm
- [ ] 6.6 Test error handling when Clockodo API fails during provisioning

## 7. Frontend: Customer Linking UI

- [ ] 7.1 Add "Clockodo" section to customer detail page — shows linked Clockodo customer or linking options
- [ ] 7.2 Add searchable Clockodo customer dropdown (fetches via existing project list endpoint customers)
- [ ] 7.3 Add "Create in Clockodo" button when no match found
- [ ] 7.4 Add bulk linking view in settings (under Integrations > Clockodo)

## 8. Frontend: Activation Dialog

- [ ] 8.1 Create `ClockodoActivationDialog.tsx` — shown before contract activation when Clockodo is configured
- [ ] 8.2 Show maintenance project status (will create / already exists / customer not linked)
- [ ] 8.3 Show one-off items with strategy toggle (combined / per-item)
- [ ] 8.4 Add "Skip" and "Create & Activate" buttons
- [ ] 8.5 Integrate into contract status change flow (call preview → show dialog → provision → activate)

## 9. Frontend: Naming Template Config

- [ ] 9.1 Add naming template fields to time tracking settings (IntegrationSettingsTabs or dedicated sub-tab)
- [ ] 9.2 Show live preview of template with example data

## 10. Frontend: i18n

- [ ] 10.1 Add EN translation keys for all new UI strings
- [ ] 10.2 Add DE translation keys for the same
