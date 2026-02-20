## Why

Contracts and customers need a comment trail where multiple users can leave timestamped notes. Currently, contracts have a single `notes` TextField (overwritten on each edit, no history), and customer notes have a `CustomerNote` model that exists but is not exposed in the API or UI. Users need a shared, chronological comment feed visible on the detail pages.

## What Changes

- Add a `ContractComment` model (author, text, timestamps) following the existing `TodoComment` / `CustomerNote` pattern
- Expose both `ContractComment` and `CustomerNote` via GraphQL (create, update-own-within-24h, delete-own, list)
- Add a comments section on ContractDetail (`/contracts/:id`) sharing the row where internal notes currently live
- Add a comments section on CustomerDetail (`/customers/:id`) in a similar position
- Show the 3 most recent comments (newest first) with a "Show all" button that opens a modal with the full history
- Add comment button opens a small modal with a textarea (markdown supported) and save
- Users can edit their own last comment if it was posted less than 24 hours ago
- Render comment text as markdown

## Capabilities

### New Capabilities
- `entity-comments`: Comment system for contracts and customers — backend models, GraphQL API, and frontend UI with markdown rendering, 24h edit window, and paginated modal

### Modified Capabilities

## Impact

- **Backend**: New `ContractComment` model + migration, new GraphQL types/mutations in `contracts/schema.py`, expose existing `CustomerNote` in `customers/schema.py`
- **Frontend**: New shared `CommentsSection` component used by both `ContractDetail.tsx` and `CustomerDetail.tsx`
- **Dependencies**: Need a markdown renderer (e.g. `react-markdown` or similar — check if already available)
- **Existing contract `notes` field**: Kept as-is (internal notes remain separate from the comment feed)
