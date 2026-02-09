## Context

The invoice system has a `InvoiceTemplateReference` model that stores uploaded reference PDFs but never reads or processes them. Users must manually enter ~20 fields of company legal data and configure template styling from scratch. The project already uses the Anthropic Claude API for PDF analysis in the contract import flow (`apps/contracts/services/pdf_analysis.py`), which sends PDFs as base64 documents and receives structured JSON back.

**Current state:**
- `CompanyLegalData` model: 20+ fields (company name, address, tax IDs, register info, directors, bank details, share capital, tax rate)
- `InvoiceTemplate` model: accent_color, header_text, footer_text, logo
- `InvoiceTemplateReference` model: file, original_filename, file_size (no extraction fields)
- `pdf_analysis.py` (contracts): Established pattern using `anthropic.Anthropic` client, base64 PDF document type, JSON extraction prompt, 24h Redis caching

## Goals / Non-Goals

**Goals:**
- Extract all CompanyLegalData fields from a reference invoice PDF using Claude vision
- Extract accent/brand color as a hex value
- Extract layout description (logo position, footer column structure)
- Store extraction results on the reference so re-extraction isn't needed
- Let users review extracted data before applying it to settings
- Follow the established `pdf_analysis.py` pattern (single API call, JSON response, caching)

**Non-Goals:**
- Pixel-perfect layout replication from arbitrary PDFs (offer predefined layout presets instead)
- Full WYSIWYG template editor
- OCR fallback for scanned/image-only PDFs (Claude vision handles these natively)
- Multi-page invoice analysis (use first page only — legal data and styling are always on page 1)

## Decisions

### 1. Single Claude API call with structured JSON output

**Decision**: Send the full PDF to Claude with a prompt requesting a single JSON object containing all extractable fields.

**Why**: Matches the existing contract PDF analysis pattern. One call extracts legal data, colors, and layout simultaneously. Claude's vision understands both text content and visual styling.

**Alternatives considered**:
- *pdfplumber + regex*: Fragile, can't extract colors or layout, fails on non-standard PDFs
- *Multiple specialized calls*: Unnecessary cost and latency for data that's all on one page
- *pdfplumber for text + Claude for layout*: Extra dependency for marginal benefit

### 2. Store extraction results as JSONField on InvoiceTemplateReference

**Decision**: Add `extracted_data` (JSONField, nullable) and `extraction_status` (CharField: pending/completed/failed) to the existing `InvoiceTemplateReference` model.

**Why**: Keeps extraction results co-located with the source PDF. Avoids re-extraction on every view. Simple migration on an existing model.

**Alternatives considered**:
- *Separate ExtractionResult model*: Over-normalized for a 1:1 relationship
- *Cache-only (Redis)*: Loses data on cache eviction; extraction results should be durable

### 3. Extraction prompt structure

**Decision**: The prompt requests a JSON object with three top-level sections:

```json
{
  "legal_data": {
    "company_name": "...",
    "street": "...",
    "zip_code": "...",
    "city": "...",
    "country": "...",
    "tax_number": "...",
    "vat_id": "...",
    "commercial_register_court": "...",
    "commercial_register_number": "...",
    "managing_directors": ["..."],
    "bank_name": "...",
    "iban": "...",
    "bic": "...",
    "phone": "...",
    "email": "...",
    "website": "...",
    "share_capital": "...",
    "default_tax_rate": "19.00"
  },
  "design": {
    "accent_color": "#hex",
    "header_text": "...",
    "footer_text": "..."
  },
  "layout": {
    "logo_position": "top-left|top-right|top-center",
    "footer_columns": 2,
    "description": "Free text layout description"
  }
}
```

**Why**: The `legal_data` keys match `CompanyLegalData` model fields exactly, enabling direct mapping. The `design` section maps to `InvoiceTemplate` fields. The `layout` section is informational for now (future layout presets).

### 4. Review-then-apply UI flow

**Decision**: After extraction, show results in a review panel on the template settings page. User clicks "Apply to Company Data" or "Apply to Template" to populate the respective forms. Navigation to CompanyDataSettings passes extracted data via React Router state.

**Why**: Users must review and confirm before overwriting existing data. Separating "extract" from "apply" prevents accidental overwrites.

**Alternatives considered**:
- *Auto-apply on upload*: Dangerous — could overwrite carefully entered data
- *Modal confirmation*: Too little visibility into what's being changed
- *Dedicated extraction page*: Unnecessary navigation; extraction is part of template setup

### 5. GraphQL mutation with async-feel pattern

**Decision**: `analyzeReferencePdf(referenceId: Int!)` mutation that calls Claude synchronously and returns the extracted data. The mutation stores results on the reference and returns them.

**Why**: Claude API calls for a single-page PDF complete in 2-5 seconds. Synchronous is simpler than polling. The frontend shows a loading spinner during the call.

**Alternatives considered**:
- *Background task + polling*: Overkill for 2-5 second operations
- *WebSocket push*: No WebSocket infrastructure exists in the project

## Risks / Trade-offs

**[Claude API latency]** → 2-5 seconds per extraction. Mitigated by: storing results so extraction only happens once per reference PDF, showing loading state in UI.

**[Extraction accuracy]** → Claude may miss or misparse some fields from complex invoice layouts. Mitigated by: review step before applying, all fields are editable after apply, null/empty fields clearly shown.

**[API cost]** → One Sonnet call per PDF (~$0.01-0.03 per extraction). Mitigated by: results stored durably, no re-extraction needed. Negligible at expected volume (1-5 reference PDFs per tenant).

**[Existing data overwrite]** → User might accidentally apply extracted data over manually corrected values. Mitigated by: explicit "Apply" action with confirmation, extraction results shown as a preview first.

**[ANTHROPIC_API_KEY not configured]** → Extraction silently unavailable. Mitigated by: hide extraction UI when key not configured, same pattern as contract PDF analysis.
