## Context

Currently the sidebar has invoice-related settings scattered as individual top-level items:
- `/settings/company-data`
- `/settings/invoice-numbering`
- `/settings/invoice-template`
- `/invoices/export`

This creates clutter and makes navigation confusing. The permissions system only has `invoices.read/write` which doesn't allow fine-grained control over who can configure templates vs export invoices.

## Goals / Non-Goals

**Goals:**
- Clean, organized Settings page with tabbed navigation
- Remove invoice config items from top-level sidebar
- Granular permissions for invoice operations
- Fix broken logo upload in template settings

**Non-Goals:**
- Changing invoice generation logic
- Adding new invoice features beyond organization
- Changing the invoice export workflow itself

## Decisions

### 1. Settings Page Layout: Tabbed Interface

Use Shadcn Tabs component within `/settings` route:
- **General** tab: Existing general settings
- **Users** tab: User management (permission: `users.read`)
- **Invoices** tab: Sub-tabs for Company Data, Numbering, Template (permission: `invoices.settings`)

**Rationale:** Tabs keep related settings grouped while maintaining a single Settings entry point in sidebar.

### 2. New Permission Structure

Replace `invoices.write` with granular permissions:
```
invoices.read      - View invoices
invoices.export    - Export/download invoices
invoices.generate  - Create/finalize invoices
invoices.settings  - Configure template, numbering, company data
```

**Rationale:** Allows Manager role to export without changing settings. Admins control configuration.

### 3. Sidebar Simplification

Remove from sidebar:
- `/settings/company-data`
- `/settings/invoice-numbering`
- `/settings/invoice-template`

Keep:
- `/settings` (entry point with tabs)
- `/invoices/export` (stays as workflow entry, permission: `invoices.export`)

**Rationale:** Export is a workflow action, not a setting. Configuration belongs in Settings.

### 4. Logo Upload Fix

Investigate and fix the broken logo save. Likely causes:
- File upload mutation not being called
- Media path misconfiguration
- Missing form submission

## Risks / Trade-offs

**[Breaking permission change]** → Existing `invoices.write` splits into multiple permissions. Migration script needed to map old permission to new ones for existing roles.

**[Route changes]** → Invoice settings routes change. Old routes should redirect or 404 cleanly since they're internal.
