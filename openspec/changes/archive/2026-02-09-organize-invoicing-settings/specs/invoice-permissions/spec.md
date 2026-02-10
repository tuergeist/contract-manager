## ADDED Requirements

### Requirement: Granular invoice permissions exist
The system SHALL define separate permissions for invoice operations: read, export, generate, and settings.

#### Scenario: Permission registry includes invoice permissions
- **WHEN** system initializes permissions
- **THEN** the following permissions exist: `invoices.read`, `invoices.export`, `invoices.generate`, `invoices.settings`

### Requirement: Invoice export requires export permission
The invoice export functionality SHALL require `invoices.export` permission.

#### Scenario: User with export permission accesses export
- **WHEN** user with `invoices.export` permission navigates to invoice export
- **THEN** user can access the export page and download invoices

#### Scenario: User without export permission
- **WHEN** user without `invoices.export` permission attempts to access export
- **THEN** system denies access

### Requirement: Invoice generation requires generate permission
Creating and finalizing invoices SHALL require `invoices.generate` permission.

#### Scenario: User with generate permission creates invoice
- **WHEN** user with `invoices.generate` permission clicks generate invoices
- **THEN** system allows invoice generation

#### Scenario: User without generate permission
- **WHEN** user without `invoices.generate` permission views invoice export
- **THEN** the generate button is hidden or disabled

### Requirement: Invoice settings require settings permission
Configuring company data, numbering, and template SHALL require `invoices.settings` permission.

#### Scenario: User with settings permission accesses configuration
- **WHEN** user with `invoices.settings` permission opens Settings Invoices tab
- **THEN** user can view and modify all invoice configuration

#### Scenario: User without settings permission
- **WHEN** user without `invoices.settings` permission opens Settings
- **THEN** the Invoices tab is not visible

### Requirement: Default roles have appropriate invoice permissions
Default roles SHALL be configured with sensible invoice permission defaults.

#### Scenario: Admin role permissions
- **WHEN** Admin role is created
- **THEN** role has all invoice permissions: read, export, generate, settings

#### Scenario: Manager role permissions
- **WHEN** Manager role is created
- **THEN** role has `invoices.read`, `invoices.export`, `invoices.generate`
- **AND** role does NOT have `invoices.settings`

#### Scenario: Viewer role permissions
- **WHEN** Viewer role is created
- **THEN** role has only `invoices.read`

### Requirement: Migration preserves existing access
Existing roles with `invoices.write` SHALL be migrated to have export and generate permissions.

#### Scenario: Role migration on upgrade
- **WHEN** system upgrades with existing roles having `invoices.write`
- **THEN** those roles receive `invoices.export` and `invoices.generate` permissions
- **AND** `invoices.write` is removed from the permission registry
