## Context

Offers today are created by `OfferService.create_offer(contract_id, billing_date)` from a single revenue-forecast row, write their frozen snapshots in one shot, and have no edit surface afterwards. `OfferRecord.status` has the choices `draft / sent / accepted / declined / expired` but no code path enforces immutability based on status — write-protection lives only in the absence of an edit UI.

The contract has the contract attachments list (`ContractAttachment` model) already, used today for OC PDFs and free uploads. `Contract.attachments` resolver returns physical rows; a recent change (diary 2026-05-13) introduced synthetic virtual rows with negative IDs for `OrderConfirmation` — we are deliberately not reusing that pattern here, because the user requirement is that the offer PDF survives as a real attachment.

Relevant existing models / services:
- `apps/offers/models.py::OfferRecord` — snapshot + `pdf_file` FileField
- `apps/offers/services.py::OfferService.create_offer` — already has the retry loop fixed in 2.33.6
- `apps/offers/tasks.py::send_offer_email_task` — sets `email_sent_at` and `email_sent_to`
- `apps/contracts/models.py::ContractAttachment` — has `category` choices and `file` FileField

Stakeholders: sales (creates offers, iterates), finance (sees the locked archive), customer success (downloads the final PDF from the contract).

## Goals / Non-Goals

**Goals:**
- A single source of truth for which fields are user-edited vs contract-derived, so re-create has a clean rule for what to overwrite.
- Backend-enforced immutability once an offer leaves `draft` — UI alone is not enough.
- Real attachment rows on the contract for sent/finalized offers so the contract page is a complete audit history.
- Deterministic, race-safe lifecycle transitions (no double-attach, no half-finalized state).
- Markdown rendering pipeline that is XSS-safe in the PDF.

**Non-Goals:**
- No new offer states beyond the simplified `draft → sent | finalized`. The previous `accepted / declined / expired` choices are dropped from the lifecycle (left in code as historical / for a future feature).
- No customer-facing accept/decline portal.
- No template-based PDF redesign — only additive rendering for the two free-text blocks and the min-term / notice-period rows.
- No backfill: existing offers in `sent` state do not retroactively attach to their contracts.
- No numbering-scheme changes (covered by 2.33.6).

## Decisions

### Decision 1: Snapshot vs editable surface

Split `OfferRecord` fields into three groups, documented in code (`OfferRecord._contract_derived_fields()` and `_user_editable_fields()` class methods):

1. **Contract-derived snapshots** (rewritten by `recreate_offer_from_contract`):
   `line_items_snapshot`, `company_data_snapshot`, `customer_name`, `contract_name`, `period_start`, `period_end`, `billing_date`, `total_net`, `tax_rate`, `tax_amount`, `total_gross`, `vat_sentence`, `scoped_item_ids` (when implicit — see Decision 3).

2. **User-editable fields** (preserved by re-create, mutated by `update_offer`):
   `free_text_after_items`, `free_text_before_terms`, `valid_until`, `minimum_term_months`, `notice_period_months`, `scoped_item_ids` (when explicit — see Decision 3).

3. **Immutable identity** (set at create, never changed):
   `offer_number`, `offer_date`, `cloned_from`, `tenant`, `contract`, `customer`, `created_by`.

`update_offer` accepts only group 2. `recreate_offer_from_contract` overwrites only group 1. This makes the contract between the two operations explicit and testable.

**Alternative considered:** a single boolean flag `is_user_edited` per field. Rejected — too granular to maintain and not what the user asked for.

### Decision 2: Lifecycle and locking enforcement

`OfferRecord.Status` is reduced to:

```
draft → sent       (system path: email send success)
draft → finalized  (user path: explicit Finalize click)
```

Both `sent` and `finalized` are terminal locked states.

Enforcement lives in **one** place: `OfferService._guard_writable(record)` raises `OfferLockedError` if `record.status != 'draft'`. Every editing entry point calls it as the first thing inside the transaction:

```python
def update_offer(self, record, **fields):
    with transaction.atomic():
        record = OfferRecord.objects.select_for_update().get(pk=record.pk)
        self._guard_writable(record)
        # ... apply fields, save, regenerate pdf
```

The `select_for_update()` plus the in-transaction status check is what guards against concurrent finalize/send races (Decision 4).

GraphQL surfaces this as `LockedOfferError` in the result type (consistent with other typed error patterns in this codebase, e.g. `VoidInvoiceResult`).

**Alternative considered:** Django signals to revert non-draft saves. Rejected — implicit, hard to surface in GraphQL responses.

### Decision 3: Scoped item set — implicit vs explicit

