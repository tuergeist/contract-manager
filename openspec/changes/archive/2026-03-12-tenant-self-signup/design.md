## Context

Tenants are currently created only via the `setup_test_data` management command or direct ORM access. Users join existing tenants through admin-created invitations (`UserInvitation` model). There is no public-facing way to create a new tenant.

The existing patterns to reuse:
- `UserInvitation` / `PasswordResetToken` for token-based verification flows
- `setup_test_data` for the tenant + default roles + admin user creation sequence
- `accept_invitation` mutation as a model for public (unauthenticated) mutations

## Goals / Non-Goals

**Goals:**
- Public signup: anyone can create a new tenant and become its admin
- Email verification before the tenant becomes usable
- Reuse existing patterns (Role seeding, JWT auth, token models)
- Feature toggle to enable/disable public signups

**Non-Goals:**
- Billing/subscription integration (future concern)
- Custom domain or branding per tenant at signup
- Multi-step onboarding wizard (just create and go)
- Social login / SSO (separate feature)
- Captcha or advanced bot protection (rate limiting is sufficient for now)

## Decisions

### 1. Signup creates tenant immediately, but inactive until email verified

**Choice**: Create the `Tenant` with `is_active=False` and the `User` with `is_active=False` on signup. After email verification, set both to active.

**Why**: Reuses the existing `is_active` flag that already blocks login. No new "pending" state needed. If verification never happens, inactive tenants can be cleaned up by a periodic task.

**Alternative considered**: Store signup data in a temporary model and only create tenant on verification. Rejected — adds complexity and a new model for transient state.

### 2. New `SignupVerification` model for email tokens

**Choice**: New model similar to `PasswordResetToken` — stores token, email, tenant reference, expiry (24h).

**Why**: Clean separation from `UserInvitation` (different purpose). Simple: token + expiry + used flag.

**Alternative considered**: Reuse `UserInvitation`. Rejected — invitations are scoped to existing tenants and have role_ids, status semantics that don't fit signup.

### 3. Two public mutations: `signUp` and `verifySignup`

- `signUp(companyName, email, firstName, lastName, password)` → creates inactive tenant + user + verification token, sends email. Returns success/error.
- `verifySignup(token)` → activates tenant + user, returns auth tokens (auto-login).

**Why**: Matches the existing `accept_invitation` pattern. Auto-login on verification reduces friction (user doesn't need to remember password immediately after signup).

### 4. Feature toggle via Django setting

**Choice**: `SIGNUP_ENABLED` environment variable (default: `True`). Checked in the `signUp` mutation — returns error if disabled. Deployments that want to disable public signup set `SIGNUP_ENABLED=false`.

**Why**: Simple on/off. No DB-level config needed. Default-on so self-hosted deployments work out of the box.

### 5. Default roles seeded on tenant creation

**Choice**: Reuse the same 3-role seeding logic from `setup_test_data` (Admin, Manager, Viewer). The signup user gets the Admin role.

**Why**: Consistent with existing tenants. The signup user needs full permissions to configure their new tenant.

### 6. Frontend: `/signup` page linked from login

**Choice**: Simple form page at `/signup` (outside `ProtectedRoute`). Link on login page: "Don't have an account? Sign up". Verification page at `/verify-signup?token=...` that auto-redirects.

**Why**: Standard SaaS pattern. Minimal pages needed.

## Risks / Trade-offs

- **Abuse / spam signups** → Rate limit the `signUp` mutation (e.g., 5 per IP per hour via Django middleware or decorator). Inactive tenants older than 48h can be purged by a management command.
- **Email deliverability** → Verification emails use the same transport as 2FA codes and invitation emails. If that's not configured, signup silently fails. Mitigation: `signUp` mutation checks email backend is configured before proceeding.
- **Orphaned inactive tenants** → Add a cleanup management command or Celery task to delete unverified signups after 48h. Not critical for v1 — can be manual initially.
- **No duplicate tenant names** → Not enforced. Multiple tenants can have the same company name (they're isolated). This matches existing behavior.
