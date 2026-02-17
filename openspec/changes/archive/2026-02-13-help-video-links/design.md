## Context

The app has ~15 page routes (dashboard, customers, contracts, products, settings, banking, etc.). Users need contextual help for specific screens. The approach is lightweight: tenant admins configure video URLs per route, and a button appears on pages that have links configured.

The Tenant model already has three JSONField configs (`hubspot_config`, `time_tracking_config`, `settings`). The frontend uses a `Layout` component that wraps all authenticated routes via `<Outlet />`. Settings are organized in a tabbed layout (`SettingsLayout`) with User, General, Team, and Invoices tabs.

## Goals / Non-Goals

**Goals:**
- Allow tenant admins to configure one or more help video links per screen
- Display a green "Kurze Anleitung" button on pages that have configured links
- Support single link (direct open) and multiple links (dropdown) per screen
- Keep it simple — just external URLs opened in new tabs

**Non-Goals:**
- In-app video player or embedded videos
- Per-user customization of which links appear
- Analytics/tracking of link clicks
- Automatic route detection — admins pick from a predefined list of route keys

## Decisions

### 1. Storage: `settings` JSONField on Tenant

Store help video config in the existing `settings` JSONField on Tenant rather than creating a new model or JSONField.

Structure:
```json
{
  "help_video_links": {
    "/customers": [
      { "url": "https://screen.studio/share/abc", "label": "Kunden verwalten" }
    ],
    "/contracts/:id": [
      { "url": "https://screen.studio/share/def", "label": "Vertragsdetails" },
      { "url": "https://screen.studio/share/ghi", "label": "Positionen bearbeiten" }
    ]
  }
}
```

**Why not a separate model?** This is simple key-value config that doesn't need querying, indexing, or relational integrity. A JSONField avoids a migration for a dedicated table and matches the pattern used by `hubspot_config` and `time_tracking_config`. The `settings` field already exists for general tenant config.

**Why not a new JSONField?** The `settings` field is the generic catch-all for tenant settings. Adding another top-level field to the model would be overkill for a simple config blob.

### 2. Route Keys: Predefined List

Use a fixed list of route keys that map to the app's routes, rather than free-text input. This prevents typos and ensures the frontend can match routes reliably.

Route keys use the path patterns from App.tsx, with parameterized segments:
- `/` (Dashboard)
- `/customers` (Customer List)
- `/customers/:id` (Customer Detail)
- `/contracts` (Contract List)
- `/contracts/:id` (Contract Detail)
- `/contracts/:id/edit` (Contract Edit)
- `/products` (Product List)
- `/banking` (Banking)
- `/invoices/imported` (Imported Invoices)
- `/invoices/export` (Invoice Export)
- `/forecast` (Revenue Forecast)
- `/liquidity-forecast` (Liquidity Forecast)
- `/todos` (Todos)
- `/audit-log` (Audit Log)

The list is maintained in a shared constant (frontend only). The backend stores whatever keys it receives — it doesn't validate route keys.

### 3. GraphQL API: Query + Single Mutation

**Query**: `helpVideoLinks` — returns all configured links for the tenant as a list of `{ routeKey, links: [{ url, label }] }`. Loaded once on app init alongside other tenant settings.

**Mutation**: `updateHelpVideoLinks(input: [{ routeKey, links: [{ url, label }] }])` — replaces the entire help video config. This is simpler than add/remove/update individual entries for a config that's small and edited infrequently.

No new permissions needed — reuse existing `settings.write` permission for mutations.

### 4. Frontend: Hook + Layout Integration

**`useHelpVideoLinks()` hook**: Reads the current pathname, matches it against configured route keys (handling parameterized segments like `/customers/:id`), and returns the matching links (if any).

**`HelpVideoButton` component**: Placed in `Layout.tsx` next to the `<Outlet />`. Uses the hook to determine visibility. Renders:
- Nothing if no links for current route
- A green button "Kurze Anleitung" if one link → opens URL in new tab on click
- A green dropdown button if multiple links → shows link labels, each opens in new tab

This avoids modifying every page component. The button is positioned `fixed` or `absolute` top-right within the main content area.

### 5. Settings UI: New "Help Videos" Tab in General Settings

Add the help video configuration table inside the General settings tab (not a new top-level tab — this is a tenant-level admin setting). The UI shows:
- A table with columns: Screen (select from predefined list), Links (url + label pairs)
- Add/remove rows for screens
- Add/remove links within a screen
- Save button that calls the `updateHelpVideoLinks` mutation

## Risks / Trade-offs

- **Route matching for parameterized paths**: `/customers/:id` needs to match `/customers/123`. Simple prefix matching or a small route-matching utility handles this. Risk is low since the route list is small and fixed.
- **Settings JSONField size**: Help video config is small (a few KB at most). No risk of hitting JSON size limits.
- **No validation of URLs**: Users could enter invalid URLs. Acceptable for an admin-only feature — the button would just open a broken link. Could add basic URL validation on the frontend form.
