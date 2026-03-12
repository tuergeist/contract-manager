## ADDED Requirements

### Requirement: Activation workflow modal
When a user initiates a `draft → active` transition, the system SHALL display an activation workflow modal instead of the simple confirmation dialog. The modal SHALL contain: activation checklist warnings (existing behavior), post-activation options with checkboxes, a confirmation message, and Activate/Cancel buttons.

#### Scenario: Modal opens on activate click
- **WHEN** a user clicks "Activate" on a draft contract
- **THEN** the activation workflow modal opens
- **AND** the modal displays the contract name in the header

#### Scenario: Other transitions unchanged
- **WHEN** a user initiates any transition other than `draft → active` (pause, resume, cancel, end, reset-to-draft)
- **THEN** the existing simple confirmation dialog is shown (no workflow modal)

### Requirement: Activation checklist in modal
The modal SHALL display activation checklist validation at the top. If required fields are missing, they SHALL be listed as warnings and the Activate button SHALL be disabled. This is the same validation logic as the current confirm dialog, relocated into the new modal.

#### Scenario: Missing required fields
- **WHEN** the activation checklist requires `po_number` and it is empty
- **THEN** the modal shows "PO Number" as a missing required field
- **AND** the Activate button is disabled

#### Scenario: All required fields present
- **WHEN** all activation checklist fields are filled
- **THEN** the warning section is hidden
- **AND** the Activate button is enabled

#### Scenario: No checklist configured
- **WHEN** `activation_required_fields` is empty
- **THEN** no checklist warnings are shown
- **AND** the Activate button is enabled

### Requirement: Order confirmation option
The modal SHALL include a checkbox "Send order confirmation" (default: checked). The checkbox SHALL be disabled with an explanation if M365 is not configured or the customer has no billing emails. Even when email cannot be sent, the PDF SHALL still be generated if the option is checked.

#### Scenario: AB option default checked
- **WHEN** the modal opens and M365 is configured and customer has billing emails
- **THEN** "Send order confirmation" is checked by default and enabled

#### Scenario: AB option disabled — no M365
- **WHEN** M365 is not configured
- **THEN** "Send order confirmation" checkbox is unchecked and disabled
- **AND** a hint explains that email sending is not configured

#### Scenario: AB option disabled — no billing emails
- **WHEN** the customer has no billing email addresses
- **THEN** "Send order confirmation" checkbox is unchecked and disabled
- **AND** a hint explains that the customer has no billing emails

### Requirement: Activation mutation with options
The `transition_contract_status` mutation SHALL accept an optional `activationOptions` input for the `draft → active` transition. The input SHALL include `sendOrderConfirmation` (boolean, default true). For all other transitions, `activationOptions` SHALL be ignored.

#### Scenario: Activate with AB
- **WHEN** the mutation is called with `newStatus: "active"` and `activationOptions: { sendOrderConfirmation: true }`
- **THEN** the contract is activated
- **AND** an OrderConfirmation record is created
- **AND** PDF generation and email sending tasks are queued

#### Scenario: Activate without AB
- **WHEN** the mutation is called with `newStatus: "active"` and `activationOptions: { sendOrderConfirmation: false }`
- **THEN** the contract is activated
- **AND** no OrderConfirmation is created

#### Scenario: Activate without options (backward compatible)
- **WHEN** the mutation is called with `newStatus: "active"` and no `activationOptions`
- **THEN** the contract is activated with default behavior (`sendOrderConfirmation: true`)

#### Scenario: Options ignored for non-activation
- **WHEN** the mutation is called with `newStatus: "paused"` and `activationOptions` provided
- **THEN** the options are ignored and the transition proceeds normally

### Requirement: Post-activation feedback
After activation, the modal SHALL show a success state indicating: contract activated, AB being generated (if selected), and AB email being sent (if applicable). The modal SHALL close after the user acknowledges.

#### Scenario: Success with AB
- **WHEN** activation succeeds with sendOrderConfirmation enabled
- **THEN** the modal shows "Contract activated. Order confirmation is being generated and will be sent by email."

#### Scenario: Success without AB
- **WHEN** activation succeeds with sendOrderConfirmation disabled
- **THEN** the modal shows "Contract activated."

#### Scenario: Success with AB but no email
- **WHEN** activation succeeds with sendOrderConfirmation enabled but M365 is not configured
- **THEN** the modal shows "Contract activated. Order confirmation is being generated."
