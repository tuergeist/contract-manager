## 1. Backend Setup

- [x] 1.1 Add `anthropic` package to `backend/pyproject.toml` dependencies
- [x] 1.2 Add `ANTHROPIC_API_KEY` setting to `config/settings/base.py` (read from env, default empty string)
- [x] 1.3 Rebuild backend Docker image to install the new dependency

## 2. PDF Analysis Service

- [x] 2.1 Create `backend/apps/contracts/services/pdf_analysis.py` with the Claude API extraction function: read PDF from disk, base64-encode, send to Claude API with structured output prompt, parse JSON response into dataclasses (ExtractedLineItem, ExtractedMetadata, PdfAnalysisResult)
- [x] 2.2 Implement the extraction prompt covering: line items (description, quantity, unit_price, price_period, is_one_off), metadata (po_number, order_confirmation_number, min_duration_months), discount identification, totals — supporting English and German PDFs
- [x] 2.3 Implement product matching in the analysis service: fuzzy-match each extracted item description against tenant's Product.name and Product.netsuite_item_name using rapidfuzz WRatio, return top match with confidence score, skip matching for discount lines
- [x] 2.4 Implement comparison logic: compare extracted items against existing ContractItems on the contract, mark items as "new" or "existing" with price difference indicators

## 3. GraphQL Schema

- [x] 3.1 Add GraphQL types to `backend/apps/contracts/schema.py`: PdfExtractedItem, PdfExtractedMetadata, PdfProductMatch, PdfComparisonItem, PdfAnalysisResult
- [x] 3.2 Add `analyze_pdf_attachment(attachment_id: ID!) -> PdfAnalysisResult` query: validate attachment exists, is PDF, belongs to user's tenant; call analysis service; return results with product matches and comparison
- [x] 3.3 Add `import_pdf_analysis` mutation with input: contract_id, list of items (description, quantity, unit_price, price_period, is_one_off, product_id), metadata fields (po_number, min_duration_months, order_confirmation_number, discount_amount). Create ContractItems via existing add-item logic (with amendment tracking for active contracts), update contract metadata fields atomically

## 4. Backend Tests

- [x] 4.1 Write unit tests for the extraction prompt/parsing (mock Claude API response, verify dataclass output)
- [x] 4.2 Write unit tests for product matching (high confidence, low confidence, discount exclusion)
- [x] 4.3 Write unit tests for comparison logic (new items, existing items, metadata diffs)
- [x] 4.4 Write integration tests for the GraphQL query (mock Claude API, verify full response shape)
- [x] 4.5 Write integration tests for the import mutation (verify ContractItems created, metadata updated, amendments for active contracts)

## 5. Translations

- [x] 5.1 Add English translations to `frontend/src/locales/en.json` under `pdfAnalysis.*` (analyze button, loading, error messages, column headers, import button, success/failure messages, metadata labels)
- [x] 5.2 Add German translations to `frontend/src/locales/de.json` under `pdfAnalysis.*`

## 6. Frontend: Analysis Review Panel

- [x] 6.1 Create `frontend/src/features/contracts/PdfAnalysisPanel.tsx` component: accepts contractId and attachmentId props, calls analyzePdfAttachment query, displays loading/error states
- [x] 6.2 Implement metadata comparison section: side-by-side display of extracted vs. current values for PO number, order confirmation number, min duration, discount amount — each with import checkbox
- [x] 6.3 Implement extracted line items table: columns for description, quantity, unit price, period, matched product (dropdown with confidence), status (new/existing), import checkbox — new items checked by default, existing items unchecked and disabled
- [x] 6.4 Implement product override dropdown: populate from tenant's product list, allow user to change the auto-matched product for any item
- [x] 6.5 Implement "Import Selected" action: collect checked items and metadata, call importPdfAnalysis mutation, show success/error, refresh contract data on success, dismiss panel
- [x] 6.6 Implement "Cancel" action to dismiss the panel without changes

## 7. Frontend: Attachments Tab Integration

- [x] 7.1 Add "Analyze" button to PDF attachments in the attachments tab (only shown for .pdf files)
- [x] 7.2 Wire the Analyze button to open the PdfAnalysisPanel with the selected attachment ID
- [x] 7.3 Add GraphQL queries and mutations for analyzePdfAttachment and importPdfAnalysis to the frontend

## 8. End-to-End Verification

- [x] 8.1 Run `make test-back` to verify all backend tests pass
- [x] 8.2 Run `make build` to verify frontend compiles without TypeScript errors
- [ ] 8.3 Manual test: upload a PO confirmation PDF to a contract, click Analyze, review results, import items, verify contract items and metadata updated correctly
