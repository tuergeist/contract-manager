## ADDED Requirements

### Requirement: User can change their own password
Authenticated users SHALL be able to change their password from their profile settings.

#### Scenario: Change password successfully
- **WHEN** user enters current password, new password, and confirmation matching
- **THEN** system updates the password and shows success message

#### Scenario: Current password incorrect
- **WHEN** user enters incorrect current password
- **THEN** system displays an error that current password is incorrect

#### Scenario: New password confirmation mismatch
- **WHEN** user enters new password and confirmation that do not match
- **THEN** system displays a validation error

#### Scenario: New password too short
- **WHEN** user enters a new password shorter than 8 characters
- **THEN** system displays a validation error

### Requirement: Admin can trigger password reset for users
Tenant admins SHALL be able to generate a password reset link for any user in their tenant.

#### Scenario: Generate reset link
- **WHEN** admin clicks "Reset Password" for a user
- **THEN** system generates a reset token and displays a copyable reset link

#### Scenario: Copy reset link
- **WHEN** admin clicks "Copy Link" on the reset link
- **THEN** system copies the reset URL to clipboard

### Requirement: Password reset link expires
Password reset links SHALL expire after 24 hours.

#### Scenario: Use valid reset link
- **WHEN** user accesses reset link within 24 hours
- **THEN** system displays the password reset form

#### Scenario: Use expired reset link
- **WHEN** user accesses reset link after 24 hours
- **THEN** system displays an error that the link has expired

### Requirement: User can set new password via reset link
Users accessing a valid reset link SHALL be able to set a new password.

#### Scenario: Complete password reset
- **WHEN** user enters a valid new password and confirmation
- **THEN** system updates the password, invalidates the reset token, and redirects to login
