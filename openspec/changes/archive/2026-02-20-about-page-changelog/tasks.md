## 1. Changelog Data

- [x] 1.1 Create `frontend/public/changelogs/` directory
- [x] 1.2 Create `frontend/public/changelogs/index.json` with empty array `[]`
- [x] 1.3 Create a seed changelog entry JSON file (e.g. `2026-02-18-shared-customer-picker.json`) with all fields (`version`, `date`, `title`, `description`, `type`, `details[]`)

## 2. Translation Keys

- [x] 2.1 Add `about.changelog.*` keys to `en.json`: tab label, type badges (feature, bugfix, improvement, security), empty state message
- [x] 2.2 Add matching `about.changelog.*` keys to `de.json`

## 3. Rewrite AboutPage Component

- [x] 3.1 Fix layout: replace `mx-auto max-w-4xl space-y-8 p-6` root div with bare `<div>` to match other pages
- [x] 3.2 Add Shadcn Tabs with "Changelog" (default) and "About" tabs
- [x] 3.3 Move existing version info + dependency tables into the "About" tab content
- [x] 3.4 Create Changelog tab content: fetch `changelogs.json`, store entries in state
- [x] 3.5 Render changelog entries as cards with type badge (icon + color), version + date subtitle, title, description, and details bullet list
- [x] 3.6 Add empty state for when no changelog entries exist
- [x] 3.7 Add loading state while entries are being fetched

## 4. Verification

- [x] 4.1 Run `npx tsc --noEmit` — no type errors
- [x] 4.2 Verify About page layout is left-aligned, matching other pages
- [x] 4.3 Verify Changelog tab is default and displays seed entry correctly
- [x] 4.4 Verify About tab still shows version info and dependency tables
