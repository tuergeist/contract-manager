## Why

Customers need formal offers (Angebote) before signing contracts. Currently, there's no way to generate offers from the system — sales staff create them manually outside the tool, leading to inconsistent formatting, missing data, and no audit trail. Adding offer management completes the pre-contract workflow and ties directly into the existing billing schedule and revenue forecast.

## What Changes

- New `offers` Django app with `OfferRecord` model (frozen snapshots of line items, company data, tax calculation) and `OfferNumberScheme` for configurable numbering
- Offer creation from billing schedule events in the revenue forecast tab — reuses existing billing calculation logic
- Offer PDF generation via WeasyPrint (derived from invoice template, with offer-specific labels and validity date)
- Offer email sending via M365 Graph API with recipient selection dialog
- Full offer lifecycle: draft → sent → accepted/rejected/cancelled
- Offer list page (`/offers`) with search, status filter, and pagination
- Offer detail page (`/offers/:id`) with metadata, line items, PDF preview, and status actions
- Offer number settings in company settings (same pattern as invoice/storno numbering)
- GraphQL queries and mutations for all offer operations
- i18n support (DE + EN) for all offer UI

## Capabilities

### New Capabilities
- `offer-record`: OfferRecord model with frozen snapshots, numbering scheme, and status lifecycle
- `offer-generation`: Create offers from billing schedule events with tax calculation and PDF generation
- `offer-list-detail`: Offer list page and offer detail page with full CRUD
- `offer-sending`: Send offer PDF via email with recipient selection

### Modified Capabilities

(none)

## Impact

- **Backend**: New `apps/offers/` Django app, new models + migration, new GraphQL types/queries/mutations, Celery task for email sending
- **Frontend**: New `features/offers/` module (OfferList, OfferDetail, SendOfferDialog), new route `/offers` + `/offers/:id`, navigation update, forecast tab integration, company settings extension
- **Dependencies**: Reuses existing billing schedule, tax classification, WeasyPrint PDF, M365 email infrastructure
- **APIs**: New GraphQL queries (`offers`, `offer`, `offerNumberScheme`) and mutations (`createOffer`, `updateOffer`, `updateOfferStatus`, `deleteOffer`, `sendOfferEmail`, `updateOfferNumberScheme`)
