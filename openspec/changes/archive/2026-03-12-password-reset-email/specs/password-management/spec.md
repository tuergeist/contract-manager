## ADDED Requirements

### Requirement: Self-service password reset request
Unauthenticated users SHALL be able to request a password reset from the login page by entering their email address. The system SHALL generate a time-limited reset token and send a reset link via email using the tenant's SMTP configuration.

#### Scenario: Request reset for existing user
- **WHEN** user enters a registered email address and submits the forgot-password form
- **THEN** system generates a reset token (valid 24 hours), sends a password reset email via `send_notification()`, and displays a success message

#### Scenario: Request reset for non-existing email
- **WHEN** user enters an email address that is not registered
- **THEN** system displays the same success message as for existing users to prevent email enumeration

#### Scenario: Request reset when SMTP not configured
- **WHEN** user requests a password reset but the tenant has no SMTP configuration
- **THEN** system displays an error indicating that password reset via email is not available

### Requirement: Password reset rate limiting
The system SHALL rate-limit password reset requests to prevent abuse.

#### Scenario: Within rate limit
- **WHEN** fewer than 5 reset requests have been made for the same email within 15 minutes
- **THEN** system processes the request normally

#### Scenario: Rate limit exceeded
- **WHEN** more than 5 reset requests are made for the same email within 15 minutes
- **THEN** system silently discards further requests and still displays the generic success message

### Requirement: Password reset email content
The system SHALL send the reset email using `send_notification()` from the SMTP mail service. The email SHALL contain a link to the password reset page with the embedded reset token.

#### Scenario: German tenant
- **WHEN** tenant language is "de" or unset
- **THEN** email subject is "Passwort zurücksetzen" and body is in German, containing the reset link and tenant name

#### Scenario: English tenant
- **WHEN** tenant language is "en"
- **THEN** email subject is "Reset your password" and body is in English, containing the reset link and tenant name

### Requirement: Login page forgot-password link
The login page SHALL display a "Forgot Password?" link that navigates to the password reset request form.

#### Scenario: Navigate to forgot password
- **WHEN** user clicks "Forgot Password?" on the login page
- **THEN** system navigates to a form with an email input field and a "Send Reset Link" button

#### Scenario: Back to login
- **WHEN** user is on the forgot-password form
- **THEN** a "Back to Login" link is visible and navigates back to the login page

### Requirement: Password reset request GraphQL mutation
The system SHALL expose a `requestPasswordReset(email: String!)` GraphQL mutation that does not require authentication.

#### Scenario: Mutation with registered email
- **WHEN** `requestPasswordReset` is called with a registered email
- **THEN** system creates a reset token, dispatches the email via Celery task, and returns `{ success: true }`

#### Scenario: Mutation with unregistered email
- **WHEN** `requestPasswordReset` is called with an unregistered email
- **THEN** system returns `{ success: true }` without sending an email

## MODIFIED Requirements

### Requirement: Admin can trigger password reset for users
Tenant admins SHALL be able to generate a password reset link for any user in their tenant. When SMTP is configured, the system SHALL also send the reset link to the user's email address.

#### Scenario: Generate reset link
- **WHEN** admin clicks "Reset Password" for a user
- **THEN** system generates a reset token and displays a copyable reset link

#### Scenario: Copy reset link
- **WHEN** admin clicks "Copy Link" on the reset link
- **THEN** system copies the reset URL to clipboard

#### Scenario: Admin reset sends email when SMTP configured
- **WHEN** admin clicks "Reset Password" for a user and SMTP is configured for the tenant
- **THEN** system generates the reset link, displays it to the admin, AND sends the reset email to the user

#### Scenario: Admin reset without SMTP
- **WHEN** admin clicks "Reset Password" for a user and SMTP is not configured
- **THEN** system generates the reset link and displays it to the admin only (no email sent, no error)
