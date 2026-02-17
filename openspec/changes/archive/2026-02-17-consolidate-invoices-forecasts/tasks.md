## 1. Sidebar cleanup

- [x] 1.1 Remove the `/invoices/export` nav entry from Sidebar.tsx navItems array
- [x] 1.2 Remove the `/liquidity-forecast` nav entry from Sidebar.tsx navItems array
- [x] 1.3 Remove the `/forecast` nav entry from Sidebar.tsx navItems array
- [x] 1.4 Add a single `/forecasts` nav entry with TrendingUp icon, labelKey `nav.forecasts`, no permission requirement

## 2. Invoice Export button on Invoices page

- [x] 2.1 Add an "Export" Link button (FileDown icon) in the InvoiceList header that navigates to `/invoices/export`, gated on `invoices.export` permission via `hasPermission`
- [x] 2.2 Add translation keys for the export button label in en.json and de.json

## 3. Unified Forecasts page

- [x] 3.1 Create `frontend/src/features/forecasts/ForecastsPage.tsx` with Shadcn Tabs, reading `tab` search param (`revenue` default, `liquidity` option)
- [x] 3.2 Import and render `RevenueForecast` inside the revenue TabsContent
- [x] 3.3 Import and render `LiquidityForecast` inside the liquidity TabsContent, conditionally shown only if user has `banking.read` permission
- [x] 3.4 Hide tab switcher entirely when user only has access to one tab (no banking permission)

## 4. Route updates in App.tsx

- [x] 4.1 Remove the `/forecast` route
- [x] 4.2 Remove the `/liquidity-forecast` route
- [x] 4.3 Add `/forecasts` route pointing to ForecastsPage
- [x] 4.4 Import ForecastsPage in App.tsx

## 5. Translation updates

- [x] 5.1 Add `nav.forecasts` key in en.json ("Forecasts") and de.json ("Vorschauen")
- [x] 5.2 Add `forecasts.revenueTab` and `forecasts.liquidityTab` keys in en.json and de.json
- [x] 5.3 Remove unused `nav.invoiceExport`, `nav.forecast`, `nav.liquidityForecast` keys from en.json and de.json

## 6. Help video links cleanup

- [x] 6.1 Update helpVideoLinks.ts: replace `/forecast` and `/liquidity-forecast` entries with `/forecasts` entry, remove `/invoices/export` entry

## 7. Remove unused icon imports

- [x] 7.1 Remove the `Wallet` and `FileDown` icon imports from Sidebar.tsx (no longer used)

## 8. Verification

- [x] 8.1 Run `npx tsc --noEmit` to verify no TypeScript errors
- [x] 8.2 Manually verify: Sidebar shows "Invoices" (with export button on page) and "Forecasts" (with tabs)
