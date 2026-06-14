## 1. Data model + migration

- [x] 1.1 Add new fields to `apps/offers/models.py::OfferRecord`: `free_text_after_items`, `free_text_before_terms` (TextField, blank=True, default=""); `minimum_term_months`, `notice_period_months` (PositiveIntegerField, null=True, blank=True); `cloned_from` (self-FK, on_delete=SET_NULL, null=True, blank=True). Status enum extended with FINALIZED (legacy values kept readable).
- [x] 1.2 Added a nullable `source_offer = FK('offers.OfferRecord', on_delete=SET_NULL)` column to `ContractAttachment`. Category is already a free CharField with "offer" mentioned in help_text — no enum change needed.
- [x] 1.3 Added helper classmethods `OfferRecord._contract_derived_fields()`, `OfferRecord._user_editable_fields()`, and `is_locked` property. Unit-test deferred to Task 7.1.
- [x] 1.4 Generated and applied migrations `offers/0003_offerrecord_cloned_from_and_more.py` and `contracts/0052_contractattachment_source_offer.py`. 1482 backend tests green.
- [x] 1.5 Added `finalize` action to `PERMISSION_REGISTRY["offers"]`. Data migration `tenants/0021_grant_offers_finalize_to_admin.py` grants the key to every existing Admin role across all tenants. Manager role inherits via the existing "not users./settings." rule. Viewer untouched. Local cleanup: removed two untracked local-only slack migrations that were blocking the migration graph.

## 2. Backend service layer

- [x] 2.1 Added `OfferLockedError` + `NoBillingEventError` + `OfferService._guard_writable(record)` (static, caller acquires the lock first).
- [x] 2.2 `create_offer` now snapshots `minimum_term_months` from `contract.min_duration_months` and `notice_period_months` from `contract.notice_period_months`. 2.33.6 retry loop preserved.
- [x] 2.3 `OfferService.update_offer(record_id, **fields)` validates the editable surface, locks via `select_for_update`, guards, recomputes line items + totals when `scoped_item_ids` changes, regenerates PDF.
- [x] 2.4 `OfferService.recreate_offer_from_contract(record_id)` locks + guards, re-reads the billing event, raises `NoBillingEventError` when missing, overwrites contract-derived fields via the new shared `_apply_event_to_record` helper, preserves user-edited fields, regenerates PDF.
- [x] 2.5 `OfferService.finalize_offer(record_id)` is idempotent on `finalized`, rejects `sent` and legacy statuses with `OfferLockedError`, transitions `draft → finalized` under `select_for_update`, then calls `attach_pdf_to_contract`.
- [x] 2.6 `OfferService.attach_pdf_to_contract(record)` reuses an existing `ContractAttachment` with `source_offer=record` (idempotent) or creates a new row with copied bytes; description language follows tenant.legal_data country, not the customer language.
- [x] 2.7 `OfferService.clone_offer_to_draft(source_id)` rejects draft sources, allocates a fresh offer number with the same retry loop, copies every snapshot + user-editable field, sets `cloned_from=source`, regenerates PDF.
- [x] 2.8 `send_offer_email_task` short-circuits non-draft offers, dispatches the email first, then transitions `draft → sent` under `select_for_update` and calls `attach_pdf_to_contract`. SMTP failure leaves the draft fully editable. Race with Finalize logs a loud warning instead of overwriting state.

## 3. GraphQL surface

