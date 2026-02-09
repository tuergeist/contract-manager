## Why

Contracts are often created manually with a single aggregated line item (e.g. "SaaS: 3,236.00 EUR/month"), but the actual PO confirmation PDF contains the full breakdown: individual line items with quantities, unit prices, discounts, one-off fees, minimum durations, and PO numbers. Manually entering this data is tedious and error-prone. By analyzing uploaded PDFs with an LLM (Claude API), we can extract structured data, compare it against the existing contract, highlight differences, and let users import missing items in one click.

## What Changes

- **PDF analysis via Claude API**: When a PDF attachment exists on a contract, users can trigger analysis that extracts structured data (line items, prices, quantities, billing periods, discounts, one-off items, PO number, minimum duration, order confirmation number).
- **Comparison view**: Extracted data is compared against the existing contract's items, prices, and metadata. Differences and missing items are highlighted.
- **Product matching**: Extracted line items are fuzzy-matched against the tenant's existing product catalog. Discounts are handled separately (not matched to products).
- **Selective import**: Users review the extraction results and can import missing line items (with matched products and pricing), update contract metadata (PO number, min duration, order confirmation number), and adjust discount amounts.
- **Contract detail integration**: The analysis UI is accessible from the contract detail page, triggered from an uploaded PDF attachment.

## Capabilities

### New Capabilities
- `pdf-contract-analysis`: LLM-powered extraction of structured contract data from PDF attachments. Covers the Claude API integration, extraction prompt, structured output parsing, and product fuzzy matching.
- `pdf-import-review-ui`: Frontend UI for reviewing extracted vs. existing contract data, showing diffs, confirming product matches, and selectively importing line items and metadata into the contract.

### Modified Capabilities
- `contract-attachments`: Add an "Analyze" action button on PDF attachments to trigger extraction and navigate to the review UI.

## Impact

- **Backend**: New service module for PDF analysis (Claude API call, structured output parsing, product matching logic). New GraphQL mutations for triggering analysis and importing reviewed items. Requires `anthropic` Python package. Claude API key stored in tenant config or environment variable.
- **Frontend**: New components for the analysis/review UI on the contract detail page. Modified attachments tab to add analyze action on PDFs.
- **External dependencies**: Anthropic Claude API (usage-based cost per analysis).
- **Data model**: No new models required — extracted data is transient (returned from the analysis query, not persisted until import). Import creates standard ContractItem/ContractItemPrice records.
