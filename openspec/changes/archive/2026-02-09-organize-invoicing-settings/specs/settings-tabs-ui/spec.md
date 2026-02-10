## ADDED Requirements

### Requirement: Settings page uses tabbed navigation
The Settings page SHALL display a tabbed interface with tabs for General, Users, and Invoices sections.

#### Scenario: User navigates to Settings
- **WHEN** user clicks Settings in the sidebar
- **THEN** system displays Settings page with tabbed navigation
- **AND** the General tab is active by default

#### Scenario: User switches tabs
- **WHEN** user clicks on a different tab
- **THEN** the tab content changes to show the selected section
- **AND** the URL updates to reflect the active tab

### Requirement: Invoices tab contains sub-navigation
The Invoices tab SHALL contain sub-tabs for Company Data, Invoice Numbering, and Invoice Template settings.

#### Scenario: User opens Invoices tab
- **WHEN** user clicks the Invoices tab
- **THEN** system displays sub-tabs: Company Data, Numbering, Template
- **AND** Company Data sub-tab is active by default

#### Scenario: User switches invoice sub-tabs
- **WHEN** user clicks a different invoice sub-tab
- **THEN** the content changes to show the selected settings form

### Requirement: Sidebar shows simplified navigation
The sidebar SHALL show only the Settings entry point, not individual invoice config pages.

#### Scenario: User views sidebar
- **WHEN** user views the sidebar
- **THEN** Settings appears as a single menu item
- **AND** Company Data, Invoice Numbering, Invoice Template do NOT appear as separate items

### Requirement: Tabs respect permissions
Tabs SHALL only be visible to users with appropriate permissions.

#### Scenario: User without users permission
- **WHEN** user lacks `users.read` permission
- **THEN** the Users tab is not visible

#### Scenario: User without invoice settings permission
- **WHEN** user lacks `invoices.settings` permission
- **THEN** the Invoices tab is not visible

### Requirement: Logo upload saves correctly
The logo upload in Invoice Template settings SHALL save the uploaded file.

#### Scenario: User uploads logo
- **WHEN** user selects a logo file and saves
- **THEN** the logo is uploaded and saved to the tenant
- **AND** the logo appears in invoice previews
