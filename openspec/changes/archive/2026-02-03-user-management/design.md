## Context

The application uses Django with Strawberry GraphQL and a React frontend. Authentication already exists with JWT tokens stored in localStorage. The multi-tenant architecture isolates data per tenant via `TenantModel` base class.

Currently all users are created manually in the database. There's no UI for user management, no invitation flow, and no self-service password changes.

## Goals / Non-Goals

**Goals:**
- Enable tenant admins to invite new users via shareable links
- Allow users to change their own passwords
- Allow admins to trigger password resets for their users
- Provide admin UI to manage tenant users (list, deactivate, reactivate)
- Designate `admin@test.local` as super-admin

**Non-Goals:**
- Email delivery (links are copied manually via Teams/Slack)
- Role-based permissions beyond admin/non-admin
- User profile editing (name, avatar, etc.)
- Self-service password reset (forgot password flow)

## Decisions

### 1. Invitation Model
Store invitations in a new `UserInvitation` model with fields: `email`, `token` (UUID), `expires_at`, `status` (pending/used/revoked), `created_by`, `tenant`.

**Rationale**: Separate model keeps invitation logic isolated and allows tracking invitation history.

### 2. Token Generation
Use Python's `secrets.token_urlsafe(32)` for invite and reset tokens.

**Rationale**: Cryptographically secure, URL-safe, sufficient entropy.

### 3. Invite Link Format
`/invite/{token}` - Frontend route that validates token and shows account setup form.

**Rationale**: Simple, stateless URL. Token lookup happens on page load.

### 4. Password Reset Link Format
`/reset-password/{token}` - Frontend route for password reset form.

**Rationale**: Consistent with invite flow pattern.

### 5. Admin Flag on User Model
Add `is_admin` boolean field to existing `User` model (default: False).

**Rationale**: Simple approach for single-admin-per-tenant. No need for full RBAC.

### 6. Super-Admin Check
Check `user.email == 'admin@test.local'` for super-admin privileges.

**Rationale**: Hardcoded for now; can be moved to env var or separate flag later.

### 7. Frontend Route Structure
- `/settings/users` - Admin user management page
- `/settings/profile` - User's own profile with password change
- `/invite/:token` - Public invitation acceptance
- `/reset-password/:token` - Public password reset

**Rationale**: Settings section for authenticated features, public routes for token flows.

### 8. GraphQL Mutations
```
createInvitation(email: String!): InvitationResult
revokeInvitation(invitationId: ID!): OperationResult
acceptInvitation(token: String!, password: String!): AuthResult
changePassword(currentPassword: String!, newPassword: String!): OperationResult
createPasswordReset(userId: ID!): ResetLinkResult
resetPassword(token: String!, newPassword: String!): OperationResult
deactivateUser(userId: ID!): OperationResult
reactivateUser(userId: ID!): OperationResult
```

**Rationale**: Follows existing mutation patterns in the codebase.

## Risks / Trade-offs

**[No email delivery]** → Users must manually share invite links. Acceptable for internal tool with small teams.

**[Single admin per tenant]** → Cannot delegate admin tasks. Sufficient for current scope; can extend later.

**[Hardcoded super-admin email]** → Tight coupling. Move to settings/env var if needed.

**[Token expiry not enforced server-side on page load]** → Token could be validated on form load but expired by submission. Mitigation: Check expiry at both load and submission.
