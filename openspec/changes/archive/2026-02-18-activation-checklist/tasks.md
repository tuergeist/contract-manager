## Tasks

### 1. Backend: GraphQL schema for settings

- [x] 1.1 Add `activation_required_fields: List[str]` to `HubSpotSettingsType` (or a new settings type) in `tenants/schema.py` — reads from `tenant.settings.get("activation_required_fields", [])`
- [x] 1.2 Add `set_activation_required_fields(fields: List[str])` mutation in `tenants/schema.py` — validates field names against whitelist (`po_number`, `order_confirmation_number`, `netsuite_sales_order_number`, `netsuite_contract_number`, `netsuite_url`), stores in `tenant.settings["activation_required_fields"]`
- [x] 1.3 Expose available checkable fields as a query/constant so the frontend knows which fields can be configured

### 2. Backend: Activation validation

- [x] 2.1 In `update_contract_status` mutation in `contracts/schema.py`, add validation when `new_status == ACTIVE` and `current_status == DRAFT`: fetch `tenant.settings.get("activation_required_fields", [])`, check each field on the contract, return error listing missing fields if any are empty/null

### 3. Backend: Tests

- [x] 3.1 Test: activation blocked when required fields are missing
- [x] 3.2 Test: activation succeeds when all required fields are filled
- [x] 3.3 Test: activation succeeds when no required fields configured (default)
- [x] 3.4 Test: paused → active transition not blocked by checklist
- [x] 3.5 Test: set_activation_required_fields mutation validates whitelist
- [x] 3.6 Test: set_activation_required_fields mutation rejects invalid field names

### 4. Frontend: Settings UI

- [x] 4.1 Update Settings.tsx to fetch `activationRequiredFields` from tenant settings query
- [x] 4.2 Add "Activation Checklist" card in Settings with toggles for each available field
- [x] 4.3 Add mutation call to save toggled fields

### 5. Frontend: Activate dialog

- [x] 5.1 In the activate confirmation dialog, check contract data against required fields
- [x] 5.2 Show missing fields as a warning list with human-readable labels
- [x] 5.3 Disable confirm button when fields are missing

### 6. Translations

- [x] 6.1 Add German and English translations for settings card labels, field names, and validation messages

### 7. Verification

- [x] 7.1 Run `make test-back` — all tests pass (590 passed, 4 skipped)
- [x] 7.2 Run `npx tsc --noEmit` — no type errors
