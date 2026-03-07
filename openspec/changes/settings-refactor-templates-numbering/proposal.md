## Why

The "Invoice Settings" tab currently holds 9 sub-tabs covering unrelated concerns: company data, PDF templates, Zugferd, email templates for invoices and order confirmations, and numbering schemes for invoices, stornos, offers, and order confirmations. This is hard to navigate and unintuitive — offer numbering has nothing to do with invoice settings.

## What Changes

- Move all numbering schemes (Invoice, Storno, Offer, AB) into a new top-level "Numbering" settings tab
- Move all email templates (Invoice Email, AB Email) into a new top-level "Email Templates" settings tab
- Invoice Settings keeps only: Company Data, PDF Template, Zugferd
- Add cross-link from email templates to numbering settings ("Configure numbering schemes →")
- No backend changes — purely frontend restructuring

## Capabilities

### New Capabilities

_None — this is a frontend-only restructuring._

### Modified Capabilities

_None — no spec-level behavior changes, only UI reorganization._

## Impact

- **Frontend**: `SettingsLayout.tsx` gets 2 new top-level tabs, `InvoiceSettingsTabs.tsx` is simplified, new `NumberingSettingsTabs.tsx` and `EmailTemplateSettingsTabs.tsx` components
- **Routes**: New `/settings/numbering/*` and `/settings/email-templates/*` routes
- **i18n**: New navigation label translations
- **Backend**: No changes
