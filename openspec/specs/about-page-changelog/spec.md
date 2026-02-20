## Requirements

### Requirement: About page uses standard left-aligned layout
The About page SHALL use the same layout pattern as other pages — a bare `<div>` root element without `mx-auto`, `max-w-4xl`, or extra `p-6` padding. Content SHALL be left-aligned and full-width within Layout's `<main>`.

#### Scenario: Layout matches other pages
- **WHEN** user navigates to the About page
- **THEN** the page content is left-aligned and stretches the full available width, matching the layout of CustomerList, ContractList, and other pages

### Requirement: About page has tabbed navigation
The About page SHALL display two tabs: "Changelog" and "About". The "Changelog" tab SHALL be selected by default. Tabs SHALL use the Shadcn `Tabs` component.

#### Scenario: Default tab is Changelog
- **WHEN** user navigates to the About page
- **THEN** the "Changelog" tab is active and its content is displayed

#### Scenario: Switching to About tab
- **WHEN** user clicks the "About" tab
- **THEN** the version info and dependency tables are displayed (existing About page content)

### Requirement: Changelog tab displays entries from static JSON files
The Changelog tab SHALL fetch `changelogs/index.json` to discover entry filenames, then fetch each entry JSON file. Entries SHALL be displayed in reverse-chronological order as cards.

#### Scenario: Entries load and render
- **WHEN** the Changelog tab is active and `changelogs/index.json` contains entry filenames
- **THEN** the system fetches each referenced JSON file and displays entries as cards in the order listed in the index

#### Scenario: Empty changelog
- **WHEN** `changelogs/index.json` is an empty array or fails to load
- **THEN** a "No changelog entries" empty state is displayed

### Requirement: Changelog entry JSON schema
Each changelog entry JSON file SHALL contain: `version` (string), `date` (ISO date string), `title` (string), `description` (string), `type` (one of `"feature"`, `"bugfix"`, `"improvement"`, `"security"`), and `details` (array of strings, may be empty).

#### Scenario: Valid entry file
- **WHEN** a JSON file in `changelogs/` contains all required fields with valid types
- **THEN** the entry renders as a card with all fields displayed

#### Scenario: Entry with empty details
- **WHEN** a changelog entry has `details: []`
- **THEN** the card renders without a bullet list section

### Requirement: Changelog entry card layout
Each entry card SHALL display: a colored type badge (top area), version and formatted date as subtitle, title as heading, description as body text, and details as a bulleted list.

#### Scenario: Feature entry rendering
- **WHEN** an entry has `type: "feature"`
- **THEN** the badge is green and shows "Feature" with a Sparkles icon

#### Scenario: Bugfix entry rendering
- **WHEN** an entry has `type: "bugfix"`
- **THEN** the badge is red and shows "Bugfix" with a Bug icon

#### Scenario: Improvement entry rendering
- **WHEN** an entry has `type: "improvement"`
- **THEN** the badge is blue and shows "Improvement" with a Zap icon

#### Scenario: Security entry rendering
- **WHEN** an entry has `type: "security"`
- **THEN** the badge is orange and shows "Security" with a Shield icon

### Requirement: Changelog index file
A file at `frontend/public/changelogs/index.json` SHALL contain a JSON array of entry filenames in reverse-chronological order. The frontend SHALL use this file to discover which entries to fetch.

#### Scenario: Index references multiple entries
- **WHEN** `index.json` contains `["2026-02-18-feature.json", "2026-02-15-fix.json"]`
- **THEN** the system fetches both files from `changelogs/` and displays them in that order

### Requirement: Translation keys for changelog UI
The changelog UI elements (tab labels, type badges, empty state) SHALL use i18n translation keys under `about.changelog.*` in both `en.json` and `de.json`.

#### Scenario: German locale
- **WHEN** the app language is set to German
- **THEN** tab labels, type badge text, and empty state messages display in German
