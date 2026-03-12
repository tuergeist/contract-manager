# Tasks: Tenant Self-Signup

## Backend

- [x] Add `SIGNUP_ENABLED` setting to Django settings (read from env, default `True`)
- [x] Create `SignupVerification` model in `apps/tenants/models.py` (tenant FK, user FK, token, email, expires_at, used, is_valid property)
- [x] Create and run migration for `SignupVerification`
- [x] Extract role-seeding logic from `setup_test_data` into a reusable `create_default_roles(tenant)` helper in `apps/tenants/models.py` (already exists as post_save signal in signals.py)
- [x] Add `signupEnabled` public query to `CoreQuery` (returns `settings.SIGNUP_ENABLED`)
- [x] Add `signUp` mutation (public, no auth): validate inputs, create inactive tenant + roles + user + verification token in transaction, send verification email
- [x] Add `verifySignup` mutation (public, no auth): validate token, activate tenant + user, mark token used, return auth tokens
- [x] Add rate limiting to `signUp` mutation (5 per email per hour, using Django cache)
- [x] Write tests for `signUp` mutation (happy path, duplicate email, disabled signup, validation errors)
- [x] Write tests for `verifySignup` mutation (happy path, expired token, used token, invalid token)

## Frontend

- [x] Add `signupEnabled` query and use it to conditionally show signup link on Login page
- [x] Create `/signup` page (`SignupPage.tsx`): form with company name, first name, last name, email, password; calls `signUp` mutation; shows success message on completion
- [x] Create `/verify-signup` page (`VerifySignup.tsx`): reads token from URL params, calls `verifySignup` mutation on mount, stores tokens and redirects to dashboard on success, shows error on failure
- [x] Add routes for `/signup` and `/verify-signup` in `App.tsx` (outside ProtectedRoute)
- [x] Add link on Login page: "Don't have an account? Sign up" (conditional on signupEnabled)
- [x] Add link on Signup page: "Already have an account? Sign in"
- [x] Add i18n keys for signup/verification pages in `en.json` and `de.json`
- [x] Add `Signup` and `Verify Signup` to `searchablePages` in `Sidebar.tsx`