`scoped_item_ids` is currently optional: `None` means "all contract items". When the user edits the scope on a draft, that becomes explicit and we record `scoped_item_ids` as a real list. On `recreate_offer_from_contract`:

- If the existing `scoped_item_ids` is `None` (implicit), re-create keeps it `None` and the line items naturally follow the contract's full item set.
- If `scoped_item_ids` is an explicit list, re-create preserves the list and recomputes line items only for those IDs (ignoring contract items no longer in scope).

We surface this distinction by storing `None` explicitly (not an empty list — which would mean "scope to zero items"). Empty-list is invalid input on `update_offer`.

### Decision 4: Race-safe lock + idempotent finalize

`finalize_offer`:

```
SELECT ... FOR UPDATE                       # serialize concurrent finalize
if status == 'finalized':  return record    # idempotent no-op
if status == 'sent':       raise LockedOfferError
assert status == 'draft'
status = 'finalized'
save()
attach_pdf_to_contract(record)              # see Decision 5
```

Email-send path (in the celery task):

```
SELECT ... FOR UPDATE
if status != 'draft':  abort (do not send a locked-then-sent offer)
send email
on success: status = 'sent', email_sent_at = now()
            save()
            attach_pdf_to_contract(record)
on failure: leave status = 'draft', email_sent_at stays null
```

Both writers hit `attach_pdf_to_contract` after the status transition is persisted. That function is itself idempotent (Decision 5).

### Decision 5: Contract attachment copy

`OfferService.attach_pdf_to_contract(record)`:

1. Skip if `record.pdf_file` is empty (defensive — should never happen for a sent or finalized offer).
2. Look up an existing `ContractAttachment` with `contract=record.contract` AND `source_offer=record`. If one exists, return it (idempotent).
3. Else create a new `ContractAttachment` row:
   - `contract = record.contract`
   - `category = ContractAttachment.Category.OFFER` (new choice value)
   - `source_offer = record` (new FK)
   - `description = f"Angebot {record.offer_number}"` (localized by tenant default)
   - `file` = a fresh save of the bytes from `record.pdf_file` so the attachment owns its own physical file and is not corrupted by later offer file deletes.

`ContractAttachment.source_offer` is a nullable `ForeignKey('offers.OfferRecord', on_delete=SET_NULL)`. SET_NULL not CASCADE — if the offer is hard-deleted (test setup, manual cleanup), the attachment still survives because it represents what the customer received.

**Clone-to-edit interaction**: a cloned draft can later be finalized/sent, producing a *second* attachment with its own `source_offer`. Multiple `offer` attachments per contract are valid — the audit trail is the point.

**Alternative considered:** synthetic virtual attachments (negative-ID pattern from OC). Rejected per user requirement #4 — must be a real row.

### Decision 6: Markdown rendering in the PDF

Two free-text fields, both Markdown. PDF rendering path:

1. Persist raw Markdown in `TextField` (`free_text_after_items`, `free_text_before_terms`).
2. At PDF render time, convert via `markdown.markdown(text, extensions=['extra', 'sane_lists', 'nl2br'])` → HTML.
3. **Sanitize** with `bleach.clean(html, tags=['p','br','em','strong','ul','ol','li','code','blockquote','h3','h4'])` before injection into the Jinja PDF template — no inline styles, no links, no images. WeasyPrint inherits the surrounding CSS from the existing template.
4. Empty / whitespace-only content → block is skipped entirely (no empty `<p>` in the PDF).

**Why bleach:** WeasyPrint runs HTML through its own renderer; an attacker who can inject `<script>` cannot execute it, but unsanitized HTML can still break layout (unclosed tags, large `<img>` etc.). bleach is already in dependencies via the comments module.

**Frontend Markdown editor**: simple `<textarea>` plus a live preview that uses the existing `react-markdown` (already a dep for the changelog). Server is the source of truth — preview is best-effort.

### Decision 7: Min-term / notice-period rendering

On create, snapshot from contract:
- `OfferRecord.minimum_term_months = contract.min_duration_months` (may be `None`)
- `OfferRecord.notice_period_months = contract.notice_period_months` (default 3 on contract, may be overridden by user on offer)

On PDF render, the offer template emits two lines **only if the value is set AND non-zero**:

```
Mindestlaufzeit {{ minimum_term_months }} Monate ab Vertragsbeginn.
Kündigungsfrist {{ notice_period_months }} Monate zum Ende der Mindestvertragslaufzeit.
```

English wording mirrors:
```
Minimum term {{ minimum_term_months }} months from the contract start date.
Notice period {{ notice_period_months }} months to the end of the minimum term.
```

