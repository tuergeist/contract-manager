## Context

The contract manager uses JWT-based authentication (custom, not Django sessions). Login is a single `login(email, password)` mutation returning access + refresh tokens. SMTP is available per-tenant for transactional emails. No 2FA exists currently.

Key existing infrastructure:
- `apps/core/auth.py` — JWT creation/verification (`create_access_token`, `create_refresh_token`, `decode_token`)
- `apps/core/smtp.py` — `send_notification(tenant, to, subject, body_html)`
- `apps/tenants/models.py` — `User`, `Tenant` models
- `apps/tenants/schema.py` — `login` mutation, user management mutations
- Django cache (Redis) for rate limiting
- Celery for async tasks

## Goals / Non-Goals

**Goals:**
- Two 2FA methods: TOTP (authenticator app) and email code
- Seamless two-step login flow via GraphQL
- Tenant-level enforcement with forced setup redirect
- Recovery codes for TOTP users
- Admin 2FA management (reset, enforcement)

**Non-Goals:**
- SMS-based 2FA (no SMS provider)
- Hardware key / WebAuthn / FIDO2 (future consideration)
- Per-user enforcement policies (tenant-wide only)
- Remember device / trusted device cookies (future consideration)

## Decisions

### 1. New `TwoFactorConfig` model (not fields on User)
Separate model linked to User via OneToOne. Stores: `method` (totp/email), `totp_secret` (encrypted), `recovery_codes` (JSONField, hashed), `is_active`, timestamps.

**Rationale:** Keeps User model clean, easy to reset (delete the config), and recovery codes need their own storage. Encrypted TOTP secret via Django's `Fernet` (using `SECRET_KEY`).

**Alternative considered:** Fields directly on User — rejected because it clutters the model and makes reset harder.

### 2. Challenge token for two-step login
Modified login flow:
1. `login(email, password)` — if 2FA active, returns `{ requiresTwoFactor: true, challengeToken: "...", method: "totp"|"email" }` instead of JWT tokens
2. `verify2fa(challengeToken, code)` — validates code, returns JWT tokens

Challenge token is a short-lived JWT (5 min, type="2fa_challenge") containing `user_id` and `method`. Not usable as an access token.

**Rationale:** Stateless (no server-side session for the challenge), consistent with existing JWT approach.

**Alternative considered:** Server-side challenge stored in cache/DB — adds state management complexity, JWT is simpler.

### 3. Email codes via Celery task
New `send_2fa_email_code` Celery task. Code is 6-digit numeric, stored in Django cache with key `2fa_code:{user_id}` and 5-min TTL. Single-use (deleted after successful verification).

**Rationale:** Cache-based codes are simple, auto-expire, no migration needed. Celery keeps the login mutation fast.

### 4. TOTP via `pyotp` library
Standard TOTP implementation. 30-second window, 1 window tolerance (accepts current and previous code). QR code generated as `otpauth://` URI — frontend renders via a QR library.

**Rationale:** `pyotp` is the standard Python TOTP library, well-maintained, minimal footprint.

### 5. Recovery codes: hashed storage
10 codes, 8 characters each (alphanumeric). Stored as hashed values (SHA-256). Shown to user only once at creation. Each code can only be used once (removed from list after use).

**Rationale:** Hashing prevents exposure if DB is compromised. Same pattern as password storage but simpler (no salt needed for random codes).

### 6. Enforcement: restricted JWT with `scope` claim
When tenant enforces 2FA and user has none, the login mutation returns a JWT with `scope: "2fa_setup"`. Frontend checks this scope and redirects to setup. Backend middleware rejects all requests with this scope except 2FA setup mutations and user profile queries.

**Rationale:** Keeps the flow stateless. Frontend and backend both enforce the restriction.

### 7. Frontend: new SecuritySettings component + login flow modification
- `SecuritySettings.tsx` in profile — 2FA setup/disable, recovery codes
- `TwoFactorVerify.tsx` — verification step shown after login when `requiresTwoFactor` is true
- `TwoFactorSetup.tsx` — forced setup page when enforcement active
- Tenant settings: toggle in existing settings page under new "Security" sub-tab

## Risks / Trade-offs

- [Risk] TOTP secret encryption uses `SECRET_KEY` — if key rotates, all TOTP secrets break → Mitigation: document that key rotation requires 2FA re-enrollment, or use a dedicated encryption key
- [Risk] Email code delivery depends on SMTP — if email is slow, UX suffers → Mitigation: show "code sent" message with option to resend after 30 seconds
- [Risk] Enforcement could lock out users who can't set up 2FA → Mitigation: admin can always reset 2FA, and enforcement allows login to reach the setup page
- [Risk] Cache (Redis) loss means active email codes and rate limits reset → Acceptable: worst case user needs to re-request a code
