## Context

Settings are organized as top-level tabs in `SettingsLayout.tsx`:
- User (profile, password, 2FA, notifications, dashboard, language)
- General (contracts, help videos, performance, revenue goals, security)
- Integrations (HubSpot, SMTP, etc.)
- Team (user management, roles)
- Invoices (9 sub-tabs — the problem)
- Banking

The "Invoices" tab has grown into a catch-all:
1. Company Data
2. Invoice Numbering
3. Storno Numbering
4. Offer Numbering
5. PDF Template
6. Invoice Email Template
7. AB Numbering
8. AB Email Template
9. Zugferd

## Goals / Non-Goals

**Goals:**
- Group all numbering schemes in one place
- Group all email templates in one place
- Cross-link between them ("numbering is configured under Numbering →")
- Keep Invoice Settings focused on invoice-specific config

**Non-Goals:**
- Changing any backend logic or APIs
- Making email templates editable for transactional emails (password reset, 2FA) — those stay hardcoded for now
- Changing numbering logic itself

## Decisions

### 1. New top-level tabs structure

```
Settings
├── User (unchanged)
├── General (unchanged)
├── Integrations (unchanged)
├── Team (unchanged)
├── Documents
│   ├── Company Data
│   ├── PDF Template
│   └── Zugferd
├── Numbering
│   ├── Invoices
│   ├── Stornos (Credit Notes)
│   ├── Offers
│   └── Order Confirmations
├── Email Templates
│   ├── Invoice Email
│   └── Order Confirmation Email
└── Banking (unchanged)
```

**Rationale:** "Invoices" → "Documents" because it contains company data and PDF template settings that apply to all document types (invoices, offers, ABs all use the same company data and template styling). "Numbering" and "Email Templates" become siblings at the top level since they span multiple document types.

**Alternative considered:** Keeping "Invoices" and just pulling out numbering/templates — but the remaining content (Company Data, PDF Template) isn't invoice-specific either.

### 2. Cross-links
Each email template tab shows a small info banner: "Numbering schemes are configured under [Numbering →](/settings/numbering)". Each numbering tab shows: "Email templates are configured under [Email Templates →](/settings/email-templates)".

### 3. Reuse existing components
All existing settings components (`NumberSchemeSettings`, `EmailTemplateSettings`, etc.) stay as-is with `showHeader={false}`. Only the container layout changes.

## Risks / Trade-offs

- [Risk] Users familiar with old layout can't find settings → Mitigation: logical grouping is more intuitive, and settings count doesn't change
- [Risk] Bookmarked URLs break → Mitigation: old `/settings/invoices/numbering` could redirect, but low risk since settings aren't typically bookmarked