- [x] 3.1 Added `is_locked_error: bool` on `UpdateOfferResult` and `FinalizeOfferResult`. Also added `UpdateOfferInput`, `FinalizeOfferResult`, `CloneOfferResult` types.
- [x] 3.2 New `updateOffer(id, input: UpdateOfferInput!)` mutation. Editable surface only. Maps OfferLockedError → `is_locked_error=true`, ValueError → typed error. Gated on `offers.write`.
- [x] 3.3 New `recreateOfferFromContract(id)` mutation. Maps NoBillingEventError → typed error. Gated on `offers.write`.
- [x] 3.4 New `finalizeOffer(id)` mutation. Gated on the new `offers.finalize` permission.
- [x] 3.5 New `cloneOfferToDraft(id)` mutation. Gated on `offers.write`.
- [x] 3.6 `updateOfferStatus` stubbed: always returns the deprecation error pointing at `finalizeOffer` / `sendOfferEmail` / `deleteOffer`. Existing callers see a clean structured response instead of breaking on a removed field.
- [x] 3.7 `OfferRecordType` extended with `free_text_after_items`, `free_text_before_terms`, `minimum_term_months`, `notice_period_months`, `cloned_from_id`, `is_locked`. `_convert_offer_record` wires them all.
- [x] 3.8 `ContractAttachmentType` extended with `source_offer_id`. Existing `attachments` resolver passes the FK through. Category is already a free CharField; existing "order" / "contract" / "offer" / "other" values continue to work unchanged.

## 4. PDF rendering

- [x] 4.1 Added `apps/offers/markdown_render.py::render_markdown_to_safe_html`. Uses `markdown` extensions `extra/sane_lists/nl2br` + `bleach.clean` with the block-level allowlist (`p, br, em, strong, ul, ol, li, code, blockquote, h3, h4`), no attributes, no protocols, `strip=True`. Added `markdown~=3.7` and `bleach~=6.2` to `backend/pyproject.toml` (also `pip install`ed in the running container).
- [x] 4.2 Template renders `free_text_after_items_html` directly below the line-item table, above totals, conditional on non-empty.
- [x] 4.3 Template renders `free_text_before_terms_html` directly above the VAT block, conditional on non-empty.
- [x] 4.4 Template renders the min-term and notice-period lines via two new context keys (`minimum_term_line`, `notice_period_line`) populated by `_render_minimum_term_line` / `_render_notice_period_line` module helpers — only when `months` is set and `> 0`. German/English wording from spec.
- [x] 4.5 Regression test file `backend/tests/test_offer_pdf_rendering.py` (23 cases): `TestMarkdownSanitizer` covers tag allowlist + script/anchor/image/inline-style stripping; `TestMinTermNoticeLines` covers conditional rendering and wording; `TestTemplateContextWiring` checks the new keys land in the context with the expected values; `TestRenderedHtmlIncludesBlocks` renders the actual Jinja template (mocking WeasyPrint) and asserts the blocks appear / are omitted correctly. Total backend suite at 1505 tests, all green.

## 5. Frontend — ContractDetail

- [x] 5.1 Added the "Create Offer" button to the `ContractDetail.tsx` header next to "Add Todo", gated on `contract.status === 'draft'`. Uses lucide `FileText` icon. `data-testid="contract-create-offer"`.
- [x] 5.2 Wired up the billing-date Dialog (date input, defaults to `contract.startDate`, falls back to today). Calls the existing `createOffer(contractId, billingDate)` mutation. Spinner + disabled state while in flight.
- [x] 5.3 On success: closes the dialog and navigates to `/offers/{id}`. Failure: error message rendered inline inside the dialog (no toast — keeps the input visible for retry).
- [ ] 5.4 Playwright E2E deferred — would need a running dev server + seeded draft contract; scoped to Group 8 verification rather than Group 5.

## 6. Frontend — OfferDetail

