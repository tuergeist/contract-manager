## ADDED Requirements

### Requirement: Admin can view list of tenant users
Tenant admins SHALL be able to view a list of all users in their tenant from Settings > Users.

#### Scenario: View user list
- **WHEN** admin navigates to Settings > Users
- **THEN** system displays a table with all users showing name, email, status, and last login

#### Scenario: Non-admin cannot access user management
- **WHEN** non-admin user navigates to Settings > Users
- **THEN** system displays an access denied message or hides the menu item

### Requirement: Admin can deactivate users
Admins SHALL be able to deactivate user accounts. Deactivated users cannot log in.

#### Scenario: Deactivate user
- **WHEN** admin clicks "Deactivate" on an active user
- **THEN** system marks the user as inactive and they can no longer log in

#### Scenario: Prevent self-deactivation
- **WHEN** admin tries to deactivate their own account
- **THEN** system displays an error preventing self-deactivation

### Requirement: Admin can reactivate users
Admins SHALL be able to reactivate previously deactivated user accounts.

#### Scenario: Reactivate user
- **WHEN** admin clicks "Reactivate" on an inactive user
- **THEN** system marks the user as active and they can log in again

### Requirement: Super-admin has access to all tenants
The user `admin@test.local` SHALL be designated as super-admin with ability to access all tenants for support purposes.

#### Scenario: Super-admin login
- **WHEN** super-admin logs in
- **THEN** system grants access and shows tenant selector if applicable

### Requirement: Tenant has one admin role
Each tenant SHALL have exactly one user designated as admin. Admin status is assigned during initial setup.

#### Scenario: First user is admin
- **WHEN** the first user is created for a tenant
- **THEN** that user SHALL be designated as the tenant admin

#### Scenario: Admin role indicator
- **WHEN** admin views user list
- **THEN** admin user is clearly marked with an "Admin" badge

### Requirement: Admin can view pending invitations
Admins SHALL be able to view all pending invitations for their tenant.

#### Scenario: View pending invitations
- **WHEN** admin views the Users page
- **THEN** system displays a section showing pending invitations with email, created date, and expiry
