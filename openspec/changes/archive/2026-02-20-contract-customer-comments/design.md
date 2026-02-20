## Context

Contracts have a single `notes` TextField that gets overwritten on each edit — no history, no attribution. Customers have a `CustomerNote` model (FK to Customer, FK to User, TextField content, ordered by `-created_at`) that already exists but is not exposed via GraphQL or rendered in the UI. The `TodoComment` model provides a proven pattern for user-attributed comments with timestamps.

The frontend has two detail pages where comments will live:
- **ContractDetail** (`/contracts/:id`): Internal notes section at line ~993, a bordered card with edit-in-place textarea
- **CustomerDetail** (`/customers/:id`): Similar layout

No markdown rendering library is currently installed in the frontend.

## Goals / Non-Goals

**Goals:**
- Chronological comment feed on both contract and customer detail pages
- Multi-user attribution with timestamps
- 24-hour edit window for own last comment (prevents permanent mistakes without allowing unlimited rewrites)
- Markdown rendering for comment text
- Compact 3-comment preview with full-history modal
- Shared component reusable across both entity types

**Non-Goals:**
- Replacing the existing contract `notes` field (kept as separate internal notes)
- Comment notifications or email alerts
- @mentions or comment threading
- File attachments on comments
- Comments on other entity types (products, invoices, etc.)

## Decisions

### 1. Model: New `ContractComment`, reuse existing `CustomerNote`

**Choice:** Create `ContractComment` following the `TodoComment` pattern. Adapt `CustomerNote` in-place (it already has the right shape: customer FK, user FK, content text, timestamps from TenantModel).

**Why not a generic polymorphic Comment model?** The two models live in separate Django apps (`contracts` vs `customers`). A shared model would require either a GenericForeignKey (poor query performance, no FK integrity) or a new shared app. Two simple models in their respective apps is cleaner and follows the existing codebase pattern.

**`ContractComment` fields:**
- `contract` — FK to Contract, `related_name="comments"`, CASCADE
- `text` — TextField
- `author` — FK to User, CASCADE

Inherits `created_at`, `updated_at`, `tenant` from TenantModel. Ordered by `-created_at`.

**`CustomerNote` changes:** Rename `content` → keep as-is (no migration needed). The field name difference is fine — the GraphQL layer normalizes to `text`.

### 2. Frontend: Shared `CommentsSection` component

**Choice:** A single `CommentsSection` component parameterized by entity type and ID, used in both detail pages.

**Props:**
- `entityType: "contract" | "customer"` — determines which GraphQL queries/mutations to use
- `entityId: string` — the entity ID
- `currentUserId: string` — for edit/delete permission checks

**Subcomponents:**
- `CommentItem` — renders a single comment (avatar placeholder, author name, relative time, markdown body, edit/delete actions)
- `AddCommentModal` — dialog with textarea + save
- `AllCommentsModal` — full scrollable list

### 3. Markdown: `react-markdown` with minimal config

**Choice:** Add `react-markdown` (lightweight, widely used, already a React component). No plugins needed — basic markdown (bold, italic, links, lists, code) is sufficient.

**Why not a rich text editor?** Users want quick text comments, not documents. A textarea with markdown preview-on-render is simpler and matches the existing pattern (todo comments are plain text).

### 4. 24-hour edit window enforcement

**Choice:** Enforce on both backend and frontend.

- **Backend:** Mutation checks `comment.author == current_user` AND `comment.created_at >= now - 24h`. Returns error otherwise.
- **Frontend:** Only shows edit button on comments where `author.id == currentUser.id` AND `createdAt` is within 24h. This is a UX convenience — the backend is the source of truth.

Users can only edit their own **most recent** comment (not any comment within 24h). This prevents rewriting history mid-conversation.

### 5. Delete: own comments only, no time restriction

**Choice:** Users can delete their own comments at any time. This is more permissive than edit (which has the 24h window) because deletion is a simpler action — it removes rather than rewrites.

### 6. Layout: Comments beside internal notes

**Choice:** On ContractDetail, add the comments section in the same bordered card row as internal notes, using a two-column grid on wider screens (notes left, comments right) that stacks on mobile. On CustomerDetail, add comments in a similar position.

### 7. GraphQL API shape

**Queries:**
- `contractComments(contractId: ID!) → [CommentType!]!` — all comments, newest first
- `customerComments(customerId: ID!) → [CommentType!]!` — all comments, newest first

**Mutations:**
- `addContractComment(contractId: ID!, text: String!) → CommentResult`
- `updateContractComment(commentId: ID!, text: String!) → CommentResult`
- `deleteContractComment(commentId: ID!) → DeleteResult`
- `addCustomerComment(customerId: ID!, text: String!) → CommentResult`
- `updateCustomerComment(commentId: ID!, text: String!) → CommentResult`
- `deleteCustomerComment(commentId: ID!) → DeleteResult`

**CommentType fields:** `id`, `text`, `author { id, firstName, lastName }`, `createdAt`, `updatedAt`, `canEdit` (computed: is author + within 24h + is last comment), `canDelete` (computed: is author)

The `canEdit`/`canDelete` fields let the frontend show/hide action buttons without duplicating business logic.

## Risks / Trade-offs

- **Two sets of mutations** (contract + customer) instead of a unified API — adds some code duplication but keeps the codebase aligned with existing patterns where each app owns its schema. Mitigation: shared helper functions for the 24h check and permission logic.

- **No pagination on the "all comments" query** — for most contracts/customers, comment count will be low (tens, not thousands). If this becomes a problem later, add cursor-based pagination. For now, fetching all is simpler and sufficient.

- **`react-markdown` bundle size** — adds ~30KB gzipped. Acceptable for this use case. The alternative (dangerouslySetInnerHTML with a custom parser) is riskier and harder to maintain.

- **No real-time updates** — comments won't appear for other users until they refresh or navigate away and back. Mitigation: Apollo cache updates after mutations ensure the current user sees their changes immediately. Real-time via WebSockets is out of scope.
