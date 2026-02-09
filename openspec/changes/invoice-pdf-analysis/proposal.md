## Why

Users currently must manually enter all company legal data (address, tax numbers, Handelsregister, managing directors, bank details, etc.) and configure invoice template styling from scratch. Most companies already have existing invoices that contain all this information. Uploading a reference invoice and automatically extracting this data eliminates tedious manual entry and ensures accuracy. The existing reference PDF upload feature stores files but does nothing with them.

## What Changes

- **Invoice PDF analysis service**: Upload a reference invoice PDF, send it to the Claude API (already available as a project dependency), and extract structured data: company legal fields, accent/brand colors, and layout characteristics.
- **Auto-populate CompanyLegalData**: Extracted legal fields (company name, address, tax number, VAT ID, Handelsregister, Geschäftsführer, bank details, Stammkapital) pre-fill the CompanyLegalData form for user review and confirmation.
- **Auto-populate template settings**: Extracted accent color fills the template accent color field. Layout characteristics (logo position, footer structure) inform template layout selection.
- **Extraction status tracking**: The `InvoiceTemplateReference` model gains fields to track extraction status and store extracted data as JSON, so re-extraction isn't needed.
- **Frontend extraction UI**: After uploading a reference PDF, user can trigger "Extract Data" which shows extracted fields in a review panel before applying them to settings.

## Capabilities

### New Capabilities
- `invoice-pdf-analysis`: Covers the Claude API-based extraction of legal data, colors, and layout from uploaded reference invoice PDFs, including the extraction prompt, result storage, and the frontend review/apply workflow.

### Modified Capabilities
- `invoice-export`: Invoice template settings page gains an extraction trigger and review panel for applying extracted data from reference PDFs.

## Impact

- **Backend**: New service module `apps/invoices/pdf_analysis.py`, updated `InvoiceTemplateReference` model (new fields for extraction results), new GraphQL mutation for triggering extraction, updated schema types.
- **Frontend**: Updated `TemplateSettings.tsx` with extraction UI, updated `CompanyDataSettings.tsx` to accept pre-filled data via URL params or shared state.
- **Dependencies**: Uses existing `anthropic` Python package and `ANTHROPIC_API_KEY` setting. Follows established pattern from `apps/contracts/services/pdf_analysis.py`.
- **API costs**: Each extraction is one Claude API call per PDF (~one page of content). Cached after first extraction.
