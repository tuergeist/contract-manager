## ADDED Requirements

### Requirement: Webhook configuration in HubSpot settings

The HubSpot integration settings SHALL include a section for configuring webhook-based sync as an alternative to polling.

#### Scenario: Webhook settings section visible when HubSpot configured
- **WHEN** admin views HubSpot integration settings
- **AND** a HubSpot API key is configured
- **THEN** a "Webhook Sync" section is displayed below the existing sync controls

#### Scenario: Webhook settings hidden without HubSpot
- **WHEN** admin views HubSpot integration settings
- **AND** no HubSpot API key is configured
- **THEN** the webhook settings section is not displayed

### Requirement: Portal ID configuration

The system SHALL allow admins to enter their HubSpot portal ID, which is required for routing webhook events to the correct tenant.

#### Scenario: Save portal ID
- **WHEN** admin enters a portal ID and saves
- **THEN** `hubspot_config.portal_id` is stored
- **AND** a success message is shown

#### Scenario: Portal ID displayed as read-only when set
- **WHEN** admin views webhook settings
- **AND** a portal ID is already configured
- **THEN** the portal ID is displayed with an option to change it

### Requirement: Client secret configuration

The system SHALL allow admins to enter their HubSpot app's client secret for webhook signature verification.

#### Scenario: Save client secret
- **WHEN** admin enters a client secret and saves
- **THEN** `hubspot_config.client_secret` is stored
- **AND** the input shows a masked placeholder (not the actual secret)

#### Scenario: Client secret masked after save
- **WHEN** admin views webhook settings
- **AND** a client secret is already configured
- **THEN** the field shows `••••••••` placeholder, not the actual value

### Requirement: Sync mode toggle

The system SHALL allow admins to switch between polling and webhook sync modes.

#### Scenario: Switch to webhook mode
- **WHEN** admin selects "Webhooks" as the sync mode
- **AND** portal ID and client secret are configured
- **THEN** `hubspot_config.sync_mode` is set to `"webhooks"`
- **AND** a message confirms that the 6-hour polling sync is now disabled for this tenant

#### Scenario: Switch to polling mode
- **WHEN** admin selects "Polling (every 6 hours)" as the sync mode
- **THEN** `hubspot_config.sync_mode` is set to `"polling"`
- **AND** a message confirms that scheduled sync is active

#### Scenario: Cannot enable webhooks without portal ID and secret
- **WHEN** admin tries to switch to webhook mode
- **AND** portal ID or client secret is missing
- **THEN** the system shows an error and does not switch modes

#### Scenario: Default sync mode is polling
- **WHEN** a tenant has HubSpot configured but has never set sync mode
- **THEN** the effective sync mode is `"polling"`

### Requirement: Webhook endpoint URL displayed

The settings SHALL display the webhook endpoint URL that the admin needs to configure in HubSpot's developer portal.

#### Scenario: Endpoint URL shown
- **WHEN** admin views webhook settings
- **THEN** the full webhook URL is displayed (e.g., `https://<domain>/api/hubspot/webhook/`)
- **AND** a copy button is provided

### Requirement: Webhook activity indicator

The settings SHALL show when the last webhook event was received and processed.

#### Scenario: Last webhook event shown
- **WHEN** at least one webhook event has been processed for this tenant
- **THEN** settings displays "Last webhook received: {datetime}"

#### Scenario: No webhook events yet
- **WHEN** no webhook events have been received
- **AND** webhook mode is enabled
- **THEN** settings displays a hint that no events have been received yet
