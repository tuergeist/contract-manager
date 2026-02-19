## Context

The About page (`frontend/src/features/about/AboutPage.tsx`) currently shows version info and dependency tables in a centered, width-capped layout. Every other page in the app is left-aligned and full-width inside Layout's `<main className="p-6">`. There is no changelog anywhere in the app.

heykurt uses YAML files + a backend service, but our case is simpler: static JSON files served directly, no backend involvement.

## Goals / Non-Goals

**Goals:**
- Fix layout to match other pages (left-aligned, no `mx-auto max-w-4xl`)
- Add tabbed UI: "Changelog" (default tab) and "About" (existing content)
- Load changelog entries from static JSON files in `frontend/public/changelogs/`
- Display entries as cards with type badge, version, date, title, description, details

**Non-Goals:**
- No "What's New" modal or unseen-entry tracking (heykurt has this, we don't need it)
- No backend API for changelog — purely static files
- No changelog entry management UI — files are hand-created by developers
- No notification dot in navigation

## Decisions

### 1. Static JSON files in `frontend/public/changelogs/`

Each release gets a file like `2026-02-18-customer-picker-dialog.json`:

```json
{
  "version": "1.8.0",
  "date": "2026-02-18",
  "title": "Shared Customer Picker",
  "description": "Extracted a shared customer picker dialog used across contracts and invoices.",
  "type": "improvement",
  "details": [
    "Consistent search UI with debounced input",
    "Customer cards show name, CUS-ID, and city"
  ]
}
```

**Why JSON over YAML**: The frontend can `fetch()` JSON natively. No parser library needed. Developers already write JSON (locale files, package.json). YAML would require adding `js-yaml` as a dependency.

**Why individual files over one big file**: Easier to manage in PRs — adding a release is adding a file, no merge conflicts on a shared array. Same pattern as heykurt.

### 2. Index file for discovery

A `frontend/public/changelogs/index.json` file lists all entry filenames in reverse-chronological order:

```json
["2026-02-18-customer-picker-dialog.json", "2026-02-15-price-increase.json"]
```

**Why**: The browser can't list directory contents. An index avoids needing a backend endpoint. Developers update this file when adding an entry (one line addition at the top of the array).

### 3. Tabs using Shadcn Tabs component

Use `@/components/ui/tabs` (Tabs, TabsList, TabsTrigger, TabsContent) — already in the project. "Changelog" is the default tab since it's the more frequently useful view.

### 4. Changelog card design

Each entry renders as a card (`rounded-lg border bg-white p-6`) with:
- **Type badge** (top-right): colored Badge component — green for feature, red for bugfix, blue for improvement, orange for security
- **Version + date** (subtitle line): `v1.8.0 · Feb 18, 2026`
- **Title**: bold heading
- **Description**: paragraph text
- **Details**: bulleted list (if non-empty)

This matches heykurt's pattern closely while using our existing Shadcn components.

### 5. Type icons from lucide-react

- `feature` → Sparkles (green)
- `bugfix` → Bug (red)
- `improvement` → Zap (blue)
- `security` → Shield (orange)

## Risks / Trade-offs

- **Manual index maintenance**: Developers must update `index.json` when adding entries → low risk, it's one line, and forgetting just means the entry doesn't show up (not a crash)
- **No pagination**: All entries load at once → acceptable for a changelog that grows by ~2-4 entries per month. Can add pagination later if needed
- **No i18n for changelog content**: Entries are written in one language (English or German depending on team preference) → acceptable for an internal tool
