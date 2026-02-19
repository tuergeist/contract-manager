## 1. Backend SMTP Module

- [x] 1.1 Create `backend/apps/core/smtp.py` with `SmtpError` exception class and `_get_config(tenant)` helper that extracts and validates SMTP config from `tenant.settings.smtp`
- [x] 1.2 Implement `test_connection(tenant)` — connect, EHLO, STARTTLS if enabled, authenticate, quit; return success dict or raise `SmtpError`
- [x] 1.3 Implement `send_notification(tenant, *, to, subject, body_html)` — build MIME message, connect, send, quit; raise `SmtpError` on failure

## 2. Backend GraphQL API

- [x] 2.1 Add `SmtpSettingsType` strawberry type (host, port, username, from_address, use_tls, is_configured, password_set) to `tenants/schema.py`
- [x] 2.2 Add `smtp_settings` query to `TenantQuery` — return config with masked password
- [x] 2.3 Add `save_smtp_settings` mutation (host, port, username, password, from_address, use_tls) — requires `settings.write`, stores in `tenant.settings.smtp`
- [x] 2.4 Add `test_smtp_connection` mutation — requires `settings.write`, calls `smtp.test_connection()`
- [x] 2.5 Add `send_smtp_test_email` mutation — requires `settings.write`, sends test email to current user via `smtp.send_notification()`

## 3. Backend Tests

- [x] 3.1 Test `_get_config` — returns config when present, raises `SmtpError` when missing required fields
- [x] 3.2 Test `test_connection` — mock `smtplib.SMTP`, verify EHLO/STARTTLS/login sequence, verify error handling
- [x] 3.3 Test `send_notification` — mock `smtplib.SMTP`, verify MIME message construction, verify error propagation
- [x] 3.4 Test `save_smtp_settings` mutation — saves config to `tenant.settings.smtp`, verify permission check
- [x] 3.5 Test `smtp_settings` query — returns masked password, correct `is_configured` flag
- [x] 3.6 Test `test_smtp_connection` mutation — mock smtp module, verify success/error passthrough
- [x] 3.7 Test `send_smtp_test_email` mutation — mock smtp module, verify sends to current user's email

## 4. Frontend SMTP Settings Component

- [x] 4.1 Create `frontend/src/features/settings/SmtpSettings.tsx` — form with Host, Port, Username, Password, From Address inputs, TLS switch
- [x] 4.2 Add GraphQL query `SMTP_SETTINGS` and mutations `SAVE_SMTP_SETTINGS`, `TEST_SMTP_CONNECTION`, `SEND_SMTP_TEST_EMAIL`
- [x] 4.3 Implement Save handler — calls `save_smtp_settings` mutation, shows toast on success/error
- [x] 4.4 Implement Test Connection button — calls `test_smtp_connection`, shows inline success/error status
- [x] 4.5 Implement Send Test Email button — calls `send_smtp_test_email`, shows inline success/error status

## 5. Frontend Routing & Integration

- [x] 5.1 Add "Notifications" tab to `GeneralSettingsTabs.tsx` — new `TabsTrigger`, `TabsContent` rendering `SmtpSettings`
- [x] 5.2 Add `settings/general/notifications` route to `App.tsx`
- [x] 5.3 Add translations for SMTP settings UI in `en.json` and `de.json` (settings.smtp.* keys)

## 6. Verification

- [x] 6.1 Run `make test-back` — all tests pass
- [x] 6.2 Run `npx tsc --noEmit` — no TypeScript errors
