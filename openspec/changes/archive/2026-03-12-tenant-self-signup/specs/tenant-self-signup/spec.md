# Tenant Self-Signup

## Overview

Public self-service flow allowing anyone to create a new tenant and become its first admin user. Includes email verification before the account becomes active.

## Requirements

### Feature Toggle

- `SIGNUP_ENABLED` Django setting controlled by environment variable (default: `True`)
- When disabled, the `signUp` mutation returns an error
- Frontend hides the signup link on the login page when signup is disabled
- A `signupEnabled` GraphQL query (public, no auth) exposes the toggle to the frontend

### Signup Form

- Public page at `/signup`, accessible without authentication
- Required fields: company name, first name, last name, email, password
- Password minimum 8 characters (same rule as existing flows)
- Email must not already be registered (unique constraint on User.email)
- Link from login page: "Don't have an account? Sign up"
- Link from signup page back to login: "Already have an account? Sign in"

### Signup Backend (`signUp` mutation)

- Public mutation (no authentication required)
- Validates all fields (company name non-empty, email format, password length, email uniqueness)
- Creates in one transaction:
  - `Tenant` with `name=companyName`, `is_active=False`
  - Three default roles: Admin (all permissions), Manager, Viewer (same as `setup_test_data`)
  - `User` with provided details, `is_active=False`, assigned Admin role
  - `SignupVerification` token (secure random, 24h expiry)
- Sends verification email with link: `{base_url}/verify-signup?token={token}`
- Returns `{ success: true }` on success, `{ success: false, error: "..." }` on failure
- Rate limited: max 5 signups per email per hour (prevent spam)

### SignupVerification Model

- Fields: `tenant` (FK), `user` (FK), `token` (unique, 64-char `secrets.token_urlsafe`), `email`, `expires_at` (24h), `used` (boolean)
- `is_valid` property: not used and not expired

### Email Verification (`verifySignup` mutation)

- Public mutation (no authentication required)
- Accepts `token` and optional `baseUrl` for redirect
- Validates: token exists, is valid (not used, not expired)
- On success:
  - Sets `tenant.is_active = True`
  - Sets `user.is_active = True`
  - Marks token as `used = True`
  - Returns auth tokens (access + refresh) for auto-login
- On failure: returns error message (invalid/expired token)

### Verification Page

- Frontend page at `/verify-signup` (outside `ProtectedRoute`)
- Reads `token` from URL query params
- Calls `verifySignup` mutation on mount
- On success: stores tokens, redirects to dashboard
- On failure: shows error with link to signup page

### Email Content

- Subject: "Verify your account" / "Bestätige dein Konto"
- Body: Welcome message + verification link + expiry notice (24h)
- Uses the same email transport as existing 2FA and invitation emails

### Security

- Signup mutation rate limited per email address
- Verification tokens are single-use
- Inactive tenants/users cannot log in (existing `is_active` checks in login)
- No sensitive data exposed in error messages (don't reveal if email exists — use generic "signup failed" for duplicate emails)

### Edge Cases

- Duplicate email: return generic error "Unable to create account. Please try again or sign in."
- Expired token: show "This verification link has expired. Please sign up again."
- Already-used token: show "This link has already been used. Please sign in."
- Signup disabled: mutation returns error, frontend shows no signup link
