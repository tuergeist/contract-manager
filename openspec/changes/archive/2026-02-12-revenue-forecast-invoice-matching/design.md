## Context

The revenue forecast tab (`ForecastTab` in ContractDetail.tsx) displays a `billingSchedule` query that shows expected billing dates and amounts for a contract. Each `BillingEvent` has a date, line items, and total amount.

Contracts can have linked imported invoices (`ImportedInvoice` model with `contract` FK). These invoices have:
- `invoice_number`, `invoice_date`, `total_amount`
- `is_paid` property (based on payment matches)
- `contract_id` for the linked contract

Currently there's no connection between forecast events and actual invoices in the UI.

## Goals / Non-Goals

**Goals:**
- Show which forecast billing events have matching invoices
- Display invoice number (linked to PDF) and payment status (paid/unpaid badge)
- Match invoices to forecast events by contract + date proximity + amount similarity

**Non-Goals:**
- Auto-linking invoices to contracts (already exists separately)
- Creating invoices from forecasts
- Complex matching algorithms (fuzzy matching, ML)
- Matching multiple invoices to one forecast event (show first/best match only)

## Decisions

### 1. Extend `BillingEvent` type to include matched invoice

**Decision**: Add optional `matched_invoice` field to `BillingEvent` GraphQL type

**Rationale**: Keeps the data together in one query, avoids N+1 queries on frontend. The invoice matching logic runs server-side during billing schedule calculation.

**Alternatives considered**:
- Separate query for invoice matches → Extra round-trip, harder to correlate
- Frontend-side matching → Requires fetching all invoices, complex date logic in JS

### 2. Matching criteria

**Decision**: Match invoice to forecast event when:
1. Invoice has same `contract_id` as the contract
2. Invoice date is within ±15 days of the forecast billing date
3. (Optional tiebreaker) Amount within 10% of forecast total

**Rationale**: Simple date proximity works for most cases. Contract FK ensures we only match relevant invoices. 15-day window accounts for invoice date vs billing date discrepancies.

### 3. Invoice display format

**Decision**: Add "Invoice" column to forecast table showing:
- Invoice number as link (to PDF if available, else to imported invoices page)
- Paid/Unpaid badge (green/gray, same style as invoices tab)

**Rationale**: Consistent with existing invoice display patterns in the app.

## Risks / Trade-offs

**[Multiple invoices match same forecast date]** → Show first match by invoice date, log warning. Future: could show count or list.

**[Performance with many invoices]** → Filter invoices by contract_id upfront (indexed), then in-memory matching for date proximity. Should be <100 invoices per contract typically.

**[Invoice date significantly different from billing date]** → 15-day window may miss some. User can still see invoices in the Invoices tab.
