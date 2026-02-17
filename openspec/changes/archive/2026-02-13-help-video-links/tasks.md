## 1. Backend: GraphQL Query & Mutation

- [x] 1.1 Add `HelpVideoLinkType` and `HelpVideoLinksEntryType` strawberry types (url: str, label: Optional[str], routeKey: str, links: list)
- [x] 1.2 Add `helpVideoLinks` query that reads `tenant.settings.get("help_video_links", {})` and returns list of entries
- [x] 1.3 Add `HelpVideoLinkInput` and `UpdateHelpVideoLinksInput` strawberry input types
- [x] 1.4 Add `updateHelpVideoLinks` mutation — requires `settings.write` permission, replaces `settings["help_video_links"]` and saves tenant
- [x] 1.5 Add backend tests for query (empty config, populated config) and mutation (add links, clear links, permission check)

## 2. Frontend: Route Keys Constant & Hook

- [x] 2.1 Create `ROUTE_KEYS` constant mapping route patterns to human-readable labels (e.g. `{ key: "/customers", label: "Customers" }`)
- [x] 2.2 Create `useHelpVideoLinks` hook — queries `helpVideoLinks`, matches current `pathname` against route keys (handling parameterized segments like `/customers/:id`), returns matching links array
- [x] 2.3 Add `helpVideoLinks` GraphQL query and `updateHelpVideoLinks` mutation definitions in frontend

## 3. Frontend: HelpVideoButton Component

- [x] 3.1 Create `HelpVideoButton` component — green button labeled "Kurze Anleitung", positioned top-right in content area
- [x] 3.2 Single link: clicking the button opens URL in new tab via `window.open`
- [x] 3.3 Multiple links: button opens a dropdown (DropdownMenu) showing each link's label, clicking a label opens that URL in new tab
- [x] 3.4 Integrate `HelpVideoButton` into `Layout.tsx` alongside `<Outlet />`

## 4. Frontend: Settings UI

- [x] 4.1 Create `HelpVideoSettings` component — table showing configured screen/links mappings with add/remove controls
- [x] 4.2 Screen selector: dropdown from `ROUTE_KEYS` constant, filtering out already-configured keys
- [x] 4.3 Link inputs: URL field (required) + label field (optional) per link, with add/remove link buttons per screen row
- [x] 4.4 Save button calls `updateHelpVideoLinks` mutation with the full config
- [x] 4.5 Integrate `HelpVideoSettings` into the General settings tab in `Settings.tsx`

## 5. i18n & Polish

- [x] 5.1 Add translation keys for "Kurze Anleitung", route labels, settings section title, and button/placeholder text in de.json and en.json
- [x] 5.2 Verify button positioning doesn't overlap page headers across different screen sizes
