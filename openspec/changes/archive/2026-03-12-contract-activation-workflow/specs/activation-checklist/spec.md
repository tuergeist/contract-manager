## MODIFIED Requirements

### Requirement: Frontend pre-check
The activate confirmation dialog checks required fields before showing the confirm button. Missing fields are displayed as a warning list. The confirm button is disabled until all required fields are filled.

**Change**: The checklist validation UI is relocated from the `StatusTransitionModal` into the new `ActivationWorkflowModal`. The validation logic, display of missing fields, and button disabling behavior remain identical. The `StatusTransitionModal` no longer handles the `draft → active` case.

#### Scenario: Frontend shows missing fields
- **WHEN** required fields are `["po_number", "netsuite_url"]`
- **AND** a draft contract has `po_number = null`
- **THEN** the activation workflow modal shows `po_number` as missing
- **AND** the Activate button is disabled

#### Scenario: Checklist in workflow modal
- **WHEN** the user clicks Activate on a draft contract
- **THEN** the activation workflow modal opens (not the old StatusTransitionModal)
- **AND** the checklist validation is displayed at the top of the modal
- **AND** post-activation options are displayed below the checklist
