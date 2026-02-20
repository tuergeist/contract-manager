## Why

The About page uses a centered, narrow layout (`max-w-4xl mx-auto`) that looks inconsistent with every other page in the app (left-aligned, full-width). There is also no way for users to see what changed between releases — no changelog exists.

## What Changes

- **Fix About page layout**: Remove centering and width cap to match the standard page pattern (bare `<div>` inside Layout's padded `<main>`)
- **Add tabbed navigation**: Restructure the About page with tabs — "Changelog" (default) and "About" (version info + dependencies, the current content)
- **Add Changelog tab**: Display a reverse-chronological list of release entries with version, date, type badge, title, description, and detail bullets
- **Changelog data as JSON files**: Each release is a JSON file in `frontend/public/changelogs/` (e.g. `2026-02-18-customer-picker-dialog.json`). No backend needed — static files served by Vite/nginx
- **Entry schema**: `{ version, date, title, description, type: "feature"|"bugfix"|"improvement"|"security", details: string[] }` — inspired by heykurt's pattern but using JSON instead of YAML since the frontend can fetch them directly

## Capabilities

### New Capabilities
- `about-page-changelog`: Tabbed About page with changelog entries loaded from static JSON files

### Modified Capabilities
_(none — no existing specs are affected)_

## Impact

- **Frontend only** — no backend changes
- `frontend/src/features/about/AboutPage.tsx` — rewrite with tabs + changelog rendering
- `frontend/public/changelogs/` — new directory for JSON changelog entries
- `frontend/src/locales/{en,de}.json` — new translation keys for changelog tab and entry types
- No API changes, no migrations, no breaking changes
