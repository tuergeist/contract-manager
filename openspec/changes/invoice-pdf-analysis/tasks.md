## 1. Backend Model & Migration

- [x] 1.1 Add `extracted_data` (JSONField, null=True, blank=True) and `extraction_status` (CharField, choices: pending/completed/failed, default blank) to `InvoiceTemplateReference` model
- [x] 1.2 Generate and run migration for the new fields

## 2. Backend PDF Analysis Service

- [x] 2.1 Create `apps/invoices/pdf_analysis.py` with extraction prompt requesting structured JSON (legal_data, design, layout sections) matching CompanyLegalData model fields
- [x] 2.2 Implement `extract_from_invoice_pdf(pdf_data: bytes) -> dict` function: base64-encode PDF, send to Claude API as document, parse JSON response (following `apps/contracts/services/pdf_analysis.py` pattern)
- [x] 2.3 Implement `analyze_reference(reference: InvoiceTemplateReference) -> dict` function: read file, call extract function, update extracted_data and extraction_status on the reference, handle errors (set status to "failed")
- [x] 2.4 Write tests for extraction service: mock Claude API response, verify JSON parsing, verify status updates on success/failure, verify missing fields return null

## 3. Backend GraphQL Schema

- [x] 3.1 Add `extractionStatus` and `extractedData` fields to `InvoiceTemplateReferenceType`
- [x] 3.2 Add `pdfAnalysisAvailable` query field (returns true if ANTHROPIC_API_KEY is configured)
- [x] 3.3 Add `analyzeReferencePdf(referenceId: Int!)` mutation: loads reference, calls analyze_reference, returns extraction result with success/error
- [x] 3.4 Add permission check (settings.write) on the analyze mutation
- [x] 3.5 Write tests for GraphQL mutation: successful extraction, failed extraction, permission denied, reference not found

## 4. Frontend: Extraction Controls on Template Settings

- [x] 4.1 Update TEMPLATE_QUERY to include `extractionStatus` and `extractedData` on reference items, and add `pdfAnalysisAvailable` query
- [x] 4.2 Add `ANALYZE_REFERENCE` GraphQL mutation
- [x] 4.3 Add "Extract Data" button to each reference PDF row (visible only when pdfAnalysisAvailable is true)
- [x] 4.4 Show extraction status indicator per reference (completed: green check, failed: red X with retry button, pending/in-progress: spinner)
- [x] 4.5 Add loading state during extraction (disable button, show spinner, 2-5 second expected duration)

## 5. Frontend: Extraction Review Panel

- [x] 5.1 Create ExtractionReviewPanel component showing extracted data in three sections: Legal Data, Design, Layout
- [x] 5.2 Display legal_data fields in a readable key-value list, marking null fields as "not found" (grayed out)
- [x] 5.3 Display accent_color as a color swatch with hex value, show header_text and footer_text
- [x] 5.4 Display layout description (logo position, footer columns, free text)
- [x] 5.5 Add "View Results" button on completed references that toggles the review panel open/closed

## 6. Frontend: Apply Extracted Data

- [x] 6.1 Add "Apply to Company Data" button in review panel that navigates to `/settings/company-data` with extracted legal_data passed via React Router state
- [x] 6.2 Update CompanyDataSettings to read React Router location state and pre-fill form fields with extracted values (only non-null values, preserve existing values for null fields)
- [x] 6.3 Add "Apply to Template" button in review panel that updates accent_color, header_text, footer_text fields on the current template settings form (unsaved, user must click Save)
- [x] 6.4 Add German and English translations for all new UI elements (extraction buttons, review panel labels, apply buttons, status indicators, error messages)

## 7. Testing

- [x] 7.1 Write backend test: extraction prompt produces expected JSON structure from mocked Claude response
- [x] 7.2 Write backend test: analyze_reference updates model fields correctly on success and failure
- [x] 7.3 Write backend test: GraphQL mutation returns extracted data and respects permissions
- [x] 7.4 Write frontend E2E test: upload reference PDF, trigger extraction, view results in review panel, apply to company data
