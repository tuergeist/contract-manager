## Why

New customers currently can't onboard themselves — a developer or admin must manually create tenants via Django ORM or management commands. A self-service signup flow lets prospective customers create their own tenant and admin account, removing onboarding friction and enabling growth without manual intervention.

## What Changes

- Public signup page where a user provides company name, their name, email, and password
- Backend mutation to create a new tenant with default roles, and the first admin user in one step
- Email verification to confirm the signup email before activating the tenant
- Post-signup redirect to login (or auto-login)
- Optional: admin-configurable flag to enable/disable public signups (environment variable or Django setting)

## Capabilities

### New Capabilities
- `tenant-self-signup`: Public signup flow that creates a new tenant and its first admin user, including email verification

### Modified Capabilities
_(none — existing invitation and auth flows remain unchanged)_

## Impact

- **Backend**: New public GraphQL mutation (`signUp`), email verification token model, email sending for verification
- **Frontend**: New `/signup` route and page, link from login page
- **Models**: New `SignupVerification` model (or reuse token pattern from `UserInvitation`/`PasswordResetToken`)
- **Settings**: Environment variable or Django setting to toggle public signups on/off
- **Security**: Rate limiting on signup endpoint to prevent abuse; email verification prevents fake tenants
