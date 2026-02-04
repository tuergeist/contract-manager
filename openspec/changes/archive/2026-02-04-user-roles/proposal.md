## Why

The app currently has only a binary `is_admin` flag — users are either full admins or have no restrictions at all. There's no way to give someone read-only access, or to let a contract manager work without touching tenant settings. As the user base grows, we need granular, tenant-customizable role-based access control (RBAC).

## What Changes

- Introduce RBAC with a permission model covering all major resources and actions
- Ship 3 default roles: **Admin**, **Manager**, **Viewer** — created automatically for each tenant
- Allow admins to customize permissions on each role (add/remove granular permissions)
- Users can have one or more roles; effective permissions are the union of all assigned roles
- Enforce permissions in every GraphQL resolver (queries and mutations)
- Add a role/permission management UI in Settings (admin only)
- Show user roles in the user administration list and assignment UI
- The existing `is_admin` field becomes redundant — replaced by the Admin role. Migration path: existing admins get the Admin role, non-admins get the Manager role.

**Default role permissions:**

| Resource | Action | Admin | Manager | Viewer |
|----------|--------|-------|---------|--------|
| contracts | read | ✓ | ✓ | ✓ |
| contracts | write | ✓ | ✓ | ✗ |
| contracts | delete | ✓ | ✓ | ✗ |
| customers | read | ✓ | ✓ | ✓ |
| customers | write | ✓ | ✓ | ✗ |
| customers | delete | ✓ | ✓ | ✗ |
| products | read | ✓ | ✓ | ✓ |
| products | write | ✓ | ✓ | ✗ |
| products | delete | ✓ | ✓ | ✗ |
| users | read | ✓ | ✗ | ✗ |
| users | write | ✓ | ✗ | ✗ |
| users | delete | ✓ | ✗ | ✗ |
| settings | read | ✓ | ✗ | ✗ |
| settings | write | ✓ | ✗ | ✗ |
| todos | read | ✓ | ✓ | ✓ |
| todos | write | ✓ | ✓ | ✓ |
| notes | read | ✓ | ✓ | ✓ |
| notes | write | ✓ | ✓ | ✓ |
| invoices | read | ✓ | ✓ | ✓ |
| invoices | write | ✓ | ✓ | ✗ |

## Capabilities

### New Capabilities
- `role-based-access-control`: Core RBAC engine — Role model refactor (M2M user↔role), permission registry, permission checking helpers, default role seeding, migration from `is_admin`
- `role-management-ui`: Admin UI in Settings to view/edit roles and their permissions, assign roles to users

### Modified Capabilities
- `user-administration`: User list shows roles instead of admin badge; role assignment replaces `is_admin` toggle; invitation includes role selection
- `user-invitation`: Invitations assign one or more roles to the new user (default: Manager)

## Impact

- **Backend models**: Refactor `Role` model — change `User.role` FK to M2M, add permission registry with known resources/actions, seed default roles in migration
- **Backend permissions**: New `has_permission(user, resource, action)` helper used in all schema resolvers; replaces `is_admin` checks
- **GraphQL schema**: All queries/mutations get permission checks; new role/permission queries and mutations for admin UI
- **Frontend**: Settings gets role management section; user admin gets role assignment; UI elements conditionally hidden based on user permissions (via `me` query returning effective permissions)
- **Migration**: Data migration to convert `is_admin=True` → Admin role, `is_admin=False` → Manager role; deprecate `is_admin` field
