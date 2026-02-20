## ADDED Requirements

### Requirement: HubSpot sync completion notification

The system SHALL send a summary email to all active admin users in the tenant after the periodic HubSpot sync completes for that tenant. The email SHALL include results for each sync type (customers, products, deals) and any errors encountered.

#### Scenario: Successful HubSpot sync sends summary to admins
- **WHEN** the periodic HubSpot sync completes for a tenant with all three syncs succeeding
- **THEN** the system SHALL send a `hubspot_sync_completed` notification to all active admin users (`is_admin=True`) in that tenant
- **AND** the email subject SHALL contain "HubSpot Sync"
- **AND** the email body SHALL include created/updated counts for customers, products created/updated counts, and deals created/skipped counts

#### Scenario: Partial failure includes error info
- **WHEN** the HubSpot sync completes but one sync type (e.g., products) failed with an exception
- **THEN** the notification email SHALL include the successful results for the other sync types
- **AND** the email SHALL indicate which sync type failed

#### Scenario: No admin users means no notification
- **WHEN** the HubSpot sync completes for a tenant with no active admin users
- **THEN** the system SHALL not attempt to send any notification

#### Scenario: Non-admin users do not receive the notification
- **WHEN** the HubSpot sync completes and the tenant has both admin and non-admin users
- **THEN** only users with `is_admin=True` SHALL be included as recipients

### Requirement: Time tracking sync completion notification

The system SHALL send a summary email to all active admin users in each tenant after the periodic time tracking refresh completes. The email SHALL include the count of mappings synced and any failures.

#### Scenario: Successful time tracking sync sends summary
- **WHEN** the periodic time tracking refresh completes and a tenant has mappings that were synced
- **THEN** the system SHALL send a `time_tracking_sync_completed` notification to all active admin users in that tenant
- **AND** the email subject SHALL contain "Time Tracking Sync"
- **AND** the email body SHALL include the number of mappings synced and total mappings for that tenant

#### Scenario: Time tracking sync with failures
- **WHEN** the time tracking refresh completes and some mappings failed to sync
- **THEN** the notification email SHALL indicate how many mappings failed

#### Scenario: No mappings for tenant means no notification
- **WHEN** the periodic time tracking refresh runs and a tenant has no time tracking mappings
- **THEN** the system SHALL not send a notification to that tenant's admins

### Requirement: Background task notification emails use HTML format

The system SHALL render background task notification emails as HTML with inline styles, consistent with existing notification emails.

#### Scenario: HubSpot sync email format
- **WHEN** a HubSpot sync notification is sent
- **THEN** the email body SHALL be HTML containing a summary with sync type headings and result counts

#### Scenario: Time tracking sync email format
- **WHEN** a time tracking sync notification is sent
- **THEN** the email body SHALL be HTML containing a summary with mapping sync counts
