## Why

Invoice-related settings (company data, numbering, template) are scattered as separate top-level sidebar items, making navigation confusing. Additionally, the logo upload in template settings is broken, and invoice permissions are too coarse-grained (only `invoices.read/write`) for proper access control.

## What Changes

- **Fix logo saving bug** in invoice template settings
- **Reorganize Settings UI** with tabbed interface grouping related settings
- **Move invoice settings** under Settings section instead of top-level sidebar
- **Add granular invoice permissions**: separate permissions for template, numbering, export, and generation
- **Update sidebar** to show cleaner hierarchy with Settings as expandable/collapsible section

## Capabilities

### New Capabilities
- `settings-tabs-ui`: Tabbed settings interface grouping Users, Invoice Config (company data, numbering, template), and other settings
- `invoice-permissions`: Granular RBAC permissions for invoice-related actions (template, numbering, export, generate)

### Modified Capabilities
None - these are UI reorganization and new permission additions

## Impact

- **Frontend**: Sidebar component, Settings routes, new tabbed Settings layout
- **Backend**: PERMISSION_REGISTRY additions for granular invoice permissions
- **RBAC**: Default role definitions need updating for new permissions
- **Routes**: Invoice settings routes move under `/settings/invoices/*`