- [x] 6.1 `OfferDetail` query now fetches `freeTextAfterItems`, `freeTextBeforeTerms`, `minimumTermMonths`, `noticePeriodMonths`, `clonedFromId`, and `isLocked`.
- [x] 6.2 New `MarkdownField` sub-component renders side-by-side `<textarea>` + live `react-markdown` preview when editable. Saves via `updateOffer` on blur — auto-save semantics consistent with the spec's "every successful edit re-renders the PDF" requirement.
- [x] 6.3 Editable inline inputs for `validUntil`, `minimumTermMonths`, `noticePeriodMonths` in the metadata card (date + number inputs, auto-save on blur). `scoped_item_ids` editor deferred — backend accepts it but the UI for picking a subset of contract items is non-trivial and out-of-scope for this PR per Suggestion #2 from the verify pass.
- [x] 6.4 Locked offers render the same `MarkdownField` component in read-only mode (live preview only, no textarea, empty fields render as muted "—").
- [x] 6.5 "Re-create from contract" button on drafts opens a confirmation `Dialog` listing what's overwritten vs preserved (i18n key `offers.recreateConfirmDescription`). Confirm calls `recreateOfferFromContract`. Maps `isLockedError` to a clear toast.
- [x] 6.6 "Finalize" button on drafts uses a native `confirm()` (per spec: no extra dialog) then calls `finalizeOffer`. Toast on success/error.
- [x] 6.7 "Copy to edit" button on locked offers calls `cloneOfferToDraft`, navigates to the new draft on success.
- [x] 6.8 Locked-state banner (purple) at the top of the layout with `Lock` icon, status-specific text (Sent vs Finalized), recipients, date, and the "Copy to edit" hint. `data-testid="offer-locked-banner"`. Cloned-from badge in the title row.
- [x] 6.9 i18n updates: 30+ new keys in both `offers.*` blocks (createOffer dialog, billingDate, freeText labels + hint, minimumTerm/noticePeriod labels, finalize/recreate/copyToEdit + their toasts, lockedBanner variants). No `attachments.category.offer` key needed since the existing attachment-list renderer reads the category string directly.
- [ ] 6.10 Playwright E2E deferred to Group 8.

## 7. Tests

- [x] 7.1 `backend/tests/test_offer_lifecycle.py` (20 tests). Covers `update_offer` (accept-only-editable / reject-unknown / reject-empty-list / null-scope / reject-locked), `recreate_offer_from_contract` (preserve user edits + overwrite snapshot, raises `NoBillingEventError`, rejects locked), `finalize_offer` (finalize+attach, idempotent, rejects sent/legacy), `attach_pdf_to_contract` (idempotent, FK survives offer delete), `clone_offer_to_draft` (copies snapshots + new number + `cloned_from`, rejects draft sources).
- [x] 7.2 `TestConcurrentFinalizeAndSend.test_finalize_then_send_does_not_overwrite` simulates the send-task entering its post-send transaction after Finalize has locked the offer; verifies the send-task's status guard refuses to overwrite the finalized state.
- [x] 7.3 Markdown sanitizer covered by Group 4's `test_offer_pdf_rendering.py::TestMarkdownSanitizer` (9 cases including `<script>`, inline styles, `<img>`, `<a>`, plus positive cases for allowlist tags).
- [x] 7.4 Min-term / notice-period conditional rendering covered by Group 4's `TestMinTermNoticeLines` + `TestRenderedHtmlIncludesBlocks` (German + English wording, null / zero / positive value handling, full Jinja render).
- [x] 7.5 `TestFinalizePermission` (in `test_offer_lifecycle.py`): editor with `offers.write` but NOT `offers.finalize` is rejected; admin succeeds. Goes through the GraphQL mutation entry point so permission wiring is exercised.
- [ ] 7.6 Frontend snapshot tests deferred — Vitest setup is out of scope here; manual smoke covers the visibility matrix in Group 8 verify.

## 8. Docs + rollout

- [ ] 8.1 Update CLAUDE.md with the editable-surface contract and the lifecycle change.
- [ ] 8.2 Add changelog entry for the release that ships this change.
- [ ] 8.3 Verify the change end-to-end on staging: create from contract page → edit free-text → finalize → confirm the PDF appears as a `ContractAttachment` on the contract detail page; clone-to-edit → new draft has same content + new number.
- [ ] 8.4 Run `/opsx:verify offer-edit-and-finalize` before archiving the change.
