## ADDED Requirements

### Requirement: Configure M365 credentials per tenant
The system SHALL allow users with `settings.write` permission to configure Microsoft 365 connection credentials: Azure AD tenant ID, client ID, and client secret. Credentials SHALL be stored in the tenant's settings JSON field under the `m365` key.

#### Scenario: Save M365 credentials
- **WHEN** user provides tenant_id, client_id, and client_secret via the settings mutation
- **THEN** system stores the credentials in `Tenant.settings["m365"]` and returns success

#### Scenario: Update existing credentials
- **WHEN** user saves new credentials while existing ones are configured
- **THEN** system overwrites the previous credentials with the new values

#### Scenario: Credentials require settings.write permission
- **WHEN** a user without `settings.write` permission attempts to save M365 credentials
- **THEN** system returns a permission error

### Requirement: Test M365 connection
The system SHALL provide a way to test the configured M365 credentials by acquiring a token from Azure AD using the client credentials flow.

#### Scenario: Successful connection test
- **WHEN** user triggers "Test Connection" with valid credentials configured
- **THEN** system acquires a token via `ConfidentialClientApplication` and returns success with the authenticated app display name

#### Scenario: Failed connection test with invalid credentials
- **WHEN** user triggers "Test Connection" with invalid client_id or client_secret
- **THEN** system returns an error message describing the authentication failure

#### Scenario: Connection test with no credentials configured
- **WHEN** user triggers "Test Connection" with no M365 credentials saved
- **THEN** system returns an error indicating M365 is not configured

### Requirement: Discover available mailboxes
The system SHALL list mailboxes that the configured M365 app has permission to send from, using the Microsoft Graph API.

#### Scenario: List available mailboxes
- **WHEN** user requests mailbox discovery with valid M365 credentials
- **THEN** system queries Graph API for users/mailboxes and returns a list of email addresses and display names

#### Scenario: No mailbox access
- **WHEN** the M365 app has no `Mail.Send` permission or no mailbox access policies configured
- **THEN** system returns an appropriate error from the Graph API response

### Requirement: Select sender mailbox
The system SHALL allow the user to select one mailbox from the discovered list as the default sender for outgoing emails. The selected mailbox SHALL be stored in `Tenant.settings["m365"]["sender_mailbox"]`.

#### Scenario: Select a sender mailbox
- **WHEN** user selects a mailbox from the discovery list
- **THEN** system stores the mailbox address in the M365 config and returns success

#### Scenario: Clear sender mailbox
- **WHEN** user clears the sender mailbox selection
- **THEN** system removes `sender_mailbox` from the M365 config

### Requirement: Query M365 configuration status
The system SHALL expose a query that returns the current M365 configuration state: whether credentials are configured, whether a sender mailbox is selected, and the sender mailbox address (without exposing the client secret).

#### Scenario: M365 configured with sender
- **WHEN** user queries M365 settings with credentials and sender mailbox configured
- **THEN** system returns `isConfigured: true`, `senderMailbox: "invoices@company.com"`, and masked client_id

#### Scenario: M365 not configured
- **WHEN** user queries M365 settings with no credentials saved
- **THEN** system returns `isConfigured: false`, `senderMailbox: null`
