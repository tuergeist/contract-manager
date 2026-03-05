## Context

The contract manager already has:
- `PasswordResetToken` model with `create_token()`, `is_valid`, `is_expired` (24h expiry)
- `createPasswordReset` mutation (admin-only, requires `users.write`) — generates token, returns URL
- `resetPassword` mutation (public) — validates token, sets new password
- `ResetPassword.tsx` frontend page at `/reset-password/:token`
- `send_notification()` in `apps/core/smtp.py` — sends HTML email via tenant SMTP config
- i18n with `en.json` / `de.json` locales

What's missing: a self-service flow where unauthenticated users enter their email to receive a reset link.

## Goals / Non-Goals

**Goals:**
- Self-service "forgot password" flow from the login page
- Email delivery of reset links using existing SMTP infrastructure
- Admin reset also sends email (when SMTP available)
- Rate limiting to prevent abuse

**Non-Goals:**
- Changing the existing reset token model or expiry (24h stays)
- CAPTCHA or advanced bot prevention (rate limiting is sufficient for now)
- Password strength requirements beyond the existing 8-char minimum

## Decisions

### 1. New public mutation `requestPasswordReset(email: String!)`
Reuses `PasswordResetToken.create_token()`. Looks up user by email, creates token, dispatches Celery task for email delivery. Always returns `{ success: true }` to prevent enumeration.

**Alternative considered:** Django's built-in password reset — rejected because we use Strawberry GraphQL + JWT, not Django sessions/views.

### 2. Rate limiting via Django cache
Store a counter in Django's cache (Redis) keyed by `password_reset:{email}` with 15-minute TTL. Increment on each request; skip email send if count > 5. No extra model needed.

**Alternative considered:** Database counter on User model — unnecessary persistence, cache is simpler and auto-expires.

### 3. Email via Celery task
Create `send_password_reset_email` task in `apps/core/tasks.py` (or alongside existing notification tasks). Uses `send_notification()` directly. Keeps mutation fast.

### 4. Frontend: New `ForgotPassword.tsx` page at `/forgot-password`
Simple form with email input. Link from Login page. Shares styling with existing auth pages.

### 5. Admin reset email: modify `create_password_reset` mutation
After creating the token and building the URL, attempt to send the email via Celery task. Failure is non-blocking (admin still gets the copyable link).

### 6. Email templates: inline HTML in the Celery task
Two templates (DE/EN) based on tenant language setting (`tenant.settings.language` or default "de"). Matches the pattern in `notifications.py`.

## Risks / Trade-offs

- [Risk] SMTP misconfigured → user gets no email, no feedback → Mitigation: self-service form shows generic message explaining to contact admin if no email arrives
- [Risk] Rate limiting via cache loses state on Redis restart → Acceptable: worst case is a few extra emails
- [Risk] Tenant language lookup needs to work for unauthenticated context → Mitigation: look up tenant from user's tenant FK
