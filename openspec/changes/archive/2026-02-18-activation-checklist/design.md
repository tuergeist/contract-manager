## Context

Contracts can transition from `draft` → `active` via the `update_contract_status` mutation. Currently there is no validation of contract completeness — any draft can be activated regardless of missing fields. The `Tenant` model has a `settings` JSONField already used for various config, and contract fields like `po_number`, `netsuite_sales_order_number`, `netsuite_url`, `order_confirmation_number` are all nullable `CharField`/`URLField`.

## Goals / Non-Goals

**Goals:**
- Tenant admins can configure which contract fields must be filled before activation
- The status transition mutation validates these fields and returns clear errors
- Frontend shows missing fields in the activation confirmation dialog
- Zero-migration approach using existing `Tenant.settings` JSONField

**Non-Goals:**
- Custom/arbitrary fields (only existing Contract model fields are checkable)
- Per-customer or per-contract-type overrides
- Validation on other status transitions (only draft → active)

## Decisions

### 1. Store config in `Tenant.settings` under `activation_required_fields`

Store as a list of field names in `Tenant.settings["activation_required_fields"]`: e.g. `["po_number", "netsuite_sales_order_number"]`. Empty list or absent key = no requirements.

**Why:** No migration needed. The `settings` JSONField already exists and is the canonical place for tenant-level feature config. A dedicated model would be overengineered for a simple list of field names.

### 2. Validate in `update_contract_status` mutation

Add validation right after the allowed-transitions check, only for `new_status == ACTIVE`. Fetch `tenant.settings.get("activation_required_fields", [])`, check each field on the contract, collect missing ones, return error with the list.

**Why:** Single enforcement point. The mutation is the only way to change status, so validation here is complete.

### 3. Allowable fields whitelist

Only allow a known set of fields to be configured: `po_number`, `order_confirmation_number`, `netsuite_sales_order_number`, `netsuite_contract_number`, `netsuite_url`. This prevents invalid field names from being stored.

### 4. Frontend: show missing fields as a warning list in the activate dialog

The activate confirmation already exists. Add a pre-check query or compute locally from the contract data + settings. If fields are missing, show them as a warning list and disable the confirm button. If all fields are set, show the existing confirmation text.

**Why:** Better UX than attempting activation and getting an error. The frontend already has all the data needed (contract fields + settings from tenant query).

## Risks / Trade-offs

- **Risk:** Admin forgets to configure → no validation happens → same as today (acceptable default)
- **Risk:** Field renamed in model → config references stale name → validation silently skips unknown fields (safe fallback, log a warning)
- **Trade-off:** No per-field custom labels in settings UI — use translation keys based on field names. Simpler but less flexible.
