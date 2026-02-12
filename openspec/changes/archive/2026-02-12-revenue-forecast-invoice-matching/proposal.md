## Why

The revenue forecast tab shows expected billing dates and amounts for a contract, but there's no visibility into whether those expected revenues have actually been invoiced or paid. Users need to see at a glance which forecast entries have corresponding invoices and their payment status.

## What Changes

- Add an "Invoice" column to the revenue forecast table in ContractDetail
- For each forecast event (billing date), match against imported invoices by:
  - Contract ID match
  - Date proximity (invoice date within billing period or close to expected date)
  - Amount matching (similar total)
- Display invoice number as a link to the invoice/PDF
- Display payment status badge (paid/unpaid) next to the invoice

## Capabilities

### New Capabilities
- `revenue-forecast-invoice-matching`: Logic to match forecast billing events with imported invoices and display invoice/payment status in the forecast table

### Modified Capabilities
_(none - this is additive UI enhancement)_

## Impact

- **Backend**: May need to extend `billingSchedule` query to include matched invoice data, or create a new query/resolver to match invoices to forecast dates
- **Frontend**: `ForecastTab` component in ContractDetail.tsx - add Invoice column with invoice number link and paid/unpaid badge
- **GraphQL**: Extend BillingScheduleEvent type or add invoice matching field
