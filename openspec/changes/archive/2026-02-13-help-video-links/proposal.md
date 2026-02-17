## Why

Users need guidance on how to use specific screens. Rather than building an in-app help system, we want a lightweight approach: configurable links to tutorial videos (e.g. Screen.Studio recordings) that appear as a contextual button on the relevant page. This keeps things simple while providing immediate help where users need it.

## What Changes

- New tenant-level setting to configure help video links per screen/route
- Settings UI with a table mapping route keys to one or more video URLs
- Green "Kurze Anleitung" button rendered top-right on pages that have a configured link
- Button opens the video URL in a new tab
- If multiple links are configured for a screen, show a dropdown instead of a single button

## Capabilities

### New Capabilities
- `help-video-links`: Tenant-level configuration of tutorial video links per screen, with contextual button display on pages

### Modified Capabilities
(none)

## Impact

- **Backend**: New model for storing help video link configuration (tenant, route key, URL, label). New GraphQL query + mutations.
- **Frontend**: New settings section for managing links. Shared layout component or hook to display the help button on all pages.
- **Routes affected**: All page routes can potentially show the button — no route changes needed, just a context-aware component in the layout.
