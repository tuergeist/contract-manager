## Why

Invoice email templates are currently hardcoded in `backend/apps/invoices/tasks.py` (the `EMAIL_TEMPLATES` dict). To customize the greeting, tone, or add company-specific content (e.g. payment terms, bank details), a code change and redeployment is required. Tenants need to configure their own email subject and body per language directly from the settings UI.

## What Changes

- Add a per-tenant, per-language email template configuration stored in `tenant.settings` (JSON field)
- Provide a settings UI under the existing Email sub-tab where users can edit subject and body templates for each supported language (DE, EN)
- Templates use simple `{placeholder}` syntax with the existing placeholders: `{invoice_number}`, `{total_gross}`, `{currency}`, `{period_start}`, `{period_end}`, `{company_name}`
- The send task reads custom templates from tenant settings, falling back to the current hardcoded defaults when no custom template is configured
- Show a live preview of the rendered template using sample data so users can see formatting before saving

## Capabilities

### New Capabilities
- `invoice-email-template-settings`: Configurable per-language email templates (subject + HTML body) stored in tenant settings, with a settings UI for editing and preview

### Modified Capabilities
- `invoice-generation`: The `send_invoice_email_task` reads templates from tenant settings instead of the hardcoded `EMAIL_TEMPLATES` dict (falls back to hardcoded defaults)

## Impact

- **Backend**: `apps/invoices/tasks.py` — `send_invoice_email_task` loads templates from `tenant.settings.invoice_email_templates` with fallback to `EMAIL_TEMPLATES`
- **Backend**: `apps/tenants/schema.py` — add query to read and mutation to save email templates per language
- **Frontend**: `Settings.tsx` — add template editor under Email sub-tab with subject/body fields per language, placeholder reference, and rendered preview
- **Frontend**: Translations (`en.json`, `de.json`) — labels for template editor UI
