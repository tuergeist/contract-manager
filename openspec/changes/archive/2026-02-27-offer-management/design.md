## Context

Contract Manager handles invoicing end-to-end: billing schedules, invoice generation, PDF rendering, email sending. Offers/quotes are the missing pre-sales counterpart. The invoice infrastructure (models, numbering, PDF, email) is mature and battle-tested — offers should follow the same patterns to minimize risk and keep the codebase consistent.

The revenue forecast tab already computes billing events per contract. Each row has all the data needed to create an offer: date, line items, quantities, prices, amounts.

## Goals / Non-Goals

**Goals:**
- Generate offers from any contract's forecast (draft or active)
- Offer lifecycle: draft → sent → accepted / rejected / expired
- PDF rendering with dedicated offer template
- Email sending with additional recipient selection
- List + detail views mirroring the invoice UI

**Non-Goals:**
- Offer acceptance workflow (e-signature, customer portal) — status is set manually for now
- Converting accepted offers into contracts or invoices automatically
- Offer versioning / revision tracking
- Discount negotiation or approval workflows
- ZUGFeRD/e-invoicing for offers (not applicable)

## Decisions

### 1. Separate `offers` Django app vs. extending `invoices`

**Decision:** Create a new `offers` app.

**Rationale:** Offers and invoices share structural similarities (numbering, PDF, email) but have different lifecycles, status flows, and business rules. Mixing them into the `invoices` app (which is already large with schema.py, services.py, models.py) would increase complexity. A separate app keeps concerns clean and avoids bloating the invoice code.

**Alternative considered:** Adding `OfferRecord` to the invoices app. Rejected because the invoices app already handles InvoiceRecord, ImportedInvoice, InvoiceTemplate, CompanyLegalData, numbering schemes — adding offers would make it unwieldy.

### 2. OfferRecord model design

**Decision:** Mirror InvoiceRecord's snapshot approach — freeze line items, company data, and customer data at offer creation time.

Key fields:
- `offer_number` — from OfferNumberScheme (default pattern: `A-{YYYY}-{NNNN}`)
- `contract`, `customer` — FK links (nullable, SET_NULL)
- `offer_date`, `valid_until` — offer date and expiration
- `billing_date`, `period_start`, `period_end` — from the billing event
- `total_net`, `tax_rate`, `tax_amount`, `total_gross` — amounts
- `line_items_snapshot`, `company_data_snapshot` — frozen JSON
- `status` — draft / sent / accepted / rejected / expired / cancelled
- `pdf_file` — generated PDF
- `customer_name`, `contract_name` — denormalized for display
- `email_sent_at`, `email_sent_to`, `email_message_id` — sending tracking
- `notes` — free-text field for offer conditions/notes (rendered in PDF)

**Rationale:** Snapshot approach ensures the offer reflects exactly what was quoted, even if prices change later. Same proven pattern as invoices.

### 3. PDF template

**Decision:** Dedicated `offers/offer.html` template, derived from `invoices/invoice.html` but with offer-specific changes:
- Title: "Offer" / "Angebot" instead of "Invoice" / "Rechnung"
- Offer number instead of invoice number
- "Valid until" date prominently displayed
- Notes/conditions section
- No tax breakdown for foreign customers (same VAT sentence logic as invoices)
- No ZUGFeRD XML embedding

**Rationale:** Reusing the invoice template layout ensures visual consistency. Customers see a familiar format.

### 4. Offer creation from forecast

**Decision:** One "Create Offer" button per billing event row in the ForecastTab. Clicking it calls a `createOffer` mutation that:
1. Takes `contractId` + `billingDate` as input
2. Computes the billing event via `get_billing_schedule()`
3. Snapshots line items and company data
4. Assigns an offer number
5. Creates the OfferRecord in `draft` status
6. Generates the PDF synchronously (offers are single-page, fast)
7. Returns the created offer ID for navigation

**Alternative considered:** Batch offer creation for all forecast rows. Deferred — can be added later if needed.

### 5. Email sending with additional recipients

**Decision:** Before sending, show a dialog that:
1. Pre-fills customer billing emails as recipients
2. Allows adding/removing recipients
3. Sends via the existing M365 email infrastructure
4. Stores all recipients in `email_sent_to`

**Rationale:** Offers often need to go to different people than invoices (procurement, decision makers). The dialog lets users adjust per-send without changing customer data.

### 6. Numbering scheme

**Decision:** `OfferNumberScheme` model — same structure as `InvoiceNumberScheme` (pattern, counter, reset period). Default pattern: `{YYYY}-{NNNN}` — fully configurable, user can add any prefix they want.

Reuse `InvoiceNumberService` logic via a shared base or duplicate the small numbering module (it's ~60 lines). Given the simplicity, duplicating into `offers/numbering.py` is cleaner than creating a shared abstraction.

### 7. Settings UI

**Decision:** Add "Offer Numbering" section to the existing invoice/company settings page. Same pattern as invoice numbering configuration.

## Risks / Trade-offs

- **Code duplication with invoices** — PDF generation, numbering, email sending will mirror invoice patterns. This is acceptable given the small module sizes (~60-100 lines each). A shared abstraction would add complexity for little benefit at this stage.
  → Mitigation: Keep the code structurally identical so future extraction into shared modules is straightforward.

- **Offer expiration** — Offers don't auto-expire. Users must manually change status.
  → Mitigation: Show visual indicators (red badge) for expired offers in the list. A future Celery periodic task could auto-expire.

- **Forecast tab changes** — Adding buttons to each row increases visual density.
  → Mitigation: Use a small icon button (not a full-width button). Show only when hovering or as a subtle action.

## Migration Plan

1. Create `offers` app with models and migrations
2. Add GraphQL schema (queries + mutations)
3. Add PDF template and generation service
4. Add email sending task
5. Add frontend routes, list, and detail components
6. Add "Create Offer" button to ForecastTab
7. Add numbering scheme settings UI

No data migration needed. No breaking changes. Feature is purely additive.

## Resolved Questions

- **PDF period display:** Show both — offer date + validity date AND the billing/service period for reference.
- **Blank offers:** No. Offers are always generated from a billing event (forecast row). Keeps it simple.
- **Numbering prefix:** Fully configurable via OfferNumberScheme (same pattern system as invoice and credit note numbering). Default pattern: `{YYYY}-{NNNN}`, user can set any prefix they want.
