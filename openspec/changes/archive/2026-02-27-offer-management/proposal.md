## Why

Customers need formal offers/quotes before contracts are signed or renewed. Currently there's no way to generate offers from Contract Manager — sales has to create them manually outside the system. Since the billing schedule already calculates exactly what will be invoiced, offers should be generatable directly from the revenue forecast tab with one click per billing event line.

## What Changes

- New `OfferRecord` model with numbering scheme, status lifecycle, line items snapshot, and PDF storage
- "Create Offer" button on each row of the revenue forecast tab (works for both draft and active contracts)
- Offer list page (`/offers`) with search, filters, and pagination — similar to invoice list
- Offer detail page (`/offers/:id`) with metadata, line items, PDF preview, and actions
- Offer PDF generation using a dedicated template (similar to invoice PDF but with offer-specific fields like validity date)
- Offer email sending via M365 with the ability to add additional recipients before sending
- Offer numbering scheme configurable in settings (separate from invoice numbering)

## Capabilities

### New Capabilities
- `offer-record`: Offer data model, numbering scheme, status lifecycle (draft → sent → accepted/rejected/expired), and GraphQL API
- `offer-generation`: Creating offers from billing schedule events, snapshotting line items and company data, PDF rendering with dedicated template
- `offer-list-detail`: Frontend list and detail pages for offers, following the invoice UI pattern
- `offer-sending`: Email sending with recipient selection (customer billing emails + additional recipients dialog)

### Modified Capabilities
- `revenue-forecast-invoice-matching`: Add "Create Offer" button to each forecast row

## Impact

- Backend: New `offers` Django app (or extend `invoices` app) with OfferRecord model, OfferNumberScheme, migrations, GraphQL types/mutations/queries, PDF template, email task
- Frontend: New `/offers` and `/offers/:id` routes, OfferList and OfferDetail components, "Create Offer" button in ForecastTab
- Settings: Offer numbering scheme configuration (pattern, reset period) in company settings
- Email: New offer-specific email templates (subject/body) with M365 sending
- No breaking changes to existing invoice functionality
