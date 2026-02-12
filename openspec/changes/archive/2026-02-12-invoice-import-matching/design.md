## Context

We issue invoices to customers but currently have no way to track them centrally or match them against incoming bank payments. The existing infrastructure includes:
- **Object storage** for file storage (S3-compatible)
- **Claude API integration** for PDF analysis (used for contract PDF extraction)
- **Banking module** with BankTransaction model containing booking_text, counterparty, and amount
- **Customer model** with name field for matching

The goal is to import existing outgoing invoices, extract key data via AI, and match incoming payments to track receivables.

## Goals / Non-Goals

**Goals:**
- Import outgoing invoice PDFs and store them in object storage
- Extract invoice number, total amount, invoice date, and customer name via AI
- Match extracted customer to existing customers (with fuzzy matching)
- Create invoice records with metadata and payment status tracking
- Match incoming bank transactions (credits) to invoices automatically
- Support multiple matching strategies (invoice number in booking text, amount+customer)
- Allow manual matching as fallback

**Non-Goals:**
- Generating new invoices (existing capability)
- Handling incoming invoices (accounts payable) - future scope
- Real-time payment notifications
- Multi-currency invoice matching (EUR only for now)
- Partial payment tracking (invoice is either paid or unpaid)

## Decisions

### 1. Invoice model separate from invoice generation

**Decision:** Create a new `ImportedInvoice` model distinct from the existing invoice generation system.

**Rationale:**
- Existing invoice system is for generating new invoices with templates
- Imported invoices are historical records from external sources
- Different data requirements (imported has PDF, generated has line items)
- Keeps concerns separated; can unify later if needed

**Alternatives considered:**
- Extend existing Invoice model: Would conflate two different use cases

### 2. AI extraction uses existing Claude infrastructure

**Decision:** Reuse the `extract_from_invoice_pdf` pattern from `apps/invoices/pdf_analysis.py` with a new extraction prompt.

**Rationale:**
- Proven pattern already in codebase
- Same Claude API key and client setup
- Just needs different prompt for extracting invoice number, amount, date, customer

**Extraction fields:**
- `invoice_number`: String (e.g., "2025-001234")
- `invoice_date`: Date
- `total_amount`: Decimal (gross amount including tax)
- `currency`: String (default EUR)
- `customer_name`: String (as printed on invoice)

### 3. Customer matching uses trigram similarity

**Decision:** Use PostgreSQL `pg_trgm` extension for fuzzy customer name matching.

**Rationale:**
- Already available in PostgreSQL
- Handles typos, abbreviations (GmbH vs. GmbH.), word order differences
- Returns similarity score for confidence threshold
- Fast with GIN index on customer names

**Matching logic:**
1. Exact match on customer name → auto-link
2. Similarity > 0.6 → suggest match, require confirmation
3. Similarity < 0.6 → manual selection required

### 4. Payment matching as separate service with pluggable strategies

**Decision:** Create a `PaymentMatcher` service with strategy pattern.

**Rationale:**
- Different customers use different reference formats
- Need flexibility to add new strategies without code changes
- Can run multiple strategies and rank by confidence

**Strategies (in priority order):**
1. **Invoice number in booking text**: Fuzzy search for invoice number pattern in `booking_text` field
2. **Amount + Customer match**: Exact amount match + counterparty matches customer (via linked customer)
3. **Manual match**: User explicitly links transaction to invoice

**Match model:**
```
InvoicePaymentMatch:
  - invoice: FK to ImportedInvoice
  - transaction: FK to BankTransaction
  - match_type: enum (invoice_number, amount_customer, manual)
  - confidence: Decimal (0-1)
  - matched_at: DateTime
  - matched_by: FK to User (for manual)
```

### 5. Counterparty-Customer linking

**Decision:** Add optional `customer` FK to `Counterparty` model.

**Rationale:**
- Counterparties are extracted from bank transactions
- Customers are our business contacts
- Linking them enables amount+customer matching strategy
- One counterparty → one customer (many counterparties can link to same customer)

### 6. Invoice status derived from matches

**Decision:** Invoice payment status is computed, not stored.

**Rationale:**
- Avoids sync issues between match records and status field
- `is_paid` = invoice has at least one payment match
- Can extend later for partial payments by summing match amounts

## Risks / Trade-offs

**[Accuracy] AI extraction may misread invoice data** → Show extraction results for user review before saving; allow manual correction

**[Matching] False positive matches** → Require confidence threshold; show match reason for verification; allow unlinking

**[Performance] Fuzzy search on large transaction sets** → Run matching as background job; index booking_text; limit search window to ±30 days of invoice date

**[Duplicates] Same invoice imported twice** → Dedupe on invoice_number + customer within tenant; warn on potential duplicates

## Open Questions

- Should we support batch import (ZIP of PDFs)?
- What's the retention policy for imported invoice PDFs?
- Should matching run automatically on new transactions, or on-demand only?
