## Why

The sidebar has grown with separate entries for closely related features (Invoices / Invoice Export, Liquidity Forecast / Revenue Forecast). Consolidating them reduces nav clutter and groups related functionality where users expect it.

## What Changes

- Remove the dedicated "Invoice Export" sidebar entry
- Add an "Export" button on the Invoices page that navigates to (or opens) the export functionality
- Remove separate "Liquidity Forecast" and "Revenue Forecast" sidebar entries
- Add a single "Forecasts" sidebar entry leading to a tabbed page with Liquidity and Revenue tabs
- Update routes: `/forecast` and `/liquidity-forecast` merge into `/forecasts` with tab routing

## Capabilities

### New Capabilities
- `unified-forecasts-page`: A single forecasts page with tabs for liquidity and revenue forecasts

### Modified Capabilities
- `invoice-export`: Export is no longer a standalone nav entry; it becomes accessible from the Invoices page via a button
- `liquidity-forecast-ui`: Liquidity forecast moves from a standalone page into a tab on the unified forecasts page

## Impact

- **Frontend routes**: Remove `/invoices/export`, `/forecast`, `/liquidity-forecast`; add `/forecasts` with tab params
- **Sidebar**: 4 nav entries reduced to 2 (Invoices, Forecasts)
- **Components**: New `ForecastsPage` wrapper with tabs; `InvoiceList` gains an export button
- **Translations**: New keys for forecasts tabs; remove unused nav keys
- **No backend changes** required
