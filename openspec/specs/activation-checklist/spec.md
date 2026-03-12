## activation-checklist

Configurable per-tenant checklist of required contract fields that must be filled before a contract can be activated.

### Requirements

1. **REQ-1: Settings configuration** — Tenant admins can configure which contract fields are required for activation via the Settings page. Configurable fields: `po_number`, `order_confirmation_number`, `netsuite_sales_order_number`, `netsuite_contract_number`, `netsuite_url`.

2. **REQ-2: Backend validation** — When transitioning a contract from `draft` to `active`, the `update_contract_status` mutation checks all configured required fields. If any are empty/null, the mutation returns an error listing the missing fields.

3. **REQ-3: Frontend pre-check** — The `ActivationWorkflowModal` checks required fields before showing the confirm button. Missing fields are displayed as a warning list. The Activate button is disabled until all required fields are filled. (Previously in `StatusTransitionModal`, relocated to the new activation workflow modal.)

4. **REQ-4: No impact on existing contracts** — Validation only applies to the draft → active transition. Already-active contracts and other transitions are unaffected.

5. **REQ-5: GraphQL API** — A query exposes the current `activation_required_fields` setting. A mutation allows updating it (admin-only).

### Scenarios

#### S1: Admin configures required fields
- **Given** a tenant admin on the Settings page
- **When** they toggle `po_number` and `netsuite_url` as required
- **Then** `tenant.settings["activation_required_fields"]` is `["po_number", "netsuite_url"]`

#### S2: Activation blocked — missing fields
- **Given** required fields are `["po_number", "netsuite_url"]`
- **And** a draft contract has `po_number = null` and `netsuite_url = null`
- **When** the user attempts to activate the contract
- **Then** the mutation returns an error listing `po_number` and `netsuite_url` as missing
- **And** the contract remains in `draft` status

#### S3: Activation succeeds — all fields filled
- **Given** required fields are `["po_number"]`
- **And** a draft contract has `po_number = "PO-123"`
- **When** the user attempts to activate
- **Then** the contract transitions to `active`

#### S4: No required fields configured
- **Given** `activation_required_fields` is empty or absent
- **When** the user activates any draft contract
- **Then** activation proceeds without additional validation (same as today)

#### S5: Frontend shows missing fields
- **Given** required fields are `["po_number", "netsuite_url"]`
- **And** a draft contract has `po_number = null`
- **When** the user clicks the Activate button
- **Then** the confirmation dialog shows `po_number` as missing
- **And** the confirm button is disabled

#### S6: Already-active contracts unaffected
- **Given** required fields are `["po_number"]`
- **And** an active contract has `po_number = null`
- **When** the contract is paused or cancelled
- **Then** the transition succeeds (checklist only applies to draft → active)

#### S7: Re-activation from paused
- **Given** required fields are `["po_number"]`
- **And** a paused contract has `po_number = null`
- **When** the user resumes (paused → active)
- **Then** the transition succeeds (checklist only applies to draft → active)
