## Tasks

### 1. Backend: Add date params to counterparties resolver
- [x] 1.1 Add `date_from: date | None = None` and `date_to: date | None = None` parameters to `counterparties()` resolver
- [x] 1.2 Build a `Q()` filter from the date params and apply it to all transaction annotations (total_debit, total_credit, txn_count, first_date, last_date, abs_total)

### 2. Frontend: Add date pickers to counterparties tab
- [x] 2.1 Add `cpDateFrom` and `cpDateTo` state variables
- [x] 2.2 Add `dateFrom` and `dateTo` variables to `BANK_COUNTERPARTIES` GQL query
- [x] 2.3 Pass date variables to the counterparties query call
- [x] 2.4 Add date-from and date-to input fields above the counterparty table
- [x] 2.5 Reset to page 1 when date filters change

### 3. Frontend: Pass date range to counterparty detail
- [x] 3.1 Include `dateFrom`/`dateTo` as URL search params when navigating to counterparty detail
- [x] 3.2 Read `dateFrom`/`dateTo` from URL params in `CounterpartyDetailPage` and pass to the detail query

### 4. Backend: Add date params to single counterparty resolver
- [x] 4.1 Add `date_from` / `date_to` params to `counterparty()` resolver and apply to its annotations
