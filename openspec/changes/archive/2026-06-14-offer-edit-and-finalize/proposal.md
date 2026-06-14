## Why

Offers are currently a one-shot artifact: created from a revenue-forecast row, immediately snapshotted, and effectively read-only afterwards. Users routinely need to iterate on an offer before it goes out (add free-form narrative, re-issue after contract changes, attach the agreed minimum term and notice period) and need a clean lock once it is finalized or sent so the document stays trustworthy in the customer relationship.

The current flow forces awkward workarounds: edit the contract, delete the offer, re-create from forecast, hand-edit numbers. That is error-prone, breaks numbering continuity, and there is no link back from the contract to the finalized PDF that the customer received.

## What Changes

- Add a **Create Offer** button on the contract detail page (top right, left of **Add Todo**) — visible only while the contract status is exactly `draft`. Pre-fills with the contract's billing data the same way the forecast-row flow does today.
- Snapshot the contract's **minimum duration** and **notice period** into the offer at create time, but only render them on the PDF when the value is set (non-null and non-zero). German PDF wording: "Mindestlaufzeit XX Monate", "Kündigungsfrist YY Monate zum Ende der Mindestvertragslaufzeit"; English equivalent.
- Add two **Markdown free-form fields** on the offer detail page (`/offers/:id`):
  - `free_text_after_items`: rendered into the PDF directly below the line-item table
  - `free_text_before_terms`: rendered into the PDF directly above the T&C / VAT block
  - Both optional, persisted on `OfferRecord`, rendered as Markdown in the PDF (sanitized).
- An offer is **editable while `status == 'draft'`**. Editable fields: `free_text_after_items`, `free_text_before_terms`, `valid_until`, `minimum_term_months`, `notice_period_months`, `scoped_item_ids`. Every successful edit re-renders the PDF.
- **Re-create from contract**: while the offer is `draft`, a "Re-create from contract" action re-snapshots the contract's billing data into the existing OfferRecord. The `offer_number` is preserved. Only the contract-derived snapshots are overwritten (line items, amounts, company data, period, scoped item set if it was implicit, min-term/notice-period defaults). **User-edited fields are preserved**: free-text fields, explicit `valid_until` override, and an explicit user override for min-term/notice-period.
- **Lifecycle simplification**. `OfferRecord.Status` becomes: `draft` → (`sent` OR `finalized`). Both `sent` and `finalized` are terminal locked states.
  - `sent` = the system sent the offer email (set after `email_sent_at` is recorded). System-driven.
  - `finalized` = user downloaded the PDF and intends to send it manually. User-driven, single click on "Finalize".
- **Locking on lifecycle exit**:
  - Lock fires on successful `email_sent_at` (not on click of Send), and on Finalize.
  - Locked offers reject all edit / re-create mutations at the service layer.
  - On lock, the offer's PDF is **copied into the contract's `ContractAttachment` list as a real row** with category `offer`. Source file is read from `OfferRecord.pdf_file` and saved as a new `ContractAttachment.file` so the attachment survives independently if the offer is later mutated by a migration or the file storage path changes. The row stores a back-reference (`source_offer_id` or equivalent) for traceability.
  - Finalize is **idempotent**: clicking Finalize on an already-finalized offer is a no-op; clicking Finalize on a `sent` offer is rejected (already locked through the other path).
- **Copy to edit** action on a locked offer: clones the OfferRecord into a new `draft` with:
  - A new `offer_number` from the scheme
  - Fresh snapshots from the source offer's data (NOT re-fetched from the contract — the user is iterating on the document they sent)
  - Free-text fields and overrides copied over
  - New `cloned_from` FK pointing back to the source OfferRecord for audit
- **BREAKING (internal)**: the `OfferRecord.status` lifecycle gains a hard "locked" rule that the backend enforces — any mutation that writes to a non-`draft` offer is rejected at the service layer, not just the UI. Existing callers that update non-draft offers will start to fail.

## Capabilities

### New Capabilities

- `offer-edit`: editing rules for draft offers — which fields are editable, what re-create touches vs preserves, and how PDF regeneration is triggered.
- `offer-finalize`: lifecycle rules for finalizing or sending an offer — locking semantics, idempotency, contract-attachment copy on lock, and the copy-to-edit clone operation.

### Modified Capabilities

- `offer-generation`: add the "Create from contract detail page" entry point (in addition to the existing forecast-row entry point) and snapshot `minimum_term_months` / `notice_period_months` from the contract at create time.
- `offer-record`: extend `OfferRecord` with `free_text_after_items` (Markdown), `free_text_before_terms` (Markdown), `minimum_term_months`, `notice_period_months`, and `cloned_from` (self-FK). Define which fields are part of the contract-derived snapshot vs the user-edited draft surface.
- `offer-list-detail`: surface the new free-text fields and lifecycle actions (Edit, Re-create from contract, Finalize, Copy to edit, Locked-state banner) on `/offers/:id`.

## Impact

- **Backend**:
  - `apps/offers/models.py`: new fields on `OfferRecord` (`free_text_after_items`, `free_text_before_terms`, `minimum_term_months`, `notice_period_months`, `cloned_from`) + Django migration. Existing rows: text fields default `""`, integer fields nullable, no backfill.
  - `apps/offers/services.py`: new methods `update_offer`, `recreate_offer_from_contract`, `finalize_offer`, `clone_offer_to_draft`. Existing `create_offer` snapshots min-term/notice-period from contract. PDF regeneration hook on every editable write. Lock enforcement (`select_for_update` to guard against parallel finalize / send races).
  - `apps/offers/schema.py`: GraphQL mutations `updateOffer`, `recreateOfferFromContract`, `finalizeOffer`, `cloneOfferToDraft`. Existing `sendOfferEmail` task sets `status=sent` on successful `email_sent_at` and triggers the contract-attachment copy.
  - `apps/offers/tasks.py`: on successful email send, attach PDF to parent contract.
  - `apps/contracts/models.py`: `ContractAttachment` gets an optional `source_offer` FK + a new `category` choice value `offer`. Migration backfill: none (only new locks attach).
  - `apps/contracts/schema.py`: no resolver changes needed — real `ContractAttachment` rows are already returned by the existing `Contract.attachments` resolver.
  - Permissions: keep `offers.write` for edits and clone; existing `offers.delete` unchanged; new `offers.finalize` for the Finalize action.
- **Frontend**:
  - `ContractDetail.tsx`: new **Create Offer** button left of **Add Todo**, visible only when `status === 'draft'`.
  - `OfferDetail.tsx` (route `/offers/:id`): Markdown-editable textareas for the two free-form fields, edit form for valid-until / min-term / notice-period, **Re-create from contract** action on drafts (destructive-confirm dialog), **Finalize** and **Copy to edit** actions, locked-state banner.
  - Offer PDF template: render the two free-text Markdown blocks at their respective positions, render min-term and notice-period lines when their values are set (German/English wording driven by customer language).
  - i18n: new keys for the lifecycle actions and locked banner.
- **Out of scope**: numbering-scheme changes (covered separately by the 2.33.6 retry fix), email-template changes for the `sendOffer` flow, approval workflow, or rejecting an offer.
