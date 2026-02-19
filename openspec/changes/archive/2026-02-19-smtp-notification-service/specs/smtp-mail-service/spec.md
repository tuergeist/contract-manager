## ADDED Requirements

### Requirement: SMTP configuration storage
The system SHALL store per-tenant SMTP configuration in `tenant.settings.smtp` with fields: `host` (string), `port` (integer), `username` (string), `password` (string), `from_address` (string), `use_tls` (boolean).

#### Scenario: Configuration saved successfully
- **WHEN** an admin saves SMTP settings with host "smtp-relay.brevo.com", port 587, username, password, from address, and TLS enabled
- **THEN** the system stores all fields in `tenant.settings.smtp` and returns success

#### Scenario: Partial configuration
- **WHEN** an admin saves SMTP settings with host and port but no username or password
- **THEN** the system stores the partial config (SMTP is not considered configured until host, port, username, password, and from_address are all present)

### Requirement: SMTP connection test
The system SHALL provide a connection test that verifies SMTP connectivity and authentication without sending an email.

#### Scenario: Successful connection test
- **WHEN** an admin triggers a connection test with valid SMTP credentials
- **THEN** the system connects to the SMTP server, performs EHLO, STARTTLS (if enabled), authenticates, then disconnects, and returns success

#### Scenario: Connection test with invalid host
- **WHEN** an admin triggers a connection test with an unreachable host
- **THEN** the system returns an error with a descriptive message (e.g. connection refused)

#### Scenario: Connection test with invalid credentials
- **WHEN** an admin triggers a connection test with wrong username/password
- **THEN** the system returns an error indicating authentication failure

#### Scenario: Connection test when SMTP not configured
- **WHEN** an admin triggers a connection test but SMTP settings are missing required fields
- **THEN** the system returns an error "SMTP not configured"

### Requirement: Send test email
The system SHALL send a test email to the current user's email address via SMTP to verify end-to-end delivery.

#### Scenario: Successful test email
- **WHEN** an admin clicks "Send Test Email" and SMTP is configured correctly
- **THEN** the system sends an HTML email to the admin's email address with subject "Test Email from Contract Manager" and returns success

#### Scenario: Test email with delivery failure
- **WHEN** an admin clicks "Send Test Email" but the SMTP server rejects the message
- **THEN** the system returns an error with the SMTP server's error message

### Requirement: Send notification API
The system SHALL provide a `send_notification(tenant, *, to, subject, body_html)` function that sends an email via SMTP using the tenant's configuration.

#### Scenario: Successful notification send
- **WHEN** a caller invokes `send_notification` with a configured tenant, recipient list, subject, and HTML body
- **THEN** the system connects to SMTP, sends the email from the configured `from_address` to all recipients, and returns without error

#### Scenario: Notification send with unconfigured tenant
- **WHEN** a caller invokes `send_notification` on a tenant without SMTP configuration
- **THEN** the system raises `SmtpError` with message "SMTP not configured"

#### Scenario: Notification send with SMTP server error
- **WHEN** a caller invokes `send_notification` but the SMTP server returns an error
- **THEN** the system raises `SmtpError` with the server's error details

### Requirement: SMTP settings query
The system SHALL expose SMTP configuration via a GraphQL query that masks the password.

#### Scenario: Query configured SMTP settings
- **WHEN** an authenticated user queries `smtp_settings`
- **THEN** the system returns host, port, username, from_address, use_tls, `is_configured: true`, and password masked (e.g. "********" if set, empty if not)

#### Scenario: Query unconfigured SMTP settings
- **WHEN** an authenticated user queries `smtp_settings` and no SMTP config exists
- **THEN** the system returns `is_configured: false` with empty/default values

### Requirement: SMTP settings mutations require settings.write permission
All SMTP mutations (save, test connection, send test email) SHALL require the `settings.write` permission.

#### Scenario: Unauthorized user attempts to save SMTP settings
- **WHEN** a user without `settings.write` permission attempts to save SMTP settings
- **THEN** the system returns a permission error

### Requirement: Settings UI for SMTP configuration
The system SHALL provide a "Notifications" sub-tab under General settings with a form for SMTP configuration.

#### Scenario: Admin configures SMTP
- **WHEN** an admin navigates to Settings > General > Notifications
- **THEN** the system displays a form with fields for Host, Port, Username, Password, From Address, a TLS toggle, and buttons for Save, Test Connection, and Send Test Email

#### Scenario: Admin saves and tests SMTP configuration
- **WHEN** an admin fills in the SMTP form, clicks Save, then clicks Test Connection
- **THEN** the system saves the configuration, then tests the connection and displays the result (success or error message)

#### Scenario: Form loads existing configuration
- **WHEN** an admin navigates to the Notifications tab and SMTP is already configured
- **THEN** the form is pre-populated with the existing settings (password shown as masked placeholder)
