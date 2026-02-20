## 1. Backend — Template Resolution

- [x] 1.1 Add `_get_email_template(tenant, lang)` helper in `backend/apps/invoices/tasks.py` that reads from `tenant.settings.invoice_email_templates.<lang>` and falls back to `EMAIL_TEMPLATES[lang]`
- [x] 1.2 Update `send_invoice_email_task` to use `_get_email_template()` instead of directly accessing `EMAIL_TEMPLATES`
- [x] 1.3 Wrap template rendering in try/except — on `KeyError` fall back to default template and log a warning

## 2. Backend — GraphQL API

- [x] 2.1 Add `InvoiceEmailTemplate` strawberry type (language, subject, body) and `InvoiceEmailTemplatesResult` in `backend/apps/tenants/schema.py`
- [x] 2.2 Add `invoice_email_templates` query that returns current templates per language (custom if set, defaults otherwise)
- [x] 2.3 Add `SetInvoiceEmailTemplateInput` input type (language, subject, body)
- [x] 2.4 Add `set_invoice_email_template` mutation that saves to `tenant.settings.invoice_email_templates.<lang>` (or removes the key if subject and body are empty)

## 3. Backend — Tests

- [x] 3.1 Test `_get_email_template` returns custom template when configured
- [x] 3.2 Test `_get_email_template` returns default when no custom template exists
- [x] 3.3 Test fallback on invalid placeholder in custom template
- [x] 3.4 Test `set_invoice_email_template` mutation saves and clears templates
- [x] 3.5 Test `invoice_email_templates` query returns defaults and custom values

## 4. Frontend — Template Editor UI

- [x] 4.1 Add `INVOICE_EMAIL_TEMPLATES_QUERY` and `SET_INVOICE_EMAIL_TEMPLATE` mutation in `Settings.tsx`
- [x] 4.2 Add language tab selector (DE / EN) in the Email sub-tab
- [x] 4.3 Add subject input and body textarea fields bound to the selected language
- [x] 4.4 Add placeholder reference badges listing available `{placeholders}`
- [x] 4.5 Add live preview panel that renders the template with sample data
- [x] 4.6 Add "Reset to default" button that clears the custom template for the selected language
- [x] 4.7 Add save handler calling the mutation on form submit

## 5. Frontend — Translations

- [x] 5.1 Add DE and EN translation keys for template editor labels, placeholders, preview, and reset button
