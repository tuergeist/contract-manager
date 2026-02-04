## Requirements

### Requirement: Admin can view list of tenant users
Users with `users.read` permission SHALL be able to view a list of all users in their tenant from Settings > Users.

#### Scenario: View user list
- **WHEN** user with `users.read` navigates to Settings > Users
- **THEN** system displays a table with all users showing name, email, roles, status, and last login

#### Scenario: User without permission cannot access user management
- **WHEN** user without `users.read` permission navigates to Settings > Users
- **THEN** system displays an access denied message or hides the menu item

### Requirement: Admin can deactivate users
Users with `users.write` permission SHALL be able to deactivate user accounts. Deactivated users cannot log in.

#### Scenario: Deactivate user
- **WHEN** user with `users.write` clicks "Deactivate" on an active user
- **THEN** system marks the user as inactive and they can no longer log in

#### Scenario: Prevent self-deactivation
- **WHEN** user tries to deactivate their own account
- **THEN** system displays an error preventing self-deactivation

### Requirement: Admin can reactivate users
Users with `users.write` permission SHALL be able to reactivate previously deactivated user accounts.

#### Scenario: Reactivate user
- **WHEN** user with `users.write` clicks "Reactivate" on an inactive user
- **THEN** system marks the user as active and they can log in again

### Requirement: Tenant has one admin role
Each tenant SHALL have at least one user with the Admin role. The Admin role is a system role that cannot be deleted.

#### Scenario: First user is admin
- **WHEN** the first user is created for a tenant
- **THEN** that user SHALL be assigned the Admin role

#### Scenario: Role indicator in user list
- **WHEN** user with `users.read` views user list
- **THEN** each user row displays their assigned role names as badges

### Requirement: Admin can view pending invitations
Users with `users.read` permission SHALL be able to view all pending invitations for their tenant.

#### Scenario: View pending invitations
- **WHEN** user with `users.read` views the Users page
- **THEN** system displays a section showing pending invitations with email, created date, and expiry
