## Requirements

### Requirement: Admin can view all roles
The Settings page SHALL display a Roles section listing all roles in the tenant with their names and number of assigned users.

#### Scenario: View roles list
- **WHEN** an admin navigates to Settings > Roles
- **THEN** the system displays all roles with name, user count, and a "system" badge for protected roles

#### Scenario: Non-admin cannot access roles management
- **WHEN** a user without `settings.read` permission tries to access Settings > Roles
- **THEN** the system denies access

### Requirement: Admin can view and edit role permissions
The system SHALL display a permission matrix for each role, showing resources as rows and actions as columns with checkboxes.

#### Scenario: View permission matrix
- **WHEN** admin selects a role
- **THEN** the system displays a checkbox grid with all resources and actions, checked where the role grants the permission

#### Scenario: Grant a permission
- **WHEN** admin checks an unchecked permission checkbox and saves
- **THEN** the system adds that permission to the role

#### Scenario: Revoke a permission
- **WHEN** admin unchecks a checked permission checkbox and saves
- **THEN** the system removes that permission from the role

#### Scenario: Protected permissions are not removable
- **WHEN** admin views the Admin role's permission matrix
- **THEN** the `users.*` and `settings.*` checkboxes are checked and disabled (cannot be unchecked)

### Requirement: Admin can create custom roles
The system SHALL allow admins to create new roles with a name and selected permissions.

#### Scenario: Create new role
- **WHEN** admin clicks "Create Role", enters a name, selects permissions, and saves
- **THEN** the system creates the role and it appears in the roles list

#### Scenario: Duplicate role name rejected
- **WHEN** admin tries to create a role with a name that already exists in the tenant
- **THEN** the system displays an error

### Requirement: Admin can delete non-system roles
The system SHALL allow admins to delete custom (non-system) roles, but only if no users are currently assigned to them.

#### Scenario: Delete unused custom role
- **WHEN** admin deletes a custom role with no assigned users
- **THEN** the system removes the role

#### Scenario: Cannot delete role with assigned users
- **WHEN** admin tries to delete a role that has users assigned
- **THEN** the system displays an error indicating the role is in use

#### Scenario: Cannot delete system roles
- **WHEN** admin tries to delete the Admin, Manager, or Viewer role
- **THEN** the system rejects the deletion

### Requirement: Admin can assign roles to users
The user management UI SHALL allow admins to assign one or more roles to each user.

#### Scenario: Assign role to user
- **WHEN** admin selects roles for a user and saves
- **THEN** the system updates the user's role assignments

#### Scenario: User must have at least one role
- **WHEN** admin tries to remove all roles from a user
- **THEN** the system rejects the change with an error

#### Scenario: View user roles in user list
- **WHEN** admin views the user list
- **THEN** each user row shows their assigned role names
