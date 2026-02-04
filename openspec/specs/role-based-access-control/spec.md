## Requirements

### Requirement: Permission registry defines all grantable permissions
The system SHALL maintain a hardcoded registry of all resources and actions. Each permission is identified by a `resource.action` key (e.g., `contracts.read`, `settings.write`). The registry is the single source of truth for what permissions exist.

Resources and actions:
- `contracts`: read, write, delete
- `customers`: read, write, delete
- `products`: read, write, delete
- `users`: read, write, delete
- `settings`: read, write
- `todos`: read, write
- `notes`: read, write
- `invoices`: read, write

#### Scenario: Registry is complete
- **WHEN** a developer adds a new GraphQL resolver
- **THEN** they MUST add a corresponding permission to the registry and check it in the resolver

### Requirement: Roles store permissions as a flat map
Each Role SHALL store its permissions in a JSONField as a flat map of `"resource.action": true` entries. Only keys present with a truthy value grant access. Missing keys mean denied.

#### Scenario: Role grants specific permissions
- **WHEN** a role has `{"contracts.read": true, "contracts.write": true}`
- **THEN** users with that role can read and write contracts but cannot delete them

#### Scenario: Empty permissions deny everything
- **WHEN** a role has `{}` as its permissions
- **THEN** users with only that role are denied all actions (except login and viewing their own profile)

### Requirement: Users can hold multiple roles
The system SHALL support a many-to-many relationship between Users and Roles. A user MUST have at least one role assigned.

#### Scenario: User with multiple roles
- **WHEN** a user is assigned both "Manager" and "Viewer" roles
- **THEN** the user's effective permissions are the union of both roles' permissions

### Requirement: Effective permissions are the union of all assigned roles
The system SHALL compute a user's effective permissions by taking the union of all permission keys across all their assigned roles. If any role grants a permission, the user has it.

#### Scenario: Union of permissions
- **WHEN** Role A grants `contracts.read` and Role B grants `contracts.write`
- **AND** a user is assigned both Role A and Role B
- **THEN** the user has both `contracts.read` and `contracts.write`

### Requirement: Permission enforcement on all GraphQL resolvers
Every GraphQL query and mutation SHALL check the user's effective permissions before executing. If the user lacks the required permission, the resolver SHALL return a permission denied error.

#### Scenario: User with permission can access resource
- **WHEN** a user with `contracts.read` queries the contract list
- **THEN** the system returns the contract data

#### Scenario: User without permission is denied
- **WHEN** a user without `contracts.read` queries the contract list
- **THEN** the system returns a permission denied error

#### Scenario: Write operation requires write permission
- **WHEN** a user without `contracts.write` tries to create or update a contract
- **THEN** the system returns a permission denied error

#### Scenario: Delete operation requires delete permission
- **WHEN** a user without `contracts.delete` tries to delete a contract
- **THEN** the system returns a permission denied error

### Requirement: Super-admin bypasses all permission checks
The super-admin user (`admin@test.local`) SHALL bypass all permission checks and have full access to all resources and actions regardless of assigned roles.

#### Scenario: Super-admin access
- **WHEN** super-admin performs any action
- **THEN** the system allows it regardless of role permissions

### Requirement: Three default roles are seeded per tenant
Each tenant SHALL have three default roles created automatically: Admin, Manager, and Viewer.

**Admin** — all permissions granted.
**Manager** — all permissions except `users.*` and `settings.*`.
**Viewer** — read-only on all resources, plus `todos.write` and `notes.write`.

#### Scenario: New tenant gets default roles
- **WHEN** a new tenant is created
- **THEN** the system creates Admin, Manager, and Viewer roles with the defined default permissions

#### Scenario: Existing tenants get default roles via migration
- **WHEN** the migration runs
- **THEN** the system creates default roles for all existing tenants that don't already have them

### Requirement: Admin role is protected
The Admin role SHALL be marked as a system role. Its `users.*` and `settings.*` permissions cannot be removed. Additional permissions can be added.

#### Scenario: Cannot remove core Admin permissions
- **WHEN** an admin tries to remove `users.write` from the Admin role
- **THEN** the system rejects the change and returns an error

#### Scenario: Can add permissions to Admin role
- **WHEN** an admin adds a new permission to the Admin role
- **THEN** the system saves the change

### Requirement: Migration from is_admin to roles
The data migration SHALL convert existing users from the `is_admin` boolean to role assignments.

#### Scenario: Admin users get Admin role
- **WHEN** the migration runs for a user with `is_admin=True`
- **THEN** the user is assigned the Admin role

#### Scenario: Non-admin users get Manager role
- **WHEN** the migration runs for a user with `is_admin=False`
- **THEN** the user is assigned the Manager role

### Requirement: At least one Admin role user per tenant
The system SHALL prevent removing the Admin role from the last admin user in a tenant. Every tenant MUST have at least one user with the Admin role.

#### Scenario: Prevent removing last admin
- **WHEN** an admin tries to remove the Admin role from the only admin user
- **THEN** the system rejects the change with an error message

### Requirement: Frontend receives effective permissions
The `me` GraphQL query SHALL return the user's role names and effective permissions as flat string lists, so the frontend can conditionally render UI elements.

#### Scenario: Permissions in me query
- **WHEN** a logged-in user queries `me`
- **THEN** the response includes `roles: ["Manager"]` and `permissions: ["contracts.read", "contracts.write", ...]`

#### Scenario: Frontend hides unauthorized UI elements
- **WHEN** a user without `settings.read` views the app
- **THEN** the Settings menu item is hidden

#### Scenario: Frontend disables unauthorized actions
- **WHEN** a user without `contracts.write` views a contract
- **THEN** the Edit button is hidden or disabled