Sentence selection is driven by the same `customer.get_effective_invoice_language()` call that selects the rest of the PDF language. The `notice_period_anchor` field on the contract (end_of_month vs end_of_quarter) is **not** rendered into the offer — too granular for an offer document, and finance can always override the contract later.

### Decision 8: Permissions

- `offers.write` — `update_offer`, `recreate_offer_from_contract`, `clone_offer_to_draft`, `create_offer` (existing).
- `offers.finalize` — **new permission key**, dedicated to `finalize_offer`. Created so a finance reviewer role can finalize without being given full write access.
- `offers.delete` — unchanged (existing, for drafts only).
- Reading remains `offers.read` (existing).

Default role grants: Admin gets everything; Editor gets `write` + `delete` but NOT `finalize` by default — finalize is a deliberate gate that admins can hand out to specific roles. (Migration: backfill Admin role only.)

### Decision 9: Re-create UX guard

`recreate_offer_from_contract` is destructive on group-1 fields. UI shows a confirm dialog listing exactly which fields will be overwritten ("X Positionen werden neu eingelesen, Beträge und Firmendaten aktualisiert"). User-edited fields are listed as "bleiben erhalten". Action label: "Aus Vertrag neu einlesen" / "Re-read from contract".

If the contract has no billing event for the offer's `billing_date` after the contract was edited (e.g. the user changed the contract start past that date), the mutation returns an error rather than silently doing nothing.

## Risks / Trade-offs

- **Risk**: Markdown gives users enough rope to break layout (huge nested lists). → Mitigation: bleach allowlist drops anything but block-level basics; the PDF template uses `overflow: hidden` on the free-text containers.
- **Risk**: Lock-then-send race where Finalize and email-send hit the same draft in parallel. → Mitigation: `select_for_update()` inside both code paths inside `transaction.atomic()` — Postgres row lock serializes them.
- **Risk**: User deletes the source offer (clone-to-edit) and expects the attachment to disappear too. → Trade-off accepted: `source_offer` is SET_NULL on delete; attachment stays as the historical record. Documented in the offer detail page banner.
- **Risk**: Re-create on a draft that was already heavily edited (free-text full of content) → unclear what re-create touches without reading the dialog. → Mitigation: the confirm dialog is explicit and lists both "wird überschrieben" and "bleibt erhalten" buckets.
- **Risk**: New `category=offer` choice on `ContractAttachment` requires a UI label everywhere the attachment list is rendered (contract detail, attachments page). Missing labels show as raw enum value. → Mitigation: i18n key `attachments.category.offer` added in the same change.
- **Trade-off**: dropping `accepted / declined / expired` from the live lifecycle simplifies code but loses a future-proofing path. → Accepted; can be re-introduced as a separate change later. Existing rows with those values stay readable; the GraphQL enum keeps them for backwards compat.

## Migration Plan

1. **Schema migration (additive only):**
   - `OfferRecord`: add `free_text_after_items: TextField(blank=True, default="")`, `free_text_before_terms: TextField(blank=True, default="")`, `minimum_term_months: PositiveIntegerField(null=True, blank=True)`, `notice_period_months: PositiveIntegerField(null=True, blank=True)`, `cloned_from: ForeignKey('self', null=True, blank=True, on_delete=SET_NULL)`.
   - `ContractAttachment`: add `source_offer: ForeignKey('offers.OfferRecord', null=True, blank=True, on_delete=SET_NULL)` and add `OFFER = "offer"` to its `Category` choices.
   - Permission registry migration: add `offers.finalize` and grant it to Admin role.
2. **Code rollout**: backend mutations + service-layer guard ship first, frontend follows in the same deploy.
3. **Backfill**: none. Existing `sent` offers do not get retroactive attachments — the change applies forward-only.
4. **Rollback**: status guard is the only behavior change for existing data. Reverting the deploy restores read-write on non-draft offers; no data corruption. The DB migrations are additive so a code-only rollback is safe.

## Open Questions

- **Q1**: Should "Re-create from contract" trigger a fresh PDF render automatically, or wait for the user to click Save? → Tentative: yes, fresh PDF immediately, because the draft is no longer consistent with the contract until then.
- **Q2**: Multiple finalized offers on the same contract → both attachments listed in the contract attachments tab. Acceptable? → Tentative yes per Decision 5 (audit trail). Confirm with user during tasks phase.
- **Q3**: Should `clone_offer_to_draft` re-read the contract or copy the source offer's snapshot? Proposal says copy the source. → Confirmed by user wording "Copy to edit". Re-read is one extra click via "Re-create from contract" on the new draft.
