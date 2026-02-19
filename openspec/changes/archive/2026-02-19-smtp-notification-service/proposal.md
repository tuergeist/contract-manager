## Why

The app currently has no way to send internal notifications to tenant users (e.g. sync failures, task assignments, system alerts). The only email channel is M365 Graph API, which is tied to customer-facing invoice delivery and requires Azure AD setup — too heavyweight for simple transactional notifications. An SMTP-based mail service using Scaleway Transactional Email provides a lightweight, independent channel for app-to-user notifications.

## What Changes

- Add an SMTP mail service configuration stored in `tenant.settings` (host, port, username, password, from address, TLS toggle)
- Add a settings UI under a new "Notifications" sub-tab in General settings for configuring SMTP credentials
- Add a "Send Test Email" button that sends a test message to the current user via SMTP
- Provide a backend `send_notification(tenant, to, subject, body_html)` function that sends via SMTP using tenant config
- The SMTP service is independent from M365 — M365 remains the channel for invoice emails, SMTP is for internal notifications

## Capabilities

### New Capabilities
- `smtp-mail-service`: SMTP-based transactional email service with per-tenant configuration, connection testing, and a `send_notification` API for internal use

### Modified Capabilities
_(none — M365 invoice email sending is unchanged)_

## Impact

- **Backend**: New `apps/core/smtp.py` — SMTP send function, connection test, configuration helper
- **Backend**: `apps/tenants/schema.py` — query for SMTP settings, mutation to save config, mutation to send test email
- **Frontend**: `GeneralSettingsTabs.tsx` — add "Notifications" sub-tab
- **Frontend**: New component for SMTP configuration form with test button
- **Frontend**: Translations (en.json, de.json)
- **Routing**: `App.tsx` — add `settings/general/notifications` route
- **Dependencies**: None new — Django's `django.core.mail` with SMTP backend, or direct `smtplib`
