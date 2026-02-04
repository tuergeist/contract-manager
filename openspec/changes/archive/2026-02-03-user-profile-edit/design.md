## Context

Users are managed via the User model in `apps/tenants/models.py`. The model already has `first_name`, `last_name`, and `email` fields. User management (admin features) was recently added with invitation flow and password management.

Currently there's no way for users to edit their own profile data through the UI.

## Goals / Non-Goals

**Goals:**
- Allow users to update their own first name, last name, and email
- Validate email uniqueness within tenant
- Provide simple UI in Settings page

**Non-Goals:**
- Admin editing other users' data
- Profile pictures or avatars
- Additional profile fields

## Decisions

### 1. GraphQL Mutation
Add `updateProfile(firstName: String, lastName: String, email: String): ProfileUpdateResult` mutation.

**Rationale:** Follows existing mutation patterns. All fields optional so users can update just what they need.

### 2. Email Validation
Check email uniqueness within tenant before updating. Return error if email already exists for another user.

**Rationale:** Email is the login identifier and must be unique per tenant.

### 3. UI Location
Add profile section to existing Settings page with editable fields.

**Rationale:** Settings page already has password change. Profile editing belongs there.

### 4. Immediate Update
Changes take effect immediately. No email verification required for email changes.

**Rationale:** This is an internal tool. Simplicity over ceremony.

## Risks / Trade-offs

**[No email verification]** → User could lock themselves out with typo in email. Acceptable for internal tool; admin can fix via database if needed.
