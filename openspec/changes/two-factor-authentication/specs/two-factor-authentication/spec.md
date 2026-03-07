## ADDED Requirements

### Requirement: User can enable TOTP-based 2FA
Users SHALL be able to enable TOTP-based two-factor authentication from their profile security settings. The system SHALL generate a TOTP secret and display it as a QR code scannable by authenticator apps (Google Authenticator, Authy, etc.).

#### Scenario: Initiate TOTP setup
- **WHEN** user clicks "Enable Authenticator App" in security settings
- **THEN** system generates a TOTP secret, displays a QR code and the secret key as text, and prompts for a verification code

#### Scenario: Confirm TOTP setup
- **WHEN** user enters a valid 6-digit TOTP code matching the generated secret
- **THEN** system activates TOTP 2FA for the user, stores the secret, and displays one-time recovery codes

#### Scenario: Invalid confirmation code
- **WHEN** user enters an incorrect TOTP code during setup
- **THEN** system displays an error and does not activate 2FA

### Requirement: User can enable email-based 2FA
Users SHALL be able to enable email-based two-factor authentication. When enabled, the system SHALL send a 6-digit code to the user's email address during login.

#### Scenario: Enable email 2FA
- **WHEN** user clicks "Enable Email Code" in security settings and SMTP is configured for the tenant
- **THEN** system activates email-based 2FA for the user

#### Scenario: Enable email 2FA without SMTP
- **WHEN** user attempts to enable email 2FA but SMTP is not configured for the tenant
- **THEN** system displays an error indicating email 2FA is not available

### Requirement: Two-step login with 2FA
When a user with 2FA enabled logs in, the system SHALL require a second verification step after successful password authentication.

#### Scenario: Login with TOTP
- **WHEN** user enters correct credentials and has TOTP 2FA enabled
- **THEN** system returns a temporary challenge token and prompts for a TOTP code

#### Scenario: Login with email code
- **WHEN** user enters correct credentials and has email 2FA enabled
- **THEN** system sends a 6-digit code to the user's email and prompts for the code

#### Scenario: Valid verification code
- **WHEN** user submits a correct verification code with a valid challenge token
- **THEN** system issues the full JWT access and refresh tokens

#### Scenario: Invalid verification code
- **WHEN** user submits an incorrect verification code
- **THEN** system returns an error and does not issue tokens

#### Scenario: Expired challenge token
- **WHEN** user submits a verification code with an expired challenge token (older than 5 minutes)
- **THEN** system returns an error indicating the session has expired

### Requirement: Email verification codes are short-lived
Email-based 2FA codes SHALL expire after 5 minutes and SHALL be single-use.

#### Scenario: Code used within time limit
- **WHEN** user enters the email code within 5 minutes of it being sent
- **THEN** system accepts the code and completes authentication

#### Scenario: Code expired
- **WHEN** user enters the email code after 5 minutes
- **THEN** system rejects the code and prompts user to request a new one

#### Scenario: Code already used
- **WHEN** user enters a code that has already been used
- **THEN** system rejects the code

### Requirement: Rate limiting on verification attempts
The system SHALL rate-limit 2FA verification attempts to prevent brute-force attacks.

#### Scenario: Within rate limit
- **WHEN** fewer than 5 incorrect verification attempts are made within 15 minutes for a challenge
- **THEN** system processes each attempt normally

#### Scenario: Rate limit exceeded
- **WHEN** more than 5 incorrect verification attempts are made within 15 minutes
- **THEN** system rejects further attempts and invalidates the challenge token

### Requirement: Recovery codes for TOTP
When TOTP 2FA is activated, the system SHALL generate 10 single-use recovery codes. Each code SHALL be usable exactly once as an alternative to a TOTP code.

#### Scenario: Display recovery codes on setup
- **WHEN** user completes TOTP 2FA setup
- **THEN** system displays 10 recovery codes and prompts user to save them

#### Scenario: Login with recovery code
- **WHEN** user enters a valid unused recovery code instead of a TOTP code
- **THEN** system accepts the code, marks it as used, and completes authentication

#### Scenario: Used recovery code rejected
- **WHEN** user enters a recovery code that has already been used
- **THEN** system rejects the code

#### Scenario: Regenerate recovery codes
- **WHEN** user clicks "Regenerate Recovery Codes" in security settings
- **THEN** system invalidates all existing codes, generates 10 new ones, and displays them

