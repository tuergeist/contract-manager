## 1. Backend Models

- [x] 1.1 Add `is_admin` and `is_active` fields to User model in `apps/tenants/models.py`
- [x] 1.2 Create `UserInvitation` model with email, token, expires_at, status, created_by, tenant
- [x] 1.3 Create `PasswordResetToken` model with user, token, expires_at, used
- [x] 1.4 Create and run migrations
- [x] 1.5 Set `admin@test.local` as admin in migration or setup_test_data command

## 2. Backend GraphQL - User Administration

- [x] 2.1 Add `UserType` fields: isAdmin, isActive, lastLogin
- [x] 2.2 Add `users` query to list tenant users (admin only)
- [x] 2.3 Add `deactivateUser` mutation (admin only, prevent self-deactivation)
- [x] 2.4 Add `reactivateUser` mutation (admin only)

## 3. Backend GraphQL - Invitations

- [x] 3.1 Add `InvitationType` and `InvitationResult` types
- [x] 3.2 Add `pendingInvitations` query (admin only)
- [x] 3.3 Add `createInvitation` mutation with token generation and 7-day expiry
- [x] 3.4 Add `revokeInvitation` mutation (admin only)
- [x] 3.5 Add `validateInvitation` query (public, checks token validity)
- [x] 3.6 Add `acceptInvitation` mutation (public, creates user and logs in)

## 4. Backend GraphQL - Password Management

- [x] 4.1 Add `changePassword` mutation (authenticated, validates current password)
- [x] 4.2 Add `createPasswordReset` mutation (admin only, generates reset link)
- [x] 4.3 Add `validatePasswordReset` query (public, checks token validity)
- [x] 4.4 Add `resetPassword` mutation (public, sets new password)

## 5. Backend - Auth Updates

- [x] 5.1 Block login for inactive users
- [x] 5.2 Add `is_super_admin` property checking for `admin@test.local`

## 6. Frontend - Settings Users Page

- [x] 6.1 Create `/settings/users` route and `UserManagement` component
- [x] 6.2 Add users table with name, email, status, last login, admin badge
- [x] 6.3 Add deactivate/reactivate buttons with confirmation
- [x] 6.4 Add pending invitations section with copy link and revoke actions
- [x] 6.5 Add "Invite User" button and modal with email input
- [x] 6.6 Show invite link with copy button after creation
- [x] 6.7 Restrict access to admin users only

## 7. Frontend - Password Change

- [x] 7.1 Add password change form to Settings page (or profile section)
- [x] 7.2 Implement changePassword mutation with current/new password fields
- [x] 7.3 Add validation and success/error feedback

## 8. Frontend - Invitation Acceptance

- [x] 8.1 Create `/invite/:token` route and `AcceptInvitation` component
- [x] 8.2 Validate token on page load, show error if expired/invalid
- [x] 8.3 Show password setup form with confirmation field
- [x] 8.4 Call acceptInvitation mutation and redirect to dashboard on success

## 9. Frontend - Password Reset

- [x] 9.1 Create `/reset-password/:token` route and `ResetPassword` component
- [x] 9.2 Validate token on page load, show error if expired/invalid
- [x] 9.3 Show new password form with confirmation field
- [x] 9.4 Call resetPassword mutation and redirect to login on success
- [x] 9.5 Add "Reset Password" button in user management (generates link for admin to copy)

## 10. Navigation & Translations

- [x] 10.1 Add "Users" menu item under Settings (admin only)
- [x] 10.2 Add translations for user management UI (en.json, de.json)

## 11. Testing

- [x] 11.1 Add backend tests for invitation flow
- [x] 11.2 Add backend tests for password change/reset
- [x] 11.3 Add backend tests for user deactivation blocking login
