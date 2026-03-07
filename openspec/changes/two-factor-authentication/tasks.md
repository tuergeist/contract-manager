## 1. Backend: Model & Migration

- [ ] 1.1 Add `pyotp` and `cryptography` to `requirements.txt`
- [ ] 1.2 Create `TwoFactorConfig` model in `apps/tenants/models.py` — OneToOne to User, fields: `method` (CharField choices totp/email), `totp_secret_encrypted` (TextField), `recovery_codes_hashed` (JSONField), `is_active` (BooleanField), timestamps
- [ ] 1.3 Add `encrypt_totp_secret` / `decrypt_totp_secret` helper using Fernet + `SECRET_KEY`
- [ ] 1.4 Add `generate_recovery_codes()` helper — returns 10 random 8-char alphanumeric codes and their SHA-256 hashes
- [ ] 1.5 Add `two_factor_enforced` BooleanField to `Tenant` model (default False)
- [ ] 1.6 Create migration

## 2. Backend: TOTP Setup & Verification

- [ ] 2.1 Add `setupTotp` mutation — generates TOTP secret, stores encrypted as pending (not yet active), returns `secret`, `provisioningUri` (otpauth:// URL)
- [ ] 2.2 Add `confirmTotp(code: String!)` mutation — verifies code against pending secret via `pyotp`, activates 2FA, generates and returns recovery codes (plaintext, one-time display)
- [ ] 2.3 Add `regenerateRecoveryCodes` mutation — requires password confirmation, generates new codes, replaces hashed list, returns plaintext codes

## 3. Backend: Email Code

- [ ] 3.1 Add `enableEmail2fa` mutation — checks SMTP configured, sets method=email, is_active=True
- [ ] 3.2 Create `send_2fa_email_code` Celery task in `apps/tenants/tasks.py` — generates 6-digit code, stores in cache `2fa_code:{user_id}` (5 min TTL), sends via `send_notification()`
- [ ] 3.3 Add DE/EN email templates for 2FA code

## 4. Backend: Modified Login Flow

- [ ] 4.1 Modify `login` mutation — after password check, if user has active 2FA: generate challenge JWT (5 min, type=2fa_challenge), dispatch email code if method=email, return `{ requiresTwoFactor: true, challengeToken, method }`
- [ ] 4.2 Add `verify2fa(challengeToken: String!, code: String!)` mutation — decode challenge JWT, verify code (TOTP via pyotp or email code from cache or recovery code), return access + refresh tokens
- [ ] 4.3 Add rate limiting on verify2fa — cache key `2fa_attempts:{user_id}`, max 5 per 15 min, invalidate challenge on exceed

## 5. Backend: Enforcement

- [ ] 5.1 Add `setTenant2faEnforcement(enforced: Boolean!)` mutation — requires `settings.write` permission
- [ ] 5.2 Modify `login` mutation — if tenant.two_factor_enforced and user has no 2FA: issue restricted JWT with `scope: "2fa_setup"`
- [ ] 5.3 Add middleware check in `apps/core/context.py` or `apps/tenants/middleware.py` — reject requests with `2fa_setup` scope except for 2FA setup mutations, profile query, and logout

## 6. Backend: Admin 2FA Management

- [ ] 6.1 Add `resetUser2fa(userId: ID!)` mutation — requires `users.write`, deletes TwoFactorConfig for target user
- [ ] 6.2 Add `disable2fa(password: String!)` mutation — verifies password, checks enforcement not active, deletes TwoFactorConfig
- [ ] 6.3 Expose `twoFactorMethod` and `twoFactorEnabled` fields on `UserType` in GraphQL schema

## 7. Backend: Tests

- [ ] 7.1 Test TOTP setup flow: setupTotp → confirmTotp with valid code → 2FA active
- [ ] 7.2 Test TOTP setup with invalid code — not activated
- [ ] 7.3 Test email 2FA enable — with and without SMTP
- [ ] 7.4 Test login with TOTP 2FA — returns challenge, verify2fa succeeds with valid code
- [ ] 7.5 Test login with email 2FA — returns challenge, email dispatched, verify2fa succeeds
- [ ] 7.6 Test verify2fa with expired challenge token
- [ ] 7.7 Test verify2fa rate limiting — 6th attempt rejected
- [ ] 7.8 Test recovery code login — valid code accepted and marked used, used code rejected
- [ ] 7.9 Test enforcement — login without 2FA returns restricted token
- [ ] 7.10 Test disable 2FA — with correct password, with wrong password, with enforcement active
- [ ] 7.11 Test admin reset 2FA

## 8. Frontend: Security Settings

- [ ] 8.1 Create `frontend/src/features/settings/SecuritySettings.tsx` — 2FA status display, enable TOTP/email buttons, disable button, recovery code regeneration
- [ ] 8.2 Add TOTP setup dialog — shows QR code (use `qrcode.react` or similar), code input for confirmation, recovery code display
- [ ] 8.3 Add `qrcode.react` dependency for QR rendering
- [ ] 8.4 Wire into profile/settings navigation

## 9. Frontend: Login Flow Modification

- [ ] 9.1 Create `frontend/src/features/auth/TwoFactorVerify.tsx` — code input (6 digits), recovery code option, resend button for email method
- [ ] 9.2 Modify `Login.tsx` — handle `requiresTwoFactor` response, navigate to verification step with challengeToken
- [ ] 9.3 Modify `lib/auth.tsx` — handle restricted `2fa_setup` scope, redirect to setup page

## 10. Frontend: Enforcement Setup Page

- [ ] 10.1 Create `frontend/src/features/auth/TwoFactorSetup.tsx` — forced setup when enforcement active, method selection, setup flow, redirect to app on completion
- [ ] 10.2 Add route `/setup-2fa` in `App.tsx`

## 11. Frontend: Tenant Security Settings

- [ ] 11.1 Add "Security" sub-tab to Settings page with "Require two-factor authentication" toggle
- [ ] 11.2 Add 2FA status badges to user administration list

## 12. Frontend: i18n

- [ ] 12.1 Add EN translation keys for all 2FA UI strings (setup, verify, enforce, recovery, admin)
- [ ] 12.2 Add DE translation keys for the same