### Requirement: User can disable 2FA
Users SHALL be able to disable their own 2FA by confirming with their current password.

#### Scenario: Disable 2FA with correct password
- **WHEN** user clicks "Disable 2FA" and enters their correct password
- **THEN** system removes 2FA configuration and recovery codes

#### Scenario: Disable 2FA with incorrect password
- **WHEN** user enters an incorrect password when disabling 2FA
- **THEN** system displays an error and does not disable 2FA

#### Scenario: Disable 2FA when enforcement is active
- **WHEN** user attempts to disable 2FA but the tenant enforces 2FA
- **THEN** system displays an error indicating 2FA is required by the organization

### Requirement: Tenant admin can enforce 2FA
Tenant admins SHALL be able to require all users in the tenant to have 2FA enabled.

#### Scenario: Enable 2FA enforcement
- **WHEN** admin toggles "Require 2FA" in tenant security settings
- **THEN** system stores the enforcement flag on the tenant

#### Scenario: User without 2FA logs in when enforced
- **WHEN** a user without 2FA logs in and the tenant enforces 2FA
- **THEN** system issues a restricted token that only allows access to the 2FA setup page, and redirects user to set up 2FA

#### Scenario: User completes forced 2FA setup
- **WHEN** user completes 2FA setup during enforcement redirect
- **THEN** system upgrades the restricted token to a full access token and redirects to the app

### Requirement: Admin can reset user 2FA
Tenant admins SHALL be able to reset 2FA for any user in their tenant (e.g., when a user loses their authenticator device).

#### Scenario: Admin resets user 2FA
- **WHEN** admin clicks "Reset 2FA" for a user in user management
- **THEN** system removes the user's 2FA configuration and recovery codes

#### Scenario: Reset 2FA for user in enforced tenant
- **WHEN** admin resets 2FA for a user in a tenant with 2FA enforcement
- **THEN** system removes 2FA and the user is forced to set up 2FA again on next login

### Requirement: 2FA status visible in user management
The user administration list SHALL display 2FA status for each user.

#### Scenario: User with 2FA enabled
- **WHEN** admin views the user list and a user has 2FA enabled
- **THEN** system displays a 2FA badge with the method type (TOTP or Email)

#### Scenario: User without 2FA in enforced tenant
- **WHEN** admin views the user list in an enforced tenant and a user has no 2FA
- **THEN** system displays a warning indicator for that user

### Requirement: 2FA GraphQL mutations
The system SHALL expose GraphQL mutations for 2FA operations, all requiring authentication.

#### Scenario: Setup TOTP mutation
- **WHEN** authenticated user calls `setupTotp`
- **THEN** system returns `secret`, `qrCodeUrl`, and `provisioningUri`

#### Scenario: Confirm TOTP mutation
- **WHEN** authenticated user calls `confirmTotp(code: String!)`
- **THEN** system verifies the code against the pending secret and activates TOTP

#### Scenario: Enable email 2FA mutation
- **WHEN** authenticated user calls `enableEmail2fa`
- **THEN** system activates email-based 2FA for the user

#### Scenario: Disable 2FA mutation
- **WHEN** authenticated user calls `disable2fa(password: String!)`
- **THEN** system verifies password and removes 2FA configuration

#### Scenario: Verify 2FA mutation (login step 2)
- **WHEN** unauthenticated user calls `verify2fa(challengeToken: String!, code: String!)`
- **THEN** system verifies the code and returns full JWT tokens on success

#### Scenario: Enforce 2FA mutation
- **WHEN** admin calls `setTenant2faEnforcement(enforced: Boolean!)` with `settings.write` permission
- **THEN** system updates the tenant enforcement setting

#### Scenario: Admin reset 2FA mutation
- **WHEN** admin calls `resetUser2fa(userId: ID!)` with `users.write` permission
- **THEN** system removes 2FA for the target user

### Requirement: Security settings UI
The frontend SHALL provide a "Security" section in user profile settings for 2FA management, and a "Security" sub-tab in tenant settings for enforcement.

#### Scenario: Profile security section
- **WHEN** user navigates to Profile > Security
- **THEN** system displays current 2FA status, options to enable/disable TOTP or email 2FA, and recovery code management

#### Scenario: Tenant security settings
- **WHEN** admin navigates to Settings > General > Security
- **THEN** system displays a toggle for "Require two-factor authentication" with a description
