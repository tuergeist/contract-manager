## ADDED Requirements

### Requirement: Periodic background sync of HubSpot data

The system SHALL automatically sync customers, products, and deals from HubSpot every 6 hours for tenants that have auto-sync enabled.

#### Scenario: Auto-sync runs for enabled tenant
- **WHEN** the periodic sync task fires
- **AND** Tenant A has HubSpot configured and auto-sync enabled
- **THEN** system syncs customers, then products, then deals for Tenant A
- **AND** stores the timestamp and result of each sync type

#### Scenario: Auto-sync skips disabled tenants
- **WHEN** the periodic sync task fires
- **AND** Tenant B has HubSpot configured but auto-sync disabled
- **THEN** system SHALL NOT sync Tenant B's HubSpot data

#### Scenario: Auto-sync skips tenants without HubSpot
- **WHEN** the periodic sync task fires
- **AND** Tenant C has no HubSpot API key configured
- **THEN** system SHALL NOT attempt to sync Tenant C

#### Scenario: Sync order is customers then products then deals
- **WHEN** auto-sync runs for a tenant
- **THEN** system syncs customers first
- **AND** syncs products second
- **AND** syncs deals last
- **AND** a failure in one sync type does not prevent the others from running

#### Scenario: Sync results are logged
- **WHEN** auto-sync completes for a tenant
- **THEN** system stores per-type results (created, updated, skipped, errors) in `hubspot_config`
- **AND** logs a summary at INFO level

### Requirement: Tenant can enable or disable auto-sync

The system SHALL allow tenants to toggle automatic HubSpot sync on or off via settings.

#### Scenario: Enable auto-sync
- **WHEN** admin enables "Automatic sync" in HubSpot settings
- **THEN** `hubspot_config.auto_sync_enabled` is set to `true`
- **AND** next periodic task run SHALL include this tenant

#### Scenario: Disable auto-sync
- **WHEN** admin disables "Automatic sync" in HubSpot settings
- **THEN** `hubspot_config.auto_sync_enabled` is set to `false`
- **AND** next periodic task run SHALL skip this tenant

#### Scenario: Auto-sync is off by default
- **WHEN** a tenant first configures HubSpot
- **THEN** `auto_sync_enabled` defaults to `false`
- **AND** manual sync buttons are the only way to sync

### Requirement: Manual sync remains independent

Manual "Sync now" buttons SHALL continue to work regardless of auto-sync setting.

#### Scenario: Manual sync while auto-sync is enabled
- **WHEN** admin clicks "Sync now" for customers
- **AND** auto-sync is enabled
- **THEN** system syncs customers immediately
- **AND** does not interfere with the next scheduled auto-sync

#### Scenario: Manual sync while auto-sync is disabled
- **WHEN** admin clicks "Sync now" for customers
- **AND** auto-sync is disabled
- **THEN** system syncs customers immediately as before

### Requirement: Settings UI shows auto-sync status

The HubSpot settings section SHALL display auto-sync toggle and last auto-sync information.

#### Scenario: Auto-sync toggle appears in settings
- **WHEN** user views HubSpot settings
- **AND** HubSpot API key is configured
- **THEN** an "Automatic sync every 6 hours" toggle is displayed

#### Scenario: Last auto-sync timestamp shown
- **WHEN** auto-sync has run at least once
- **THEN** settings displays "Last auto-sync: {datetime}" for each sync type (customers, products, deals)

#### Scenario: Toggle hidden without API key
- **WHEN** user views HubSpot settings
- **AND** no HubSpot API key is configured
- **THEN** the auto-sync toggle is not displayed
