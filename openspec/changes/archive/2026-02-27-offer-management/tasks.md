## 1. Backend: Django App & Models

- [x] 1.1 Create `offers` Django app (`backend/apps/offers/`) with `apps.py`, `__init__.py`, add to `INSTALLED_APPS`
- [x] 1.2 Create `OfferRecord` model: offer_number, contract (FK), customer (FK), offer_date, valid_until, billing_date, period_start, period_end, total_net, tax_rate, tax_amount, total_gross, line_items_snapshot (JSON), company_data_snapshot (JSON), status (draft/sent/accepted/rejected/cancelled), pdf_file, customer_name, contract_name, notes, vat_sentence, email_sent_at, email_sent_to (JSON), email_message_id. Unique constraint on (tenant, offer_number).
- [x] 1.3 Create `OfferNumberScheme` model: tenant (OneToOne), pattern (default `{YYYY}-{NNNN}`), next_counter, reset_period (yearly/monthly/never), last_reset_year, last_reset_month
- [x] 1.4 Create migration, run `makemigrations` and `migrate`
- [x] 1.5 Create `offers/numbering.py` — `OfferNumberService` with `get_next_number(offer_date)` (same logic as `InvoiceNumberService`)

## 2. Backend: Offer Service

- [x] 2.1 Create `offers/services.py` — `OfferService(tenant)` with `create_offer(contract_id, billing_date)`:
  - Compute billing event via `contract.get_billing_schedule()`
  - Classify customer (domestic/eu/non_eu), calculate tax
  - Snapshot line items and company data
  - Assign offer number
  - Create OfferRecord (status=draft)
  - Generate PDF and store in pdf_file
  - Return the created record
- [x] 2.2 Add offer PDF labels to services (DE: "Angebot", EN: "Offer", plus "Valid until"/"Gültig bis", per_month labels)
- [x] 2.3 Create `offers/templates/offers/offer.html` — derived from `invoices/invoice.html` but with offer-specific title, offer number, offer date, valid until, billing period, notes section. No ZUGFeRD.
- [x] 2.4 Add `generate_pdf(offer_record, language)` method to OfferService — render HTML template, convert to PDF via WeasyPrint

## 3. Backend: GraphQL Schema

- [x] 3.1 Create `offers/schema.py` — `OfferRecordType` with all fields, `OfferPage` for pagination
- [x] 3.2 Add `offers` query: paginated list with filters (search, status, dateFrom, dateTo, sortBy, sortOrder)
- [x] 3.3 Add `offer(id: Int!)` query: single offer by ID (tenant-scoped)
- [x] 3.4 Add `createOffer(contractId: Int!, billingDate: Date!)` mutation → calls OfferService.create_offer
- [x] 3.5 Add `updateOfferStatus(id: Int!, status: String!)` mutation with transition validation
- [x] 3.6 Add `updateOffer(id: Int!, validUntil: Date, notes: String)` mutation for draft offers
- [x] 3.7 Add `deleteOffer(id: Int!)` mutation (draft only)
- [x] 3.8 Register offer queries and mutations in root schema (`config/schema.py`)

## 4. Backend: Email Sending

- [x] 4.1 Create `offers/tasks.py` — `send_offer_email_task(offer_id, recipients, user_id)` Celery task: validate offer has PDF, send via M365 with offer-specific subject/body template, update email tracking fields, set status to sent
- [x] 4.2 Add `sendOfferEmail(id: Int!, recipients: [String!]!)` mutation that dispatches the task

## 5. Backend: Offer Number Settings

- [x] 5.1 Add `offerNumberScheme` query to return current scheme (or defaults)
- [x] 5.2 Add `updateOfferNumberScheme(pattern, resetPeriod, nextCounter)` mutation

## 6. Backend: Tests

- [x] 6.1 Test OfferNumberService: pattern rendering, counter increment, yearly reset
- [x] 6.2 Test OfferService.create_offer: creates record with correct snapshots, amounts, tax
- [x] 6.3 Test status transitions: valid and invalid transitions
- [x] 6.4 Test GraphQL queries: offer list with filters, single offer, tenant isolation
- [x] 6.5 Test GraphQL mutations: createOffer, updateOfferStatus, deleteOffer (draft only)

## 7. Frontend: Offer List Page

- [x] 7.1 Create `frontend/src/features/offers/OfferList.tsx` — table with columns: offer number, customer, contract, offer date, valid until, total gross, status. Search, status filter, pagination. Expired badge for past-validity draft/sent offers.
- [x] 7.2 Add route `/offers` in router, add "Offers"/"Angebote" to main navigation
- [x] 7.3 Add i18n keys for offer list (EN + DE): page title, column headers, status labels, empty state, filters

## 8. Frontend: Offer Detail Page

- [x] 8.1 Create `frontend/src/features/offers/OfferDetail.tsx` — metadata card (offer number, date, valid until, status, customer link, contract link, period, notes), line items table, PDF preview iframe, download button
- [x] 8.2 Add status action buttons: Send (draft), Mark Accepted / Mark Rejected / Cancel (sent), Delete (draft with confirmation)
- [x] 8.3 Add route `/offers/:id` in router
- [x] 8.4 Add i18n keys for offer detail (EN + DE): section headers, action buttons, status labels

## 9. Frontend: Send Offer Dialog

- [x] 9.1 Create `SendOfferDialog` component: pre-fill customer billing emails, allow adding/removing recipients, confirm button calls `sendOfferEmail` mutation
- [x] 9.2 Wire "Send" button on offer detail to open the dialog

## 10. Frontend: Forecast Tab Integration

- [x] 10.1 Add `createOffer` mutation call to ForecastTab in ContractDetail.tsx
- [x] 10.2 Add "Create Offer" icon button to each billing event row (small icon, not full button)
- [x] 10.3 On success, navigate to `/offers/:id`
- [x] 10.4 If offer already exists for contract+billingDate, show link to existing offer instead
- [x] 10.5 Add i18n keys: "Create Offer"/"Angebot erstellen", "View Offer"/"Angebot anzeigen"

## 11. Frontend: Offer Number Settings

- [x] 11.1 Add "Offer Numbering" section to company settings page (same UI pattern as invoice/storno numbering): pattern input, reset period select, next counter input
- [x] 11.2 Wire to `offerNumberScheme` query and `updateOfferNumberScheme` mutation
- [x] 11.3 Add i18n keys for offer numbering settings (EN + DE)
