## 1. Backend: Counterparty Aggregation Query

- [ ] 1.1 Add `bankCounterparties` query to `banking/schema.py` with `BankCounterpartyType` (name, totalDebit, totalCredit, transactionCount, firstDate, lastDate) and `BankCounterpartyPage` (items, totalCount, page, pageSize, hasNextPage)
- [ ] 1.2 Implement aggregation using `values('counterparty_name').annotate()` with Sum, Count, Min, Max; support search, sortBy, sortOrder, page, pageSize parameters
- [ ] 1.3 Add `counterpartyName` exact-match filter to existing `bank_transactions` query
- [ ] 1.4 Write tests for `bankCounterparties` query (list, search, sort, pagination)
- [ ] 1.5 Write tests for `counterpartyName` filter on `bankTransactions` query

## 2. Frontend: Translations & Routing

- [ ] 2.1 Add translations for counterparty section in `de.json` and `en.json` (counterparties, totalDebit, totalCredit, firstTransaction, lastTransaction, backToBanking, noCounterparties)
- [ ] 2.2 Add `/banking/counterparty/:name` route in `App.tsx` with new `CounterpartyDetailPage` component

## 3. Frontend: Counterparty List

- [ ] 3.1 Add counterparties tab/section to BankingPage with table: name, count, total amount, last date
- [ ] 3.2 Implement search input for counterparty name filtering
- [ ] 3.3 Implement column sorting (name, totalAmount, transactionCount, lastDate)
- [ ] 3.4 Implement pagination (50 per page)
- [ ] 3.5 Make each row clickable, navigating to `/banking/counterparty/:name`

## 4. Frontend: Counterparty Detail Page

- [ ] 4.1 Create `CounterpartyDetailPage.tsx` with summary header (name, totals, count, date range)
- [ ] 4.2 Reuse transaction table from BankingPage with `counterpartyName` filter pre-applied
- [ ] 4.3 Add back navigation button to banking page
- [ ] 4.4 Support all existing filters (date, amount, direction, account, sorting, pagination)

## 5. Frontend: Clickable Counterparty Names

- [ ] 5.1 Make counterparty name in transaction table a clickable link to `/banking/counterparty/:name`
- [ ] 5.2 Stop click propagation so row expand still works on other columns

## 6. Testing & Polish

- [ ] 6.1 Run `make test-back` — all tests pass
- [ ] 6.2 Run `npx tsc --noEmit` — no type errors
