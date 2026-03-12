## Context

The contract manager already handles invoices end-to-end: generation from billing schedules, PDF rendering via WeasyPrint, email sending via M365, and configurable numbering. Offers follow the same lifecycle pattern but occur *before* contract activation — they formalize pricing for a future billing period so customers can review and approve before committing.

The existing infrastructure provides strong reuse opportunities: billing schedule calculation, tax classification (domestic/EU/non-EU), PDF rendering pipeline, email sending via Celery + M365 Graph API, and the numbering scheme pattern shared by invoices and credit notes.

## Goals / Non-Goals

**Goals:**
- Create offers from any billing schedule event row with one click
- Freeze offer data at creation time (immutable snapshots) so offers remain accurate even if contract terms change later
- Full status lifecycle: draft → sent → accepted/rejected/cancelled
- PDF generation reusing the invoice template structure with offer-specific labels
- Email sending with recipient selection (pre-filled from customer billing contacts)
- Configurable offer numbering (same UX pattern as invoice numbering)
- Offer list and detail pages with search, filter, and inline PDF preview

**Non-Goals:**
- Offer editing beyond validity date and notes (line items are frozen at creation)
- Converting an accepted offer into a contract automatically
- Offer versioning (creating revised offers linked to previous versions)
- Customer-facing offer portal or self-service acceptance
- ZUGFeRD/structured data in offer PDFs (invoice-only requirement)

## Decisions

### 1. Immutable snapshots over live references

Offers freeze `line_items_snapshot` and `company_data_snapshot` as JSON at creation time rather than joining live data at render time.

**Rationale**: Offers represent a point-in-time commitment. If contract items or company legal data change after the offer is sent, the offer must still reflect what was originally proposed. This matches how invoices already work.

**Alternative considered**: Store only FKs and reconstruct at render time — rejected because contract amendments would silently change already-sent offers.

### 2. Shared numbering base class

`OfferNumberService` extends the same `BaseNumberService` used by invoices and credit notes, with its own `OfferNumberScheme` model per tenant.

**Rationale**: Consistent numbering UX and logic. Users configure offer numbers the same way they configure invoice numbers (pattern, reset period, counter). The base class handles pattern rendering, counter increment, and period reset.

**Alternative considered**: Simpler auto-increment without configurable patterns — rejected because German businesses expect formatted document numbers (e.g., `ANG-2026-0042`).

### 3. Synchronous PDF generation

PDF is generated inline during `create_offer()` rather than as a background Celery task.

**Rationale**: Offer PDFs are single-page, fast to render (<1s via WeasyPrint). The user expects to see the PDF immediately after creation. Unlike batch invoice generation, offers are created one at a time.

**Alternative considered**: Async generation like invoice batch runs — rejected as unnecessary complexity for a single-document operation.

### 4. Async email sending via Celery

Email sending uses a Celery task (`send_offer_email_task`) with no automatic retries.

**Rationale**: M365 API calls can be slow (1-3s). Moving to a background task keeps the UI responsive. No retries to prevent duplicate emails — if sending fails, the user can retry manually via the UI.

### 5. Separate offers app (not nested in contracts)

Offers live in `apps/offers/` as a standalone Django app rather than inside `apps/contracts/`.

**Rationale**: Offers have their own models, schema, services, templates, and URL endpoints. Nesting inside contracts would bloat an already large app. Foreign keys to Contract and Customer use `SET_NULL` so offers survive if the linked entity is deleted.

### 6. Forecast tab integration over standalone creation form

Offers are created from billing schedule event rows in the contract's forecast tab, not from a standalone "New Offer" form.

**Rationale**: An offer always corresponds to a specific billing event (date, period, items). Creating from the forecast row pre-fills all required data. A standalone form would require the user to manually select contract, date, and items — error-prone and redundant.

The forecast tab shows "Create Offer" for events without an existing offer, and "View Offer" with status/amount for events that already have one.

### 7. HTML template derived from invoice template

The offer HTML template (`offers/offer.html`) is a modified copy of `invoices/invoice.html` with offer-specific labels (title, offer number, validity date, no payment terms).

**Rationale**: Offers should look visually consistent with invoices (same company branding, logo, accent color, layout). Sharing the base structure ensures consistency. Offer-specific differences: "Angebot"/"Offer" title, "Gültig bis"/"Valid until" instead of payment terms, no ZUGFeRD XML embedding.

## Risks / Trade-offs

**Snapshot storage growth** → JSON snapshots add ~2-5KB per offer. Acceptable for expected volume (<1000 offers/year). No mitigation needed.

**No offer-to-contract conversion** → Users must manually create/activate contracts after an offer is accepted. This is acceptable for the current workflow where contracts are already created before offers (offers confirm pricing for existing draft/active contracts).

**SET_NULL on FK deletion** → If a contract or customer is deleted, the offer becomes orphaned but remains accessible. This preserves audit history but means the offer detail page must handle missing links gracefully.

**Single PDF language** → PDF language is determined at creation time from tenant settings. If a customer needs a different language, the offer must be deleted and recreated. Low risk given current single-language tenant usage.

**No duplicate prevention** → Multiple offers can be created for the same contract + billing date. The forecast tab mitigates this by showing existing offers, but the API doesn't enforce uniqueness. This is intentional — users may want to create revised offers for the same period.
