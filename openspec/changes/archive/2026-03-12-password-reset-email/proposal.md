## Why

Users who forget their password currently have no self-service recovery option. They must ask a tenant admin to manually generate and share a reset link. This creates unnecessary friction and admin overhead. With SMTP now available per-tenant, we can send reset links directly via email.

## What Changes

- Add a "Forgot Password?" link on the login page leading to an email-based reset request form
- Add an unauthenticated GraphQL mutation to request a password reset by email
- Send the existing reset token via email using the tenant's SMTP configuration (`send_notification()`)
- Upgrade the existing admin-triggered reset to also send the link via email (when SMTP is configured)
- Add rate limiting to prevent abuse of the reset endpoint

## Capabilities

### New Capabilities

_None — this builds on existing capabilities._

### Modified Capabilities

- `password-management`: Add self-service "forgot password" flow (request reset via email from login page, unauthenticated mutation, email delivery of reset link)
- `smtp-mail-service`: No requirement changes — used as-is via `send_notification()`

## Impact

- **Backend**: New unauthenticated mutation `requestPasswordReset`, new Celery task for sending reset emails, rate limiting logic
- **Frontend**: New "Forgot Password" page/form on the login flow, updated admin reset to show email confirmation
- **Dependencies**: Relies on `smtp-mail-service` (`send_notification()`), existing reset token infrastructure from `password-management`
- **Security**: Unauthenticated endpoint — must prevent email enumeration and abuse via rate limiting
