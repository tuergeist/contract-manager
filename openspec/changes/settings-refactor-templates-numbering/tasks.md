## 1. New Settings Tab Components

- [ ] 1.1 Create `NumberingSettingsTabs.tsx` — sub-tabs: Invoices, Credit Notes, Offers, Order Confirmations; reuses existing `NumberSchemeSettings`, `StornoNumberSchemeSettings`, `OfferNumberSchemeSettings`, `ABNumberSchemeSettings`; adds info banner linking to Email Templates
- [ ] 1.2 Create `EmailTemplateSettingsTabs.tsx` — sub-tabs: Invoice Email, Order Confirmation Email; reuses existing `EmailTemplateSettings`, `ABEmailTemplateSettings`; adds info banner linking to Numbering
- [ ] 1.3 Rename `InvoiceSettingsTabs.tsx` to `DocumentSettingsTabs.tsx` — keep only: Company Data, PDF Template, Zugferd sub-tabs

## 2. Settings Layout Updates

- [ ] 2.1 Update `SettingsLayout.tsx` — rename "Invoices" tab to "Documents", add "Numbering" tab (icon: Hash), add "Email Templates" tab (icon: Mail)
- [ ] 2.2 Add routes: `/settings/numbering/*`, `/settings/email-templates/*`, update `/settings/invoices/*` → `/settings/documents/*`
- [ ] 2.3 Add permission checks for new tabs (reuse existing `invoices.settings` permission)

## 3. Cross-Links

- [ ] 3.1 Add info banner component `SettingsCrossLink.tsx` — small blue info box with icon and link text
- [ ] 3.2 Add cross-link in each numbering sub-tab → "Email templates are configured under Email Templates"
- [ ] 3.3 Add cross-link in each email template sub-tab → "Numbering schemes are configured under Numbering"

## 4. i18n

- [ ] 4.1 Add EN translation keys: `nav.numbering`, `nav.emailTemplates`, `nav.documents`, cross-link texts
- [ ] 4.2 Add DE translation keys for the same

## 5. Backward Compatibility

- [ ] 5.1 Keep `/settings/invoices` as redirect to `/settings/documents` for bookmarked URLs
