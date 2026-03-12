## MODIFIED Requirements

### Requirement: Periodic background sync of HubSpot data

The system SHALL automatically sync customers, products, and deals from HubSpot every 6 hours for tenants that have auto-sync enabled and are using polling sync mode. Tenants using webhook sync mode SHALL be skipped by the periodic task.

#### Scenario: Auto-sync runs for enabled tenant in polling mode
- **WHEN** the periodic sync task fires
- **AND** Tenant A has HubSpot configured and auto-sync enabled
- **AND** Tenant A's `sync_mode` is `"polling"` or not set
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

#### Scenario: Auto-sync skips tenants in webhook mode
- **WHEN** the periodic sync task fires
- **AND** Tenant D has HubSpot configured and auto-sync enabled
- **AND** Tenant D's `sync_mode` is `"webhooks"`
- **THEN** system SHALL NOT sync Tenant D's HubSpot data via the periodic task
