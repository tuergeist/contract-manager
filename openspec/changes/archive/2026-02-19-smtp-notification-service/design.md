## Context

The app uses M365 Graph API for customer-facing invoice emails, configured per-tenant in `tenant.settings.m365`. This is tightly coupled to Azure AD and overkill for internal transactional notifications (sync failures, task reminders, alerts). We need a lightweight SMTP channel using Scaleway Transactional Email that's fully independent from M365.

Existing patterns to follow:
- **M365 module** (`apps/core/m365.py`): config from `tenant.settings`, `_get_config()` helper, exception class, `test_connection()` + `send_mail()` functions
- **Settings storage**: `tenant.settings` JSONField on the Tenant model (already holds `m365`, `invoice_email_templates`, `activation_required_fields`, `help_video_links`)
- **Settings UI**: General settings uses sub-tabs via `GeneralSettingsTabs.tsx`, each rendering a section of `Settings.tsx` (or a standalone component)
- **GraphQL**: Queries return typed result objects, mutations use `require_perm`/`check_perm`, credentials are never returned in full

## Goals / Non-Goals

**Goals:**
- Per-tenant SMTP configuration (host, port, username, password, from address, TLS)
- Connection test (verify SMTP handshake without sending)
- Send test email to current user
- Reusable `send_notification()` function for internal use by other features
- Settings UI under General > Notifications

**Non-Goals:**
- Email templates or notification preferences (future work)
- Replacing M365 for invoice emails
- Queue-based email sending (direct synchronous send is fine for now)
- Notification types, scheduling, or batching

## Decisions

### 1. Python `smtplib` directly (not Django mail backend)

Use `smtplib` directly in `apps/core/smtp.py`, mirroring the pattern from `m365.py`.

**Why not Django `django.core.mail`?** Django's mail backend is a global setting, not per-tenant. We'd need to override the backend per-call or create a custom backend class. Direct `smtplib` is simpler, explicit, and consistent with how `m365.py` uses `httpx` directly rather than a framework abstraction.

**Alternative considered:** Django `EmailMessage` with custom connection — viable but adds abstraction without benefit for a single function.

### 2. Config stored in `tenant.settings.smtp`

```python
tenant.settings = {
    "smtp": {
        "host": "smtp-relay.brevo.com",
        "port": 587,
        "username": "user@example.com",
        "password": "secret",
        "from_address": "noreply@company.com",
        "use_tls": True
    },
    # ... existing m365, invoice_email_templates, etc.
}
```

Follows the same pattern as `tenant.settings.m365`. Password stored alongside other credentials in the JSONField — consistent with existing `client_secret` storage.

### 3. Connection test = SMTP handshake only

`test_connection(tenant)` will:
1. Connect to host:port
2. Send EHLO
3. STARTTLS if configured
4. Authenticate with username/password
5. Quit without sending

This verifies credentials and connectivity without side effects. Separate from `send_test_email()` which actually delivers a message.

### 4. Standalone `SmtpSettings.tsx` component

Create `frontend/src/features/settings/SmtpSettings.tsx` as a standalone component (like `EmailTemplateSettings.tsx`), rendered in a new "Notifications" tab in `GeneralSettingsTabs.tsx`.

UI elements:
- Host, Port, Username, Password (masked), From Address inputs
- TLS toggle (Switch)
- "Test Connection" button — tests SMTP handshake
- "Send Test Email" button — sends actual email to current user
- "Save" button
- Status indicators for connection test and test email results

### 5. GraphQL API surface

**Query:**
- `smtp_settings` → `SmtpSettings` type (returns config with masked password, `is_configured` flag)

**Mutations:**
- `save_smtp_settings(input)` → `OperationResult` — saves config, requires `settings.write`
- `test_smtp_connection` → `OperationResult` — tests SMTP handshake, requires `settings.write`
- `send_smtp_test_email` → `OperationResult` — sends test email to current user, requires `settings.write`

Reuse existing `OperationResult` type for all mutations (matches M365 pattern).

### 6. `send_notification()` API

```python
def send_notification(tenant, *, to: list[str], subject: str, body_html: str) -> None:
    """Send a notification email via SMTP. Raises SmtpError on failure."""
```

Synchronous, raises on error. Callers (future: Celery tasks for sync failures, etc.) handle errors. No queue — keeps it simple for now.

## Risks / Trade-offs

- **Password in JSONField** — same approach as M365 `client_secret`. Not ideal (not encrypted at rest beyond DB-level encryption), but consistent. → Mitigation: mask in API responses, only settings.write can update.
- **Synchronous sending** — `send_notification()` blocks the caller. → Mitigation: acceptable for admin-triggered test emails and low-volume notifications. Future: wrap in Celery task if volume grows.
- **No connection pooling** — each `send_notification()` opens a new SMTP connection. → Mitigation: fine for low-volume transactional emails. Scaleway handles the throughput.
