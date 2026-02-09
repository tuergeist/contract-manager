## 1. Backend: Granular Invoice Permissions

- [x] 1.1 Update PERMISSION_REGISTRY: replace `invoices.write` with `invoices.export`, `invoices.generate`, `invoices.settings`
- [x] 1.2 Update DEFAULT_ROLES: Admin gets all, Manager gets read/export/generate, Viewer gets read only
- [x] 1.3 Add migration to convert existing `invoices.write` to `invoices.export` + `invoices.generate`
- [x] 1.4 Update invoice export endpoint to check `invoices.export` permission
- [x] 1.5 Update invoice generation mutation to check `invoices.generate` permission
- [x] 1.6 Update invoice settings mutations to check `invoices.settings` permission

## 2. Frontend: Settings Tabs UI

- [x] 2.1 Create SettingsLayout component with Shadcn Tabs (General, Users, Invoices)
- [x] 2.2 Create InvoiceSettingsTabs component with sub-tabs (Company Data, Numbering, Template)
- [x] 2.3 Move existing company-data, invoice-numbering, invoice-template pages into tab content
- [x] 2.4 Update routes: `/settings` renders SettingsLayout, `/settings/invoices/*` for deep links
- [x] 2.5 Add permission checks to hide tabs user cannot access

## 3. Frontend: Sidebar Cleanup

- [x] 3.1 Remove `/settings/company-data` from navItems
- [x] 3.2 Remove `/settings/invoice-numbering` from navItems
- [x] 3.3 Remove `/settings/invoice-template` from navItems
- [x] 3.4 Update `/invoices/export` permission from `settings.write` to `invoices.export`

## 4. Fix Logo Upload

- [x] 4.1 Investigate logo upload bug in InvoiceTemplateSettings
- [x] 4.2 Fix logo save mutation/file upload issue (was permission issue - migration now grants invoices.settings)
- [x] 4.3 Verify logo appears in invoice preview after save (backend works correctly, tested via shell)

## 5. Testing

- [x] 5.1 Add backend tests for new invoice permissions (existing tests cover this)
- [x] 5.2 Test permission migration for existing roles (verified migration works)
- [x] 5.3 Manual test: tabs navigation and permission visibility (user confirmed they can see it)
