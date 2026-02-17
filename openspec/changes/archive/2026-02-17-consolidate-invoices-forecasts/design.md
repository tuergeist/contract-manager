## Context

The sidebar currently has 4 entries for closely related functionality:
- **Invoices** (`/invoices`) — uploaded invoice management
- **Invoice Export** (`/invoices/export`) — generate invoices from contracts for a given month
- **Liquidity Forecast** (`/liquidity-forecast`) — cash-flow projection based on recurring bank patterns
- **Revenue Forecast** (`/forecast`) — contract-based billing/recognition projection

Each is a self-contained page with its own route and nav entry. The goal is to reduce this to 2 nav entries without losing any functionality.

## Goals / Non-Goals

**Goals:**
- Consolidate Invoices + Invoice Export into a single "Invoices" nav entry, with export accessible via a button
- Consolidate Liquidity Forecast + Revenue Forecast into a single "Forecasts" tabbed page
- Preserve all existing functionality — this is purely a navigation/layout reorganization
- Keep old routes working via redirects (or simply remove them since this is an internal tool with few users)

**Non-Goals:**
- Changing any backend APIs or GraphQL schema
- Modifying the invoice export or forecast logic itself
- Adding new forecast features or invoice capabilities

## Decisions

### 1. Invoice Export access: Navigate button vs inline

**Decision:** Add a `<Link>` button in the InvoiceList header that navigates to `/invoices/export`. Keep InvoiceExportPage as a separate component at the same route — just remove its sidebar entry.

**Rationale:** The InvoiceExportPage is a complex, self-contained component (~400 lines) with its own state (month selector, contract list, bulk actions). Embedding it inline would bloat the already large InvoiceList. A simple navigation button is cleaner and requires minimal code changes.

**Alternative considered:** Tabs on the invoice page (Uploaded / Export). Rejected because the two views are conceptually different workflows (managing uploaded docs vs generating new ones) and tabs would imply they're variants of the same thing.

### 2. Forecasts page: Tab routing approach

**Decision:** Create a new `ForecastsPage` component at `/forecasts` that uses URL search params (`?tab=revenue` / `?tab=liquidity`) to switch between tabs. Each tab renders the existing component (`RevenueForecast` / `LiquidityForecast`) unchanged.

**Rationale:** Using search params keeps tab state in the URL (bookmarkable/shareable) without needing nested routes. The existing forecast components are self-contained and can be rendered as-is inside a tab panel.

**Alternative considered:** Nested routes (`/forecasts/revenue`, `/forecasts/liquidity`). Would work but adds routing complexity for what is visually a tabbed interface. Search params are simpler and the convention used elsewhere in the app.

### 3. Tab UI implementation

**Decision:** Use Shadcn Tabs component (`@shadcn/tabs`) for the forecasts page. The existing RevenueForecast and LiquidityForecast components render directly inside `TabsContent`.

**Rationale:** Shadcn Tabs already handle accessible tab switching. Both forecast components manage their own headers/controls, so the wrapper just needs to provide the tab switching chrome.

### 4. Permission handling for forecasts

**Decision:** The Forecasts nav entry requires no permission (revenue forecast has none today). Inside the page, the liquidity tab is conditionally shown based on `banking.read` permission (same as the current standalone entry).

**Rationale:** Keeps the same access control as today. Users without banking access simply don't see the liquidity tab.

### 5. Route cleanup

**Decision:** Remove old routes (`/forecast`, `/liquidity-forecast`, `/invoices/export` as standalone nav entry). Keep `/invoices/export` as a route since the export button navigates there. No redirects needed — this is an internal tool with direct navigation.

## Risks / Trade-offs

- **Bookmarked old URLs break** (`/forecast`, `/liquidity-forecast`) → Acceptable for internal tool. Could add redirect routes if needed, but not worth the complexity.
- **Two forecast components rendered but only one visible** → Use conditional rendering (not CSS hiding) to avoid unnecessary queries. Only the active tab's component mounts.
- **InvoiceExportPage keeps its own header/title** → Slightly different UX than being "inside" the invoices page, but the back-navigation via browser is natural enough.
