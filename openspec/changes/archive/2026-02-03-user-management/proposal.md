## Why

The application currently has no user management capabilities. All users have equal access with no administrative controls. We need to enable company admins to manage their team members - inviting new users, and allowing users to change their own passwords for security.

## What Changes

- Add user management UI for company admins to view and manage team members
- Implement user invitation system (admin creates invite, copies link to share via Teams/Slack/etc)
- Add password change functionality for all users
- Designate `admin@test.local` as super-admin with full access
- Introduce admin role per tenant (one company admin who can invite others)

## Capabilities

### New Capabilities

- `user-invitation`: Admin can invite new users to the tenant. Generates an invite link that admin can copy to share via Teams/Slack/etc. Optional email sending. Invited users use the link to set their password and activate their account.
- `password-management`: Users can change their own password. Admins can trigger password reset for other users.
- `user-administration`: Admin UI to list tenant users, view their status, and manage access (deactivate/reactivate users).

### Modified Capabilities

_(none - no existing specs are being modified)_

## Impact

- **Backend**:
  - `apps/tenants/models.py`: Add `is_admin` field to User, invitation model
  - `apps/tenants/schema.py`: New mutations for invite, password change, user management
  - _(Email sending optional - invite link can be copied and shared manually)_
- **Frontend**:
  - New Settings > Users page for admin
  - Password change in user profile/settings
  - Invitation acceptance flow
- **Database**: New migrations for user fields and invitation table
