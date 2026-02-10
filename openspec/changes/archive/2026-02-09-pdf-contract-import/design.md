## Context

Contracts are often created with a single aggregated line item, but PO confirmation PDFs contain the full breakdown: individual line items with quantities, unit prices, discounts, one-off fees, durations, and PO numbers. The system already has an Excel import service (`import_service.py`) that uses a proposal-based review workflow with `rapidfuzz` for customer/product matching. The PDF import feature follows a similar pattern but operates on a single contract (update flow) rather than bulk creation.

The backend uses Django 5 + Strawberry-GraphQL with multi-tenant isolation. The frontend is React + TypeScript + Apollo. PDF attachments are already uploadable via the `ContractAttachment` model. The Claude API will be used for structured extraction from PDFs.

## Goals / Non-Goals

**Goals:**
- Extract structured contract data from PO confirmation PDFs using Claude API
- Compare extracted data against existing contract items and metadata
- Fuzzy-match extracted line items to tenant's product catalog (reusing `rapidfuzz`)
- Let users review, adjust, and selectively import line items and metadata
- Handle discounts as a contract-level `discount_amount`, not as product-matched items

**Non-Goals:**
- Creating new contracts from PDFs (update-only for now)
- Persisting extraction results (transient — re-analyze if needed)
- Supporting non-PDF file formats (Excel import already exists)
- Auto-importing without user review
- OCR for scanned/image-only PDFs (Claude handles native PDF text)
- Multi-language PDF support (English and German are sufficient for now)

## Decisions

### 1. Claude API integration: direct API call with structured output

Use the `anthropic` Python SDK with Claude's vision/document capability to send the PDF and receive structured JSON. The prompt asks for a specific JSON schema covering line items, metadata, and totals.

**Why not a generic "document parser" abstraction?** This is a single-provider feature. Adding abstraction now would be over-engineering — if we need to swap LLMs later, the prompt and response parsing are the only parts that change, and they're isolated in one service file.

**API key storage:** Store `ANTHROPIC_API_KEY` as an environment variable (not per-tenant). This is an infrastructure-level key, not a user-facing integration like HubSpot or Clockodo. Add to `config/settings/base.py` as `ANTHROPIC_API_KEY = env("ANTHROPIC_API_KEY", default="")`.

### 2. Transient extraction results (no persistence)

Extraction results are returned directly from the GraphQL query and held in frontend state. They are not stored in the database.

**Why?** PDFs don't change. Re-analyzing is cheap (~$0.01-0.05 per call). Avoiding a new model keeps the schema simple. The frontend holds the extraction result in component state and sends selected items back via a mutation.

**Alternative considered:** Storing results in a `PdfAnalysisResult` model. Rejected because it adds model/migration complexity for data that's inherently ephemeral and reproducible.

### 3. Two-step GraphQL flow: analyze query + import mutation

**Step 1 — `analyzePdfAttachment(attachmentId)` query:** Reads the PDF file from disk, sends to Claude API, parses response, fuzzy-matches products, and returns the full extraction result with match suggestions.

**Step 2 — `importPdfAnalysis(contractId, items, metadata)` mutation:** Receives the user-reviewed items and metadata. Creates `ContractItem` records (with optional `ContractItemPrice`), updates contract fields (`po_number`, `min_duration_months`, `order_confirmation_number`, `discount_amount`).

**Why a query for analysis?** It's a read operation — it doesn't modify state. The mutation only fires when the user confirms import.

### 4. Product matching: reuse rapidfuzz pattern from import_service

Match extracted item descriptions against `Product.name` and `Product.netsuite_item_name` using `rapidfuzz.fuzz.WRatio`, same as the Excel import. Return top match with confidence score. Frontend shows the match and lets users override.

**Discount handling:** Lines identified as discounts (negative amounts, "discount"/"Rabatt" in description) are not matched to products. Instead, they map to `Contract.discount_amount`.

**Threshold:** Items with match confidence ≥ 80% are auto-suggested. Below that, shown as "no match" with manual product selection.

### 5. Frontend: inline review panel on contract detail page

When the user clicks "Analyze" on a PDF attachment, the analysis result appears as a full-width panel within the contract detail page (not a separate route or modal). This keeps context visible — the user can see existing contract items alongside extracted items.

The panel has three sections:
1. **Metadata comparison** — side-by-side showing extracted vs. current values for PO number, min duration, order confirmation number, discount
2. **Line items table** — extracted items with columns: description, quantity, unit price, period, matched product (dropdown), import checkbox
3. **Action bar** — "Import Selected" button, "Cancel" to dismiss

**Why not a modal?** The data is too complex for a modal. An inline panel allows scrolling and comparing with existing contract data visible above/below.

### 6. PDF reading: base64 to Claude API

The `ContractAttachment` model stores files on disk at `uploads/{tenant_id}/contracts/{contract_id}/{uuid}_{filename}`. Read the file, base64-encode it, and send as a document block in the Claude API message. Claude natively handles PDF content.

**File size limit:** Attachments are already capped at 10MB. Claude supports up to 100 pages per document. This is sufficient for PO confirmations.

### 7. Amendment handling for non-draft contracts

When importing items into an `active` contract, the existing `add_contract_item` mutation already creates `ContractAmendment` records automatically. The import mutation will reuse this logic by calling the same internal function, ensuring amendments are tracked consistently.

## Risks / Trade-offs

**[Claude API availability/cost]** → The API call is user-initiated and infrequent (once per PDF). Cost is negligible (~$0.01-0.05 per analysis). If the API is down, the user sees an error and can retry. No background jobs or queues needed.

**[Extraction accuracy]** → LLM extraction may misparse prices, quantities, or item descriptions. Mitigation: mandatory user review before import. The comparison view makes errors visible. Users can edit values before importing.

**[Product matching confidence]** → Fuzzy matching may suggest wrong products. Mitigation: show confidence score, allow manual override via product dropdown. Items below 80% threshold shown without a match suggestion.

**[No rollback for imported items]** → Once imported, items are standard `ContractItem` records. Users can delete them individually. For active contracts, amendments are created, providing an audit trail.

**[Environment variable for API key]** → If different tenants need different API keys in the future, this would need to move to tenant config. For now, a single key is sufficient since this is a single-company deployment.

## Open Questions

- Should the extraction prompt handle multiple languages (German + English POs), or is English-only sufficient for the MVP? (Leaning toward both, since Claude handles multilingual content natively.)
