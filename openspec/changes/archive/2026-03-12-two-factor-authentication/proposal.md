## Why

The contract manager handles sensitive business data (contracts, invoices, financial information). Password-only authentication is insufficient for protecting this data. Users need a second factor to prevent account compromise from stolen/leaked passwords. Additionally, tenants need the ability to enforce 2FA for all their users.

## What Changes

- Add two 2FA methods: TOTP (authenticator app) and email code (via existing SMTP)
- Users can enable/disable 2FA from their profile settings
- Login becomes two-step when 2FA is active: credentials first, then verification code
- Tenant admins can enforce 2FA for all users in their tenant
- Users without 2FA are forced to set it up when enforcement is enabled
- Recovery codes for TOTP method as fallback

## Capabilities

### New Capabilities

- `two-factor-authentication`: Core 2FA functionality — setup, verification, recovery, login flow modification, tenant enforcement

### Modified Capabilities

_None — the login mutation changes are scoped within the new capability._

## Impact

- **Backend**: New model for 2FA secrets/recovery codes, modified login mutation (two-step), new mutations for setup/verify/disable, Celery task for email codes, `pyotp` dependency
- **Frontend**: 2FA setup page in profile, verification step in login flow, enforcement redirect, recovery code display
- **Database**: New migration for 2FA fields/model
- **Dependencies**: `pyotp` (TOTP generation/verification), existing SMTP service for email codes
- **Security**: TOTP secrets must be stored encrypted, email codes must be short-lived (5 min), rate limiting on verification attempts
