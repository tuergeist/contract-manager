## Context

The app has a `Role` model with a `permissions` JSONField and a `User.role` FK, but neither is enforced — all authorization uses a binary `is_admin` flag. There are ~8 `is_admin`/`is_super_admin` checks in backend resolvers and ~5 references in the frontend. The `is_super_admin` property is hardcoded to `admin@test.local`.

The existing `Role` model (tenant-scoped, `name` + `permissions` JSON + `is_default`) is a good foundation but needs: M2M instead of FK, a well-defined permission structure, enforcement in resolvers, and a management UI.

## Goals / Non-Goals

**Goals:**
- Enforce granular permissions on every GraphQL resolver
- Ship 3 default roles (Admin, Manager, Viewer) that work out of the box
- Let admins customize role permissions and create additional roles
- Users can hold multiple roles; effective permissions = union
- Migrate existing users from `is_admin` to role-based system without disruption
- Frontend hides/disables UI elements the user cannot use

**Non-Goals:**
- Object-level permissions (e.g., "can only edit contracts they created") — all permissions are resource-level
- Permission inheritance / role hierarchies — flat union model only
- Removing the `is_super_admin` escape hatch (stays for support access)
- Audit logging of permission changes (can be added later)
- API rate limiting or IP-based access control

## Decisions

### 1. Permission structure: `{"resource.action": true}` flat map

**Chosen:** Flat map with dot-notation keys. A role's `permissions` JSONField stores:
```json
{
  "contracts.read": true,
  "contracts.write": true,
  "contracts.delete": true,
  "customers.read": true,
  "settings.read": true,
  "settings.write": true
}
```

Only truthy keys grant access. Missing keys = denied.

**Alternatives considered:**
- Nested dict `{"contracts": ["read", "write"]}` — current structure in test data. Harder to query, merge, and diff. The flat map is simpler to union across multiple roles (`any(role.permissions.get(key) for role in roles)`).
- Django's built-in `Permission` + `Group` system — too heavyweight, designed for Django admin, doesn't map well to Strawberry-GraphQL resolvers, and would duplicate the tenant-scoped Role model.

### 2. User↔Role: M2M relationship

**Chosen:** Replace `User.role` FK with `User.roles` M2M through a join table.

```python
class User(AbstractUser):
    roles = models.ManyToManyField(Role, blank=True, related_name="users")
```

Effective permissions = union of all assigned roles' permission maps. Cached on the user object per request via a `@cached_property`.

**Alternatives considered:**
- Keep FK and add a separate "secondary roles" field — needlessly complex.
- Store permissions directly on User — defeats the purpose of reusable roles.

### 3. Permission checking: `has_perm()` method on User + `require_perm()` helper

**Chosen:** Add a `has_perm_check(resource, action)` method to User that checks the union of all role permissions. Add a `require_perm(info, resource, action)` helper in `permissions.py` that raises `PermissionError` if denied.

```python
# In User model
@cached_property
def effective_permissions(self) -> set[str]:
    perms = set()
    for role in self.roles.all():
        for key, granted in (role.permissions or {}).items():
            if granted:
                perms.add(key)
    return perms

def has_perm_check(self, resource: str, action: str) -> bool:
    if self.is_super_admin:
        return True
    return f"{resource}.{action}" in self.effective_permissions

# In permissions.py
def require_perm(info, resource: str, action: str):
    user = get_current_user(info)
    if not user.has_perm_check(resource, action):
        raise PermissionError(f"Permission denied: {resource}.{action}")
    return user
```

Every resolver replaces `if not user.is_admin` with `require_perm(info, "resource", "action")`.

**Why `has_perm_check` not `has_perm`:** Django's `AbstractUser` already defines `has_perm()` for the built-in permission system. Using a different name avoids collision.

### 4. Permission registry: hardcoded constant, not database

