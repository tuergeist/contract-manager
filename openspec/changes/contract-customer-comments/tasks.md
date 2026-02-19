## 1. Backend Models & Migration

- [x] 1.1 Add `ContractComment` model to `backend/apps/contracts/models.py` (contract FK, text TextField, author FK to User, TenantModel base, ordered by `-created_at`)
- [x] 1.2 Create migration for `ContractComment`

## 2. Backend GraphQL — Contract Comments

- [x] 2.1 Add `ContractCommentType` with fields `id`, `text`, `author`, `createdAt`, `updatedAt`, `canEdit`, `canDelete` to `contracts/schema.py`
- [x] 2.2 Add `contractComments(contractId)` query returning all comments newest first
- [x] 2.3 Add `addContractComment` mutation (validate non-empty text, set author + tenant)
- [x] 2.4 Add `updateContractComment` mutation (enforce author + most-recent + 24h window)
- [x] 2.5 Add `deleteContractComment` mutation (enforce author-only)

## 3. Backend GraphQL — Customer Comments

- [x] 3.1 Add `CustomerCommentType` with same fields as `ContractCommentType` to `customers/schema.py` (backed by existing `CustomerNote` model, map `content` → `text`)
- [x] 3.2 Add `customerComments(customerId)` query returning all comments newest first
- [x] 3.3 Add `addCustomerComment` mutation (validate non-empty text, set user + tenant)
- [x] 3.4 Add `updateCustomerComment` mutation (enforce author + most-recent + 24h window)
- [x] 3.5 Add `deleteCustomerComment` mutation (enforce author-only)

## 4. Frontend Dependencies & Shared Component

- [x] 4.1 Install `react-markdown` package in the frontend container
- [x] 4.2 Add i18n keys for comments UI (add comment, edit, delete, show all, no comments yet, comment saved, etc.) in `en.json` and `de.json`
- [x] 4.3 Create shared `CommentsSection` component (`frontend/src/components/CommentsSection.tsx`) with props `entityType`, `entityId`, `currentUserId` — includes GraphQL queries/mutations for both entity types, 3-comment preview, "Show all" button, add/edit/delete actions, markdown rendering

## 5. Frontend Integration

- [x] 5.1 Integrate `CommentsSection` into `ContractDetail.tsx` — two-column grid with internal notes (notes left, comments right, stacked on mobile)
- [x] 5.2 Integrate `CommentsSection` into `CustomerDetail.tsx` — add comments section in similar card layout

## 6. Verification

- [x] 6.1 Run `npx tsc --noEmit` — no TypeScript errors
- [x] 6.2 Run `make test-back` — all backend tests pass
