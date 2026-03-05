## 1. Backend: Password Reset Request Mutation

- [x] 1.1 Add `request_password_reset(email: String!) -> OperationResult` mutation to `TenantMutation` in `backend/apps/tenants/schema.py` — public (no auth required), always returns `success: true`
- [x] 1.2 Implement user lookup by email, create `PasswordResetToken` if user exists, dispatch Celery task for email
- [x] 1.3 Add rate limiting: use Django cache with key `password_reset:{email}`, 15-min TTL, max 5 requests — skip token creation and email if exceeded

## 2. Backend: Password Reset Email Task

- [x] 2.1 Create `send_password_reset_email(user_id, reset_url)` Celery task in `backend/apps/core/tasks.py`
- [x] 2.2 Implement DE/EN email templates (subject + HTML body) based on tenant language setting, include reset link and tenant name
- [x] 2.3 Call `send_notification()` from `apps/core/smtp.py` for delivery

## 3. Backend: Admin Reset Sends Email

- [x] 3.1 Modify `create_password_reset` mutation in `backend/apps/tenants/schema.py` to also dispatch `send_password_reset_email` task after creating the token (when SMTP is configured)
- [x] 3.2 Non-blocking: catch `SmtpError` so admin still gets the copyable link even if email fails

## 4. Backend: Tests

- [x] 4.1 Test `requestPasswordReset` with registered email — token created, task dispatched
- [x] 4.2 Test `requestPasswordReset` with unregistered email — returns success, no token created
- [x] 4.3 Test rate limiting — 6th request within 15 min does not create token
- [x] 4.4 Test admin reset sends email when SMTP configured
- [x] 4.5 Test admin reset works without SMTP (no email, no error)

## 5. Frontend: Forgot Password Page

- [x] 5.1 Create `frontend/src/features/auth/ForgotPassword.tsx` — email input form, "Send Reset Link" button, "Back to Login" link
- [x] 5.2 Add `REQUEST_PASSWORD_RESET` GraphQL mutation call
- [x] 5.3 Show success message after submission (regardless of whether email exists)
- [x] 5.4 Add route `/forgot-password` in `App.tsx`

## 6. Frontend: Login Page Link

- [x] 6.1 Add "Forgot Password?" link to `Login.tsx` below the password field, linking to `/forgot-password`

## 7. i18n

- [x] 7.1 Add EN translation keys: `auth.forgotPassword`, `auth.forgotPasswordTitle`, `auth.sendResetLink`, `auth.resetEmailSent`, `auth.resetEmailSentDesc`, `auth.backToLogin`
- [x] 7.2 Add DE translation keys for the same