**Chosen:** A `PERMISSION_REGISTRY` dict in `permissions.py` defines all known resources and actions. This is the source of truth for:
- Validating role permission edits (can't grant unknown permissions)
- Rendering the permission matrix in the admin UI
- Documenting what permissions exist

```python
PERMISSION_REGISTRY = {
    "contracts": ["read", "write", "delete"],
    "customers": ["read", "write", "delete"],
    "products": ["read", "write", "delete"],
    "users": ["read", "write", "delete"],
    "settings": ["read", "write"],
    "todos": ["read", "write"],
    "notes": ["read", "write"],
    "invoices": ["read", "write"],
}
```

**Alternatives considered:**
- Database-driven permission definitions — over-engineered for this scale. New permissions require code changes (new resolvers) anyway, so the registry should live in code.

### 5. Default roles: seeded via data migration

**Chosen:** A data migration creates the 3 default roles for every existing tenant and assigns them. A `post_save` signal on Tenant creates default roles for new tenants.

The Admin role gets a special `is_system` flag (renamed from `is_default`) so it cannot be deleted or have its core permissions removed. Users can still add permissions to it.

**Default role definitions** live in a constant `DEFAULT_ROLES` used by both the migration and the signal:

```python
DEFAULT_ROLES = {
    "Admin": {perm: True for resource, actions in PERMISSION_REGISTRY.items() for perm in [f"{resource}.{a}" for a in actions]},
    "Manager": {/* all except users.*, settings.* */},
    "Viewer": {"contracts.read": True, "customers.read": True, "products.read": True, "todos.read": True, "todos.write": True, "notes.read": True, "notes.write": True, "invoices.read": True},
}
```

### 6. Migration from `is_admin`: two-step migration

**Step 1** (schema migration): Add M2M `roles` field, add `is_system` field to Role, keep `is_admin` and `role` FK temporarily.

**Step 2** (data migration):
- For each tenant, create 3 default roles (or update existing ones)
- Users with `is_admin=True` → assign Admin role
- Users with `is_admin=False` → assign Manager role (not Viewer, to avoid breaking existing users)
- Mark `is_admin` and `role` FK as deprecated (remove in a future migration)

**Why not remove `is_admin` immediately:** Safer rollback. The field stays but is no longer checked in resolvers. Can be removed in a follow-up cleanup.

### 7. Frontend permission model: `me` query returns flat permission set

**Chosen:** Extend the `me` query to return `permissions: [String!]!` — the user's effective permission keys (e.g., `["contracts.read", "contracts.write", ...]`). The frontend stores these in auth context and uses a `hasPermission(resource, action)` helper to conditionally render UI.

```typescript
// In auth context
const hasPermission = (resource: string, action: string): boolean => {
  return user?.permissions?.includes(`${resource}.${action}`) ?? false
}
```

This avoids sending the full role structure to the frontend and keeps the permission check simple.

### 8. Role management UI: permission matrix in Settings

The admin UI shows a table with resources as rows and actions as columns. Each cell is a checkbox. Roles are tabs or a sidebar list. The Admin role's system permissions are shown as disabled checkboxes (can't be removed).

Admins can also create new custom roles and delete non-system roles (only if no users are assigned).

## Risks / Trade-offs

**[Performance] Multiple roles require extra DB queries** → Mitigated by `prefetch_related("roles")` on user queries and `@cached_property` for `effective_permissions`. The permission set is small (< 50 keys) so union computation is negligible.

**[Migration] Existing non-admin users get Manager role which may be too permissive** → Acceptable because non-admins currently have unrestricted access to everything except user management. Manager role actually reduces their access (no settings). Communicate in release notes.

**[Complexity] Customized roles may diverge from defaults after updates** → When new permissions are added to `PERMISSION_REGISTRY` in future code changes, they won't automatically appear on existing roles. The migration for the new permission should add it to the Admin role's system defaults. Other roles require manual admin action.

**[Lock-out risk] Admin removes their own Admin role** → Prevent in the mutation: cannot remove the last Admin-role assignment from yourself. At least one user must have the Admin role per tenant.

## Open Questions

- Should we add a `dashboard.read` permission or is the dashboard always visible to all authenticated users? (Leaning: always visible, it's the landing page.)
- Should the Viewer role see the revenue forecast? (Leaning: yes, it's read-only financial data.)
