## Context

Invoice emails are sent via the `send_invoice_email_task` Celery task in `backend/apps/invoices/tasks.py`. It uses a hardcoded `EMAIL_TEMPLATES` dict with DE and EN variants containing subject and HTML body with `{placeholder}` formatting. Templates are rendered with Python `str.format()` using values from the `InvoiceRecord`.

Tenant-specific configuration is already stored in `tenant.settings` (a JSONField), with established patterns for M365 (`settings.m365`) and HubSpot (`settings.hubspot_config`). The frontend Settings page already has an "Email" sub-tab where M365 configuration lives.

## Goals / Non-Goals

**Goals:**
- Allow tenants to customize invoice email subject and body per language (DE, EN)
- Store templates in `tenant.settings` alongside existing config
- Provide a UI with placeholder reference and live preview
- Fall back to current hardcoded defaults when no custom template is set
- Keep the existing `{placeholder}` syntax — no new template engine

**Non-Goals:**
- Rich text / WYSIWYG editor — plain HTML textarea is sufficient
- Per-customer template overrides
- Attachments beyond the invoice PDF
- Template versioning or history
- Additional languages beyond DE and EN

## Decisions

### 1. Storage: `tenant.settings.invoice_email_templates`

Store templates in the existing `tenant.settings` JSONField under a new key:

```json
{
  "invoice_email_templates": {
    "de": {
      "subject": "Rechnung {invoice_number}",
      "body": "<p>Sehr geehrte Damen und Herren, ...</p>"
    },
    "en": {
      "subject": "Invoice {invoice_number}",
      "body": "<p>Dear Sir or Madam, ...</p>"
    }
  }
}
```

**Rationale**: No migration needed. Consistent with how M365 and HubSpot config are stored. A missing key or empty value means "use default".

**Alternative considered**: Dedicated Django model — rejected because it adds a migration and table for what is essentially two strings per language, and all other tenant config already uses the JSON approach.

### 2. Template rendering: keep `str.format()`

The current `EMAIL_TEMPLATES` already use Python `str.format()` with named placeholders. Custom templates will use the same mechanism.

**Rationale**: Zero new dependencies. The placeholder set is fixed and small (6 values). Users see `{invoice_number}` in the UI which is intuitive.

**Alternative considered**: Jinja2 — rejected as overkill for simple variable substitution with no conditionals or loops needed.

### 3. Backend: helper function with fallback

Extract a `_get_email_template(tenant, lang)` function in `tasks.py` that:
1. Reads `tenant.settings.get("invoice_email_templates", {}).get(lang, {})`
2. Returns custom subject/body if both are non-empty
3. Falls back to `EMAIL_TEMPLATES[lang]` otherwise

**Rationale**: Single point of template resolution. The task code changes minimally — just replaces `template = EMAIL_TEMPLATES[lang]` with `template = _get_email_template(tenant, lang)`.

### 4. GraphQL: query + mutation on tenant schema

- `invoiceEmailTemplates` query: returns the current templates per language (or defaults if unset)
- `setInvoiceEmailTemplate` mutation: saves subject + body for a given language

Both go on `apps/tenants/schema.py` since they operate on `tenant.settings`.

### 5. Frontend: textarea editor with preview

Add to the Email sub-tab in Settings:
- Language selector (tab or toggle: DE / EN)
- Subject input field
- Body textarea (HTML)
- Available placeholders listed as reference badges
- "Preview" panel rendering the template with sample data
- "Reset to default" button per language

**Rationale**: Matches the existing settings UI patterns. A textarea for HTML is appropriate since the templates are simple and short.

## Risks / Trade-offs

- **Broken placeholders** — User could mistype `{invoce_number}` causing a KeyError at send time.
  → Mitigation: Wrap `str.format()` in a try/except in the task; on failure, log the error and fall back to the default template for that send. Also validate in the frontend preview (show error if a placeholder is unrecognized).

- **HTML injection** — Templates are tenant-admin authored HTML sent to billing contacts.
  → Acceptable risk: tenant admins are trusted internal users. The email body is already HTML in the current hardcoded templates.

- **No undo** — Overwriting a template has no history.
  → Acceptable: "Reset to default" covers the main recovery case. Template versioning is a non-goal.
