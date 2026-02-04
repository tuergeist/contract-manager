## 1. Model & Migration

- [x] 1.1 Add `is_system` BooleanField to Role model (default False)
- [x] 1.2 Change `User.role` FK to `User.roles` M2M (add new field, keep old FK temporarily)
- [x] 1.3 Add `PERMISSION_REGISTRY` and `DEFAULT_ROLES` constants to `apps/core/permissions.py`
- [x] 1.4 Add `effective_permissions` cached_property and `has_perm_check(resource, action)` method to User model
- [x] 1.5 Write schema migration for model changes (M2M table, `is_system` field)
- [x] 1.6 Write data migration: create 3 default roles per tenant, assign Admin role to `is_admin=True` users, Manager role to `is_admin=False` users
- [x] 1.7 Add `post_save` signal on Tenant to seed default roles for new tenants

## 2. Permission Enforcement (Backend)

- [x] 2.1 Add `require_perm(info, resource, action)` helper to `apps/core/permissions.py`
- [x] 2.2 Prefetch `roles` on user in GraphQL context (`apps/core/auth.py`)
- [x] 2.3 Replace all `is_admin`/`is_super_admin` checks in `tenants/schema.py` with permission checks (`users.read`, `users.write`)
- [x] 2.4 Add permission checks to `contracts/schema.py` resolvers (queries: `contracts.read`, mutations: `contracts.write`)
- [x] 2.5 Add permission checks to `customers/schema.py` resolvers
- [x] 2.6 Add permission checks to `products/schema.py` resolvers
- [x] 2.7 Add permission checks to invoice/todo/note resolvers

## 3. GraphQL Schema (Roles & Permissions)

- [x] 3.1 Add `RoleType` strawberry type and `roles` query (list roles for tenant, requires `settings.read`)
- [x] 3.2 Add `permissionRegistry` query returning all resources and actions
- [x] 3.3 Add `updateRolePermissions` mutation (update permissions JSON, enforce Admin role protection)
- [x] 3.4 Add `createRole` mutation (name + permissions, validates unique name per tenant)
- [x] 3.5 Add `deleteRole` mutation (non-system only, no assigned users)
- [x] 3.6 Add `assignUserRoles` mutation (set roles for a user, prevent removing last Admin, requires `users.write`)
- [x] 3.7 Extend `me` query to return `roles: [String]` and `permissions: [String]` (effective permission keys)
- [x] 3.8 Extend `UserType` to expose assigned role names

## 4. Invitation Role Assignment (Backend)

- [x] 4.1 Add `role_ids` JSONField (list of role IDs) to `UserInvitation` model + migration
- [x] 4.2 Update `createInvitation` mutation to accept optional role IDs (default: Manager role)
- [x] 4.3 Update invitation acceptance to assign stored roles to the new user

## 5. Frontend: Auth & Permission Gating

- [x] 5.1 Update `me` query in `auth.tsx` to fetch `roles` and `permissions` fields
- [x] 5.2 Add `hasPermission(resource, action)` helper to auth context
- [x] 5.3 Update Sidebar to use `hasPermission("users", "read")` instead of `isAdmin` for user management visibility
- [x] 5.4 Gate contract write/delete actions behind `contracts.write`/`contracts.delete` (backend enforced)
- [x] 5.5 Gate customer write/delete actions behind `customers.write`/`customers.delete` (backend enforced)
- [x] 5.6 Gate product write/delete actions behind `products.write`/`products.delete` (backend enforced)

## 6. Frontend: Role Management UI

- [x] 6.1 Add Roles section to Settings page with list of roles (name, user count, system badge)
- [x] 6.2 Build permission matrix component (resources × actions checkbox grid)
- [x] 6.3 Add role edit dialog with permission matrix, save calls `updateRolePermissions`
- [x] 6.4 Add create role dialog (name + permission matrix)
- [x] 6.5 Add delete role button (disabled for system roles and roles with users)

## 7. Frontend: User Administration Updates

- [x] 7.1 Replace admin badge with role name badges in user list
- [x] 7.2 Add role assignment UI to user list (toggle roles per user)
- [x] 7.3 Update invitation dialog to include role selection (default: Manager) — backend stores role_ids
- [x] 7.4 Update `UserManagement.tsx` to use `hasPermission("users", "read")` instead of `isAdmin`

## 8. Translations

- [x] 8.1 Add English translations for roles UI (`settings.roles.*`)
- [x] 8.2 Add German translations for roles UI

## 9. Tests

- [x] 9.1 Backend tests: permission enforcement (user with/without permission, super-admin bypass)
- [x] 9.2 Backend tests: role CRUD (create, update permissions, delete, system role protection)
- [x] 9.3 Backend tests: data migration (is_admin users get Admin role, others get Manager)
- [x] 9.4 Backend tests: invitation with role assignment
- [x] 9.5 Backend tests: last-admin protection (cannot remove Admin role from last admin)
- [x] 9.6 Frontend build verification (`npm run build` passes)
