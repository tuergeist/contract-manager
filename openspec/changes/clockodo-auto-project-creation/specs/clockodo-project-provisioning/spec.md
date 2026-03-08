## ADDED Requirements

### Requirement: CM customers can be linked to Clockodo customers
The system SHALL allow linking a Contract Manager customer to a Clockodo customer. This mapping is stored persistently and used for automatic project creation.

#### Scenario: Link customer manually
- **WHEN** user opens a customer detail page and clicks "Link Clockodo Customer"
- **THEN** system shows a searchable dropdown of Clockodo customers and saves the selected mapping

#### Scenario: Auto-match by name
- **WHEN** user clicks "Auto-match" on the customer linking UI
- **THEN** system attempts to match CM customers to Clockodo customers by name (case-insensitive) and shows proposed matches for confirmation

#### Scenario: Create Clockodo customer from CM
- **WHEN** no matching Clockodo customer exists and user clicks "Create in Clockodo"
- **THEN** system creates a new customer in Clockodo via API and stores the mapping

#### Scenario: Unlink customer
- **WHEN** user clicks "Unlink" on a linked customer
- **THEN** system removes the Clockodo customer mapping (does not delete the Clockodo customer)

### Requirement: Configurable project naming templates
The system SHALL allow tenant admins to configure naming templates for automatically created Clockodo projects.

#### Scenario: Configure maintenance project name
- **WHEN** admin opens time tracking settings
- **THEN** system shows a "Maintenance Project Name" field with placeholders support (e.g., `Wartung {customer_name}`)

#### Scenario: Configure one-off project name
- **WHEN** admin opens time tracking settings
- **THEN** system shows a "One-Off Project Name" field with placeholders support (e.g., `{customer_name} - {contract_name}`)

#### Scenario: Default templates
- **WHEN** no templates are configured
- **THEN** system uses defaults: `Wartung {customer_name}` for maintenance, `{customer_name} - {contract_name}` for one-off

### Requirement: Automatic project creation on contract activation
When a contract transitions from draft to active, the system SHALL check whether Clockodo projects need to be created and present the user with a confirmation dialog.

#### Scenario: Contract with recurring items, no maintenance project exists
- **WHEN** user activates a contract that has recurring items and the customer's Clockodo maintenance project does not exist
- **THEN** system shows a confirmation dialog proposing to create a maintenance project with the configured name template

#### Scenario: Contract with recurring items, maintenance project already exists
- **WHEN** user activates a contract that has recurring items and the customer already has a mapped maintenance project in Clockodo
- **THEN** system automatically links the contract to the existing maintenance project without creating a new one

#### Scenario: Contract with one-off items, user chooses combined project
- **WHEN** user activates a contract with one-off items and selects "One project for all one-off items"
- **THEN** system creates a single Clockodo project for all one-off items in the contract

#### Scenario: Contract with one-off items, user chooses per-item projects
- **WHEN** user activates a contract with one-off items and selects "One project per item"
- **THEN** system creates a separate Clockodo project for each one-off item

#### Scenario: Contract with both recurring and one-off items
- **WHEN** user activates a contract that has both recurring and one-off items
- **THEN** system handles each type independently: maintenance project for recurring, user-chosen strategy for one-off

#### Scenario: Skip project creation
- **WHEN** user activates a contract and the confirmation dialog appears
- **THEN** user can click "Skip" to activate the contract without creating Clockodo projects

#### Scenario: Customer not linked to Clockodo
- **WHEN** user activates a contract but the customer has no Clockodo mapping
- **THEN** system shows a prompt to link or create the Clockodo customer first, or skip project creation

#### Scenario: Clockodo not configured
- **WHEN** user activates a contract but the tenant has no Clockodo integration configured
- **THEN** system activates the contract normally without any Clockodo dialog

### Requirement: Clockodo write API operations
The ClockodoProvider SHALL support creating customers and projects via the Clockodo API.

#### Scenario: Create customer
- **WHEN** system calls create_customer with a name
- **THEN** system sends POST to Clockodo API /customers and returns the created customer ID

#### Scenario: Create project
- **WHEN** system calls create_project with a customer ID and project name
- **THEN** system sends POST to Clockodo API /projects and returns the created project ID

#### Scenario: API error handling
- **WHEN** a Clockodo API write call fails
- **THEN** system logs the error and returns an error message to the user without blocking contract activation

### Requirement: Automatic TimeTrackingProjectMapping creation
When Clockodo projects are created or linked during activation, the system SHALL automatically create the corresponding TimeTrackingProjectMapping records.

#### Scenario: Mapping created for new project
- **WHEN** a new Clockodo project is created during activation
- **THEN** system creates a TimeTrackingProjectMapping linking the project to the contract (and optionally to specific contract items), with link_source="auto"

#### Scenario: Mapping created for existing maintenance project
- **WHEN** an existing maintenance project is reused during activation
- **THEN** system creates a TimeTrackingProjectMapping linking it to the contract if no mapping for that project+contract exists yet

### Requirement: Bulk customer linking
The system SHALL provide a bulk customer linking view to connect multiple CM customers to Clockodo customers at once.

#### Scenario: Bulk auto-match
- **WHEN** admin opens the bulk linking view and clicks "Auto-match all"
- **THEN** system shows all proposed name-based matches with accept/reject per pair

#### Scenario: Bulk confirm
- **WHEN** admin confirms selected matches
- **THEN** system saves all confirmed Clockodo customer mappings
